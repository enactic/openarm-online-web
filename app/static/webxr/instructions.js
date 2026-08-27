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

// Tells the operator how to measure their neck pivot, inside the
// headset. Only a node started with --calibration asks for this panel.
//
// The operator is wearing the headset, so the node's output is the one
// place they cannot read: what to do, and what came of doing it, has to
// be in front of their eyes. The text is drawn on a 2D canvas and put on
// a head-locked panel below the middle of the view, where it stays
// readable through the very head turn it is asking for, and leaves the
// camera panel above it alone.

const VERTEX_SHADER = `
attribute vec2 a_corner;
uniform mat4 u_projection;
uniform mat4 u_view;
uniform vec2 u_half_extent;
uniform vec2 u_center;
uniform float u_distance;
varying vec2 v_uv;
void main() {
  gl_Position = u_projection * u_view *
    vec4(a_corner * u_half_extent + u_center, -u_distance, 1.0);
  // Flipped because the canvas starts at its top row and texture
  // coordinates start at the bottom.
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

// The canvas the text is drawn on, in pixels. Wider than the panel needs
// so the text stays sharp when the operator leans in to read it.
const CANVAS = { width: 1024, height: 512 };

// Where the panel hangs, in meters, in the operator's own view: below
// the middle of it, so the camera panel above stays visible.
const PANEL = { distance: 1.2, width: 0.8, center: -0.32 };

// How many characters a line of the node's reason may run to before it
// is wrapped. The reasons are sentences written for a terminal.
const WRAP_COLUMNS = 44;

const IDLE = {
  title: "Neck pivot calibration",
  lines: [
    "Hold the Y button on the left controller",
    "to measure it. The hands stop while it",
    "is held, and follow again on release.",
  ],
};

const RUNNING = {
  title: "Measuring — keep the body still",
  lines: [
    "Turn the head side to side, twice over,",
    "then up and down, twice over.",
    "Release Y when you are done.",
  ],
};

function wrap(text, columns) {
  const lines = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    if (line && line.length + 1 + word.length > columns) {
      lines.push(line);
      line = word;
    } else {
      line = line ? `${line} ${word}` : word;
    }
  }
  if (line) {
    lines.push(line);
  }
  return lines;
}

// What the node said about a finished run, as something to read.
function describe(result) {
  if (!result.accepted) {
    return {
      title: "Calibration refused",
      lines: wrap(result.reason, WRAP_COLUMNS).concat([
        "Hold Y again to try once more.",
      ]),
    };
  }
  const offset = result.offset
    .map((component) => component.toFixed(3))
    .join(", ");
  return {
    title: "Calibration applied",
    lines: [
      `neck pivot [${offset}] m, ${result.samples} poses`,
      `held to ${result.residual_mm.toFixed(1)} mm,` +
        ` headset moved ${result.headset_mm.toFixed(1)} mm`,
      result.saved_to
        ? `written to ${result.saved_to}`
        : "kept for this session only",
    ],
  };
}

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader));
  }
  return shader;
}

class InstructionPanel {
  #gl = null;
  #program = null;
  #buffer = null;
  #attributes = {};
  #uniforms = {};
  #texture = null;
  #canvas = null;
  #context = null;
  // Set when the drawn text no longer matches the state, so the text is
  // laid out on a change rather than on every frame.
  #stale = true;
  #pressed = false;
  #result = null;
  #clears = false;

  constructor({ clears }) {
    // Nobody else draws when there is no camera view, so the panel has
    // to clear the frame itself or the last one stays on the display.
    this.#clears = clears;
    this.#canvas = document.createElement("canvas");
    this.#canvas.width = CANVAS.width;
    this.#canvas.height = CANVAS.height;
    this.#context = this.#canvas.getContext("2d");
  }

  // Whether the Y button is down, which is the run under way. Read from
  // the controller here rather than waited for from the node, so the
  // panel answers the press at once.
  setPressed(pressed) {
    if (pressed !== this.#pressed) {
      this.#pressed = pressed;
      // A new run replaces the last one's result, so the operator is
      // never reading an old number while making a new one.
      if (pressed) {
        this.#result = null;
      }
      this.#stale = true;
    }
  }

  // What the node made of a finished run.
  setResult(result) {
    this.#result = result;
    this.#stale = true;
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
      "u_center",
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
    // Smoothed rather than sharpened, since the text is read at an
    // angle as often as head on, and clamped so it never wraps.
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    this.#texture = texture;
    // The vertical flip is done in the vertex shader instead.
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  }

  #text() {
    if (this.#pressed) {
      return RUNNING;
    }
    if (this.#result) {
      return describe(this.#result);
    }
    return IDLE;
  }

  #upload() {
    if (!this.#stale) {
      return;
    }
    const context = this.#context;
    const { width, height } = CANVAS;
    const { title, lines } = this.#text();

    context.clearRect(0, 0, width, height);
    // Dark enough to read white text over the passthrough behind it.
    context.fillStyle = "rgba(0, 0, 0, 0.72)";
    context.fillRect(0, 0, width, height);

    context.textAlign = "center";
    context.textBaseline = "middle";
    // Green while a run is under way, so the operator can tell the
    // hands stopped for this and not for a fault.
    context.fillStyle = this.#pressed ? "#7ee787" : "#ffffff";
    context.font = "bold 58px sans-serif";
    context.fillText(title, width / 2, 96);

    context.fillStyle = "#ffffff";
    context.font = "44px sans-serif";
    lines.forEach((line, index) => {
      context.fillText(line, width / 2, 200 + index * 64);
    });

    const gl = this.#gl;
    gl.bindTexture(gl.TEXTURE_2D, this.#texture);
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      this.#canvas,
    );
    this.#stale = false;
  }

  // ``space`` is the viewer space, so the panel stays in front of the
  // operator through the head turn it is asking them for.
  render(session, space, frame) {
    if (!this.#gl) {
      return;
    }
    const pose = frame.getViewerPose(space);
    if (!pose) {
      return;
    }
    const gl = this.#gl;
    const layer = session.renderState.baseLayer;

    gl.bindFramebuffer(gl.FRAMEBUFFER, layer.framebuffer);
    if (this.#clears) {
      // Transparent so passthrough shows around the panel.
      gl.clearColor(0.0, 0.0, 0.0, 0.0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    }
    gl.disable(gl.DEPTH_TEST);
    // Over whatever the camera view drew, rather than in place of it.
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    this.#upload();

    const halfExtent = [
      PANEL.width / 2.0,
      ((PANEL.width / 2.0) * CANVAS.height) / CANVAS.width,
    ];

    gl.useProgram(this.#program);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.#buffer);
    gl.enableVertexAttribArray(this.#attributes.corner);
    gl.vertexAttribPointer(this.#attributes.corner, 2, gl.FLOAT, false, 0, 0);
    gl.uniform2f(this.#uniforms.u_half_extent, halfExtent[0], halfExtent[1]);
    gl.uniform2f(this.#uniforms.u_center, 0.0, PANEL.center);
    gl.uniform1f(this.#uniforms.u_distance, PANEL.distance);
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
    gl.disable(gl.BLEND);
  }
}

export function createInstructionPanel(options) {
  return new InstructionPanel(options);
}
