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

// Signaling for the vendored dora-openarm-webxr frontend, through this
// site instead of the node's own HTTPS server. It mirrors the keyboard
// page: the offer is stored as a row, the runner polls the server for
// it, starts the dora-openarm-webxr node in WebRTC-only mode and stores
// the node's answer, which this page claims by polling.
//
// The page lives at /tasks/{task_id}/teleoperation/webxr and the
// signaling endpoints live under it, so build their URLs from the
// page's own path; the path also tells the runner what kind of offer
// this is.
async function postOffer(sdp) {
  const response = await fetch(`${location.pathname}/offers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sdp: sdp }),
  });
  if (!response.ok) {
    throw new Error("signaling failed: " + response.status);
  }
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
    if (response.status === 200) {
      const answer = await response.json();
      return answer.sdp;
    }
    if (response.status !== 204) {
      throw new Error("signaling failed: " + response.status);
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("no answer from the runner");
}

// Takes the offer SDP and resolves with the answer SDP, the shape
// connection.js expects from a custom signal function.
export async function signal(sdp) {
  const offerId = await postOffer(sdp);
  return fetchAnswer(offerId);
}
