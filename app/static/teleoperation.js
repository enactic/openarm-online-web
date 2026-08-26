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

const statusElement = document.getElementById("status");
const heldElement = document.getElementById("held");
const helpElement = document.getElementById("help");
const connectButton = document.getElementById("connect");
const video = document.getElementById("video");

let channel = null;
const held = new Set();

function setStatus(text) {
  statusElement.textContent = text;
}

function showHeld() {
  heldElement.textContent = held.size
    ? "held: " + [...held].sort().join(" ")
    : "";
}

function send(type, key) {
  if (channel && channel.readyState === "open") {
    channel.send(JSON.stringify({ type, key }));
  }
}

// Only forward keys the runner can use: printable characters plus Shift
// (rotation modifier) and Escape (quit). Modifier chords (Cmd+R, Ctrl+W, …)
// pass through untouched. Printable keys are lowercased so a key held across
// a Shift press pairs its keydown ("w") with its keyup ("W" → "w").
function usableKey(event) {
  if (event.metaKey || event.ctrlKey || event.altKey) return null;
  if (event.key.length === 1) return event.key.toLowerCase();
  if (event.key === "Shift" || event.key === "Escape") return event.key;
  return null;
}

window.addEventListener("keydown", (event) => {
  const key = usableKey(event);
  if (key === null) return;
  event.preventDefault();
  if (event.repeat) return;
  held.add(key);
  showHeld();
  send("keydown", key);
});

window.addEventListener("keyup", (event) => {
  const key = usableKey(event);
  if (key === null) return;
  event.preventDefault();
  held.delete(key);
  showHeld();
  send("keyup", key);
});

// Losing focus loses keyup events, so release everything: an unfocused page
// must never keep the robot moving.
function releaseAll() {
  for (const key of held) send("keyup", key);
  held.clear();
  showHeld();
}
window.addEventListener("blur", releaseAll);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) releaseAll();
});
window.addEventListener("pagehide", releaseAll);

// The page lives at /tasks/{task_id}/teleoperation and the signaling
// endpoints live under it, so build their URLs from the page's own path.
async function postOffer(description) {
  const response = await fetch(`${location.pathname}/offers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sdp: description.sdp }),
  });
  if (!response.ok) throw new Error("signaling failed: " + response.status);
  const { id } = await response.json();
  return id;
}

async function fetchAnswer(offerId) {
  // The runner isn't connected to us; it polls the server for pending
  // offers and stores its answer there, so poll until the answer shows up.
  const intervalMs = 1000;
  const timeoutMs = 60000;
  for (let elapsed = 0; elapsed < timeoutMs; elapsed += intervalMs) {
    // POST, not GET: claiming the answer also deletes the offer and the
    // answer on the server.
    const response = await fetch(
      `${location.pathname}/offers/${offerId}/answer/claim`,
      { method: "POST" },
    );
    if (response.status === 200) return response.json();
    if (response.status !== 204) {
      throw new Error("signaling failed: " + response.status);
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("no answer from the runner");
}

async function connect() {
  const configuration = {
    iceServers: [
      {
        urls: ["stun:stun.cloudflare.com:3478"],
      },
    ],
  };
  const pc = new RTCPeerConnection(configuration);

  channel = pc.createDataChannel("keys");
  channel.onopen = () =>
    setStatus("connected — click the page, then hold keys to move");
  channel.onclose = () => setStatus("disconnected — reload to reconnect");

  pc.addTransceiver("video", { direction: "recvonly" });
  pc.ontrack = (event) => {
    video.srcObject = event.streams[0];
  };

  // The key bindings arrive over a WebRTC "help" data channel the runner
  // opens, not over HTTP: the help text lives in the runner's keymap, and
  // this page has no copy of it.
  pc.ondatachannel = (event) => {
    if (event.channel.label === "help") {
      event.channel.onmessage = (message) => {
        helpElement.textContent = message.data;
      };
    }
  };

  await pc.setLocalDescription(await pc.createOffer());
  // Non-trickle ICE: the offer is stored as a single row and the runner
  // only learns candidates from the SDP it reads — there is no channel to
  // send candidates one by one afterwards. setLocalDescription() resolves
  // before gathering finishes, so wait until every candidate has been added
  // to localDescription.sdp before sending it. The browser has no
  // promise-based API for this; bridge the icegatheringstatechange event
  // into an awaitable, checking the current state first in case gathering
  // already finished before the listener was attached.
  await new Promise((resolve) => {
    if (pc.iceGatheringState === "complete") {
      resolve();
      return;
    }
    pc.addEventListener("icegatheringstatechange", () => {
      if (pc.iceGatheringState === "complete") resolve();
    });
  });

  const offerId = await postOffer(pc.localDescription);
  setStatus("waiting for the runner…");
  const answer = await fetchAnswer(offerId);
  await pc.setRemoteDescription({ type: "answer", sdp: answer.sdp });
}

connectButton.addEventListener("click", () => {
  connectButton.disabled = true;
  setStatus("connecting…");
  connect().catch((error) => {
    setStatus("connection failed: " + error.message);
    connectButton.disabled = false;
  });
});
