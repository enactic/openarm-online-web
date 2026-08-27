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

// The browser half of the WebRTC connection to the node.
//
// Everything the headset and the node say to each other rides one peer
// connection, so this page does not have to be served by the node. That
// is the point: WebRTC needs no certificate from whoever answers, so the
// node can sit on a LAN with no HTTPS server while the page comes from
// somewhere that already has a certificate.
//
// Two data channels, split by what they can afford to lose. "xr" is
// unordered and never retransmitted, and carries the frame messages at
// the animation frame rate: only the newest pose is worth anything, so a
// lost frame is dropped rather than retransmitted. Each frame carries a
// "sequence" so the node can drop the stale ones an unordered channel
// occasionally delivers late. "control" is reliable and carries what must
// not be lost: the node's configuration push, session-start, the select
// and squeeze events, and what came of a calibration run.

const ICE_SERVERS = [
  {
    urls: ["stun:stun.cloudflare.com:3478"],
  },
];

// The node decides how many eyes it draws, but this page has to make the
// offer before it can be told, and the signaling here is a single
// exchange with no renegotiation. So always offer this many and let the
// node leave the ones it does not use inactive.
const VIDEO_TRANSCEIVERS = 2;

// Signaling for the node's own HTTPS server: one POST, because both
// sides gather all their ICE candidates before exchanging anything.
async function postOffer(sdp) {
  const response = await fetch("offer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sdp: sdp }),
  });
  if (!response.ok) {
    throw new Error("signaling failed: " + response.status);
  }
  const answer = await response.json();
  return answer.sdp;
}

// Resolves once the browser has finished gathering; there is no
// promise-based API for this, so bridge the event.
function gathered(pc) {
  if (pc.iceGatheringState === "complete") {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    pc.addEventListener("icegatheringstatechange", () => {
      if (pc.iceGatheringState === "complete") {
        resolve();
      }
    });
  });
}

// Connect to the node and resolve once it has said how to draw itself.
//
// `signal` takes the offer SDP and resolves with the answer SDP, so a
// differently hosted page can broker signaling its own way without
// changing anything else here. `iceServers` likewise lets the hosting
// page hand in servers of its own (e.g. TURN credentials minted by its
// server); without it the default STUN-only servers are used.
export async function connect({ signal = postOffer, iceServers = null } = {}) {
  const pc = new RTCPeerConnection({ iceServers: iceServers || ICE_SERVERS });
  const received = [];
  const handlers = { calibrationResult: null, close: null };
  let control = null;
  let sequence = 0;
  let closed = false;

  const xr = pc.createDataChannel("xr", {
    ordered: false,
    maxRetransmits: 0,
  });

  for (let index = 0; index < VIDEO_TRANSCEIVERS; index++) {
    pc.addTransceiver("video", { direction: "recvonly" });
  }

  pc.addEventListener("track", (event) => {
    // Keyed by mid, because the eye a track carries is decided by
    // negotiation order and the node names that order in its
    // configuration message.
    received.push({ mid: Number(event.transceiver.mid), track: event.track });
  });

  const configured = new Promise((resolve, reject) => {
    // The node going away is noticed in two ways, and either must end
    // the session. The reliable channel closes almost instantly when
    // the node shuts down cleanly; the connection state only reaches
    // "failed" after an ICE timeout, long after a node that died
    // without a word. The channel close is the fast path, the state
    // change the last resort.
    function lost() {
      reject(new Error("the connection to the node was lost"));
      if (!closed && handlers.close) {
        closed = true;
        handlers.close();
      }
    }
    pc.addEventListener("datachannel", (event) => {
      if (event.channel.label !== "control") {
        return;
      }
      control = event.channel;
      control.addEventListener("close", lost);
      control.addEventListener("message", (message) => {
        let payload;
        try {
          payload = JSON.parse(message.data);
        } catch (error) {
          console.error("cannot read a message from the node: " + error);
          return;
        }
        if (payload.type === "configuration") {
          resolve(payload);
        } else if (payload.type === "calibration-result") {
          if (handlers.calibrationResult) {
            handlers.calibrationResult(payload);
          }
        }
      });
    });
    pc.addEventListener("connectionstatechange", () => {
      if (pc.connectionState === "failed" || pc.connectionState === "closed") {
        lost();
      }
    });
  });

  await pc.setLocalDescription(await pc.createOffer());
  await gathered(pc);
  const answer = await signal(pc.localDescription.sdp);
  await pc.setRemoteDescription({ type: "answer", sdp: answer });

  const payload = await configured;
  // The node names the eyes in track order, so a lone track in the mono
  // view is never mistaken for the left eye.
  received.sort((a, b) => a.mid - b.mid);
  const tracks = {};
  payload.eyes.forEach((eye, index) => {
    if (received[index]) {
      tracks[eye] = received[index].track;
    }
  });

  return {
    configuration: payload.view_configuration,
    calibration: { enabled: payload.calibration === true },
    eyes: payload.eyes,
    tracks: tracks,
    // Frames are numbered here so the node can drop the ones this
    // unordered channel delivers late.
    sendFrame(message) {
      if (xr.readyState !== "open") {
        return;
      }
      sequence += 1;
      xr.send(JSON.stringify({ ...message, sequence }));
    },
    sendControl(message) {
      if (control && control.readyState === "open") {
        control.send(JSON.stringify(message));
      }
    },
    onCalibrationResult(handler) {
      handlers.calibrationResult = handler;
    },
    onClose(handler) {
      handlers.close = handler;
    },
    close() {
      closed = true;
      pc.close();
    },
  };
}
