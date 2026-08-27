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

import { createVideoSource } from "./video-source.js";

// Draws the head camera image on a panel fixed in the room.
//
// The panel hangs in the world-fixed local space, straight ahead of
// where the headset was when the session started, so the operator can
// look around it or lean in while the image stays put. Both eyes see
// the same image; depth comes from the panel sitting at a real
// distance. Where it hangs is tuned over the "control" data channel.

const VERTEX_SHADER = `
attribute vec2 a_corner;
uniform mat4 u_projection;
uniform mat4 u_view;
uniform vec2 u_half_extent;
uniform float u_distance;
varying vec2 v_uv;
void main() {
  gl_Position = u_projection * u_view *
    vec4(a_corner * u_half_extent, -u_distance, 1.0);
  // Flipped because the image starts at its top row and texture
  // coordinates start at the bottom. Done here rather than with
  // UNPACK_FLIP_Y_WEBGL, which browsers honour inconsistently.
  v_uv = vec2((a_corner.x + 1.0) * 0.5, (1.0 - a_corner.y) * 0.5);
}
`;

const FRAGMENT_SHADER = `
precision mediump float;
uniform sampler2D u_texture;
varying vec2 v_uv;
void main() {
  gl_FragColor = texture2D(u_texture, v_uv);
}
`;

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader));
  }
  return shader;
}

class CameraPanel {
  #gl = null;
  #program = null;
  #buffer = null;
  #attributes = {};
  #uniforms = {};
  #texture = null;
  #source = null;
  #size = { width: 0, height: 0 };
  #configuration = null;

  constructor(configuration, track) {
    this.#configuration = configuration;
    // No track means the node is not sending this eye; the panel then
    // draws nothing rather than being absent, so the rest of the scene
    // is laid out the same either way.
    this.#source = track ? createVideoSource(track) : null;
  }

  // Called once the WebXR session has created its WebGL context.
  attach(gl) {
    this.#gl = gl;
    const program = gl.createProgram();
    gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER));
    gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program));
    }
    this.#program = program;

    this.#attributes.corner = gl.getAttribLocation(program, "a_corner");
    for (const name of [
      "u_projection",
      "u_view",
      "u_half_extent",
      "u_distance",
      "u_texture",
    ]) {
      this.#uniforms[name] = gl.getUniformLocation(program, name);
    }

    this.#buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.#buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW,
    );

    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    // Not a power of two, so no mipmaps and no repeating.
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    this.#texture = texture;
    // The vertical flip is done in the vertex shader instead.
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  }

  #upload() {
    if (!this.#source) {
      return;
    }
    // Keep the previous size when there is no new frame: the panel is
    // still showing the last one, so its shape must not change.
    const size = this.#source.upload(this.#gl, this.#texture);
    if (size) {
      this.#size = size;
    }
  }

  render(session, space, frame) {
    if (!this.#gl || !this.#configuration) {
      return;
    }
    const pose = frame.getViewerPose(space);
    if (!pose) {
      return;
    }
    const gl = this.#gl;
    const layer = session.renderState.baseLayer;

    gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
    // Transparent so passthrough shows around the panel.
    gl.clearColor(0.0, 0.0, 0.0, 0.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.disable(gl.DEPTH_TEST);

    this.#upload();
    if (this.#size.width === 0) {
      // No frame yet, so no aspect ratio to size the panel with.
      return;
    }

    const panel = this.#configuration.panel;
    // The height follows the image so it is never stretched.
    const halfExtent = [
      panel.width / 2.0,
      ((panel.width / 2.0) * this.#size.height) / this.#size.width,
    ];

    gl.useProgram(this.#program);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.#buffer);
    gl.enableVertexAttribArray(this.#attributes.corner);
    gl.vertexAttribPointer(this.#attributes.corner, 2, gl.FLOAT, false, 0, 0);
    gl.uniform2f(this.#uniforms.u_half_extent, halfExtent[0], halfExtent[1]);
    gl.uniform1f(this.#uniforms.u_distance, panel.distance);
    gl.uniform1i(this.#uniforms.u_texture, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.#texture);

    for (const view of pose.views) {
      const viewport = layer.getViewport(view);
      gl.viewport(viewport.x, viewport.y, viewport.width, viewport.height);
      gl.uniformMatrix4fv(
        this.#uniforms.u_projection,
        false,
        view.projectionMatrix,
      );
      gl.uniformMatrix4fv(
        this.#uniforms.u_view,
        false,
        view.transform.inverse.matrix,
      );
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
  }

  close() {
    if (this.#source) {
      this.#source.close();
      this.#source = null;
    }
  }
}

export function createCameraPanel(configuration, track) {
  return new CameraPanel(configuration, track);
}
