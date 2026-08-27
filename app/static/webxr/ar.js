// Copyright 2026 Enactic, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { connect } from "./connection.js";
import { createInstructionPanel } from "./instructions.js";
import { createCameraPanel } from "./panel.js";
// Vendored from dora-openarm-webxr; the local changes route signaling
// and ICE server discovery through this site instead of the node's own
// HTTPS server (signal.js).
import { iceServers, signal } from "./signal.js";
import { createStereoPanel } from "./stereo.js";

// Used only when the node's view configuration cannot be read.
const FALLBACK_CONFIGURATION = {
  view: "mono",
  session: { mode: "immersive-ar" },
  panel: { lock: "room", distance: 1.3, width: 1.5 },
};

if (navigator.xr) {
  let connection = null;
  let runningSession = null;
  let configuration = null;
  let cameraPanel = null;
  let instructionPanel = null;

  const connectButton = document.getElementById("connect");
  const startButton = document.getElementById("start");
  const statusElement = document.getElementById("status");

  function setStatus(text) {
    statusElement.textContent = text;
  }

  // The node pushes its configuration as soon as the connection opens,
  // so this page needs no route of its own to read it: whoever serves
  // this file, the node still decides how it draws itself. The session
  // can only start once this has resolved, so the view and the panels
  // are always set by then. Connecting is a button of its own rather
  // than a page-load side effect, so merely opening the page does not
  // make the runner start a node.
  function openConnection() {
    return connect({ signal, iceServers: iceServers() }).then((opened) => {
      connection = opened;
      configuration = opened.configuration || FALLBACK_CONFIGURATION;

      // How many images: the default "mono" draws one, "stereo" draws one
      // per eye, and "none" shows no camera at all. Where they hang is a
      // separate question, answered by "panel: lock" in the configuration.
      if (configuration.view === "stereo") {
        cameraPanel = createStereoPanel(configuration, opened.tracks);
      } else if (configuration.view !== "none") {
        cameraPanel = createCameraPanel(configuration, opened.tracks.right);
      }

      // Only a node started with --calibration wants the instructions, and
      // only it acts on the Y button, so the panel that asks for a head
      // turn is never in front of an operator whose Y button means
      // something else. Read after the view, since the panel has to know
      // whether a camera view is drawing the frame or it is the only one
      // there.
      if (opened.calibration.enabled) {
        instructionPanel = createInstructionPanel({
          clears: cameraPanel === null,
        });
      }

      // The node only speaks to say what came of a calibration run.
      opened.onCalibrationResult((message) => {
        if (instructionPanel) {
          instructionPanel.setResult(message);
        }
      });

      // Losing the connection ends the session: an operator left inside a
      // frozen view has no way to tell that nothing is reaching the robot.
      opened.onClose(() => {
        connection = null;
        if (runningSession) {
          runningSession.end();
          runningSession = null;
        }
        // The node is one-shot, so continuing needs a fresh offer.
        startButton.disabled = true;
        connectButton.disabled = false;
        setStatus("disconnected — connect again to continue");
      });

      return configuration;
    });
  }

  function sendControl(message) {
    if (connection) {
      connection.sendControl(message);
    }
  }

  function log(message) {
    // document.getElementById("log").innerText += `${message}\n`;
    // sendControl({type: "log", message: `${message}`});
  }
  function onSessionEnd(event) {
    log("ended");
    if (cameraPanel) {
      cameraPanel.close();
    }
    runningSession = null;
    if (connection) {
      connection.close();
      connection = null;
    }
  }
  function onSelectStart(event) {
    const response = {
      type: "select-start",
      buttons: event.inputSource.gamepad.buttons,
      axes: event.inputSource.gamepad.axes,
    };
    sendControl(response);
  }
  function onSelect(event) {
    const response = {
      type: "select",
      buttons: event.inputSource.gamepad.buttons,
      axes: event.inputSource.gamepad.axes,
    };
    sendControl(response);
  }
  function onSelectEnd(event) {
    const response = {
      type: "select-end",
      buttons: event.inputSource.gamepad.buttons,
      axes: event.inputSource.gamepad.axes,
    };
    sendControl(response);
  }
  function onSqueezeStart(event) {
    const response = {
      type: "squeeze-start",
      buttons: event.inputSource.gamepad.buttons,
      axes: event.inputSource.gamepad.axes,
    };
    sendControl(response);
  }
  function onSqueeze(event) {
    const response = {
      type: "squeeze",
      buttons: event.inputSource.gamepad.buttons,
      axes: event.inputSource.gamepad.axes,
    };
    sendControl(response);
  }
  function onSqueezeEnd(event) {
    const response = {
      type: "squeeze-end",
      buttons: event.inputSource.gamepad.buttons,
      axes: event.inputSource.gamepad.axes,
    };
    sendControl(response);
  }
  function sendFrameResponse(response) {
    if (instructionPanel) {
      // An absent button is a released one, which is how the node reads
      // it too, so a controller that falls asleep or goes missing ends
      // the run on the panel just as it ends it there.
      instructionPanel.setPressed(response.button_y === true);
    }
    // Frames go on the unreliable channel, which numbers them: only the
    // newest pose is worth anything, so a lost one is dropped rather
    // than retransmitted behind the frames that follow it.
    if (connection) {
      connection.sendFrame(response);
    }
  }
  function sendFrame(session, space, time, frame) {
    const response = {
      type: "frame",
      time: time,
    };
    // Read before the controller check below, so a consumer driving something
    // from head motion keeps tracking while the controllers are off or asleep.
    // The hand poses are made relative to this pose by the node, so when it is
    // missing the node drops them and only the head keeps flowing.
    const viewerPose = frame.getViewerPose(space);
    if (viewerPose) {
      const transform = viewerPose.transform;
      response.pose_reference = {
        x: transform.position.x,
        y: transform.position.y,
        z: transform.position.z,
        qx: transform.orientation.x,
        qy: transform.orientation.y,
        qz: transform.orientation.z,
        qw: transform.orientation.w,
      };
    }
    if (session.inputSources.length < 2) {
      sendFrameResponse(response);
      return;
    }
    for (const source of session.inputSources) {
      if (source.handedness === "none") {
        continue;
      }
      const suffix = `_${source.handedness}`;
      // The target ray space is the OpenXR aim pose: its -Z points where
      // the controller points. The node maps the gripper onto that axis
      // directly, so it must not be the grip pose, whose -Z runs along the
      // handle and would turn the handle's tilt into the gripper's.
      const pose = frame.getPose(source.targetRaySpace, space);
      if (pose) {
        response[`pose${suffix}`] = {
          x: pose.transform.position.x,
          y: pose.transform.position.y,
          z: pose.transform.position.z,
          qx: pose.transform.orientation.x,
          qy: pose.transform.orientation.y,
          qz: pose.transform.orientation.z,
          qw: pose.transform.orientation.w,
        };
      }
      const gamepad = source.gamepad;
      if (gamepad) {
        if (
          source.profiles.includes("pico-4u") ||
          source.profiles.includes("meta-quest-touch-plus") ||
          source.profiles.includes("oculus-touch-v3")
        ) {
          const trigger = gamepad.buttons[0];
          response[`trigger${suffix}`] = trigger.value;

          // The squeeze sits next to the trigger under the xr-standard
          // mapping. Sent as its 0..1 value rather than a pressed flag, so
          // that a consumer can pick its own threshold.
          const grip = gamepad.buttons[1];
          if (grip) {
            response[`grip${suffix}`] = grip.value;
          }
          if (source.handedness === "right") {
            const a = gamepad.buttons[4];
            const b = gamepad.buttons[5];
            response.button_a = a.pressed;
            response.button_b = b.pressed;
          } else {
            const x = gamepad.buttons[4];
            const y = gamepad.buttons[5];
            response.button_x = x.pressed;
            response.button_y = y.pressed;
          }
        }
        // Send the whole array and let the node pick the pair it wants.
        // Testing the axes for truthiness, as this once did, meant the
        // joystick was never sent from a Quest at all: its Touch controllers
        // have no touchpad and report axes[0..1] as a constant 0, so the
        // check could never pass. A centred thumbstick reads exactly 0 too,
        // which would have gated out the resting position even on a device
        // that does have a touchpad.
        if (gamepad.axes.length >= 2) {
          response[`joystick${suffix}`] = Array.from(gamepad.axes);
        }
      }
    }
    sendFrameResponse(response);
  }
  function onSessionStart(session) {
    runningSession = session;
    // TODO: Add device information
    const response = {
      type: "session-start",
    };
    sendControl(response);

    session.addEventListener("end", onSessionEnd);

    session.addEventListener("selectstart", onSelectStart);
    session.addEventListener("select", onSelect);
    session.addEventListener("selectend", onSelectEnd);

    session.addEventListener("squeezestart", onSqueezeStart);
    session.addEventListener("squeeze", onSqueeze);
    session.addEventListener("squeezeend", onSqueezeEnd);

    // The render state is needed to use immersive AR even when nothing
    // is drawn into it. The camera views draw their panel into it.
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl", { xrCompatible: true });
    session.updateRenderState({ baseLayer: new XRWebGLLayer(session, gl) });
    if (cameraPanel) {
      cameraPanel.attach(gl);
    }
    if (instructionPanel) {
      instructionPanel.attach(gl);
    }

    Promise.all([
      // The hand poses and the head pose are both read in the
      // world-fixed local space, and the node makes the hand positions
      // relative to the head pose without inheriting the head rotation.
      // The panel hangs in whichever space "panel: lock" names: the
      // room is the local space, the head is the viewer space.
      session.requestReferenceSpace("viewer"),
      session.requestReferenceSpace("local"),
    ])
      .then(([viewerSpace, localSpace]) => {
        const panel = configuration.panel || {};
        const panelSpace = panel.lock === "head" ? viewerSpace : localSpace;
        function onFrame(time, frame) {
          log("sources: " + session.inputSources.length);
          sendFrame(session, localSpace, time, frame);
          if (cameraPanel) {
            cameraPanel.render(session, panelSpace, frame);
          }
          // After the camera view, so the text is over the image rather
          // than cleared away with the rest of the frame, and always in
          // the viewer space so it stays readable through a head turn.
          if (instructionPanel) {
            instructionPanel.render(session, viewerSpace, frame);
          }
          session.requestAnimationFrame(onFrame);
        }
        session.requestAnimationFrame(onFrame);
      })
      .catch((error) => {
        alert(error);
      });
  }
  function onStart(mode) {
    navigator.xr.requestSession(mode).then(onSessionStart);
  }

  connectButton.addEventListener("click", () => {
    connectButton.disabled = true;
    setStatus("connecting…");
    openConnection()
      .then((configuration) => {
        // The session mode is configured with the head camera view so
        // that passthrough can be turned off without changing this file.
        const mode = configuration.session.mode;
        return navigator.xr.isSessionSupported(mode).then((isSupported) => {
          if (!isSupported) {
            throw new Error(`this device does not support ${mode}`);
          }
          startButton.disabled = false;
          setStatus("connected — press Start to enter the session");
        });
      })
      .catch((error) => {
        setStatus(`connection failed: ${error.message || error}`);
        connectButton.disabled = false;
      });
  });

  // WebXR requires explicit user interaction on start, and
  // requestSession() must be called directly in the click handler:
  // waiting for signaling here would outlive the click's transient
  // activation, which is why connecting is a separate button pressed
  // first.
  startButton.addEventListener("click", () => {
    onStart(configuration.session.mode);
  });
} else {
  document.getElementById("status").textContent =
    "WebXR is not supported by this browser";
}
