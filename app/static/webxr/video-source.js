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

// A WebRTC video track as a WebGL texture source.
//
// The track arrives decoded, so there is no JPEG to turn into a bitmap
// first: the video element goes straight into texImage2D. The element is
// muted and plays inline because a headset browser will not start a video
// that could make noise without a gesture it never gets here.

export function createVideoSource(track) {
  const video = document.createElement("video");
  video.autoplay = true;
  video.muted = true;
  video.playsInline = true;
  video.srcObject = new MediaStream([track]);
  // A rejected play() leaves the texture blank rather than throwing into
  // the render loop, where it would stop everything else being drawn.
  video.play().catch(() => {});

  let uploaded = -1;

  return {
    // Upload the newest decoded frame, if there is one that has not been
    // uploaded yet. Returns the frame size, or null when nothing was
    // uploaded, so the caller can keep the size it already had.
    upload(gl, texture) {
      // HAVE_CURRENT_DATA: anything less has no frame to read.
      if (video.readyState < 2 || video.videoWidth === 0) {
        return null;
      }
      if (video.currentTime === uploaded) {
        return null;
      }
      uploaded = video.currentTime;
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.RGBA,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        video,
      );
      return { width: video.videoWidth, height: video.videoHeight };
    },
    close() {
      video.pause();
      video.srcObject = null;
    },
  };
}
