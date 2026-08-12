const BUSYBAR_WIDGETS = [
  "message",
  "entity",
  "weather",
  "calendar",
  "countdown",
  "clock",
  "progress",
  "chart",
  "alert",
  "streak",
  "scoreboard",
];

const BUSYBAR_EFFECTS = [
  "rainbow",
  "scanner",
  "confetti",
  "breathe",
  "aurora",
  "fireplace",
  "lava_lamp",
  "ocean_waves",
  "starfield",
  "matrix_rain",
  "snowfall",
  "sunrise",
  "equalizer",
  "fireworks",
  "jackpot",
  "thunderstorm",
  "red_alert",
  "heartbeat",
  "sparkle",
  "package_drop",
  "laundry_party",
  "goal",
];

const BUSYBAR_GAMES = [
  "dice",
  "coin_flip",
  "magic_8_ball",
  "reaction",
  "pong",
  "snake",
  "pixel_pet",
];

const BUSYBAR_PRESETS = [
  "someone_is_here",
  "package_delivered",
  "laundry_done",
  "dinner_ready",
  "meeting_soon",
  "weather_warning",
  "air_quality_warning",
  "alarm",
  "welcome_home",
  "bedtime",
  "chore_complete",
  "focus_break",
  "goal_scored",
  "print_complete",
  "celebration",
];

class BusyBarCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._config = {};
  }

  setConfig(config) {
    if (!config.device_id) {
      throw new Error("BUSY Bar card requires device_id");
    }
    this._config = {
      title: "BUSY Bar Playground",
      preview_entity: "",
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._updatePreview();
  }

  getCardSize() {
    return 7;
  }

  static getConfigElement() {
    return document.createElement("busybar-card-editor");
  }

  static getStubConfig() {
    return { device_id: "", title: "BUSY Bar Playground" };
  }

  _render() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host { --busy-accent: #22d3ee; --busy-pink: #f472b6; }
        ha-card { overflow: hidden; background: linear-gradient(145deg, var(--ha-card-background, #111827), #0f172a); }
        .hero { padding: 18px 18px 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
        h2 { margin: 0; font-size: 20px; letter-spacing: .02em; }
        .status { color: var(--secondary-text-color); font-size: 12px; }
        .preview-wrap { padding: 0 18px 14px; }
        .preview { width: 100%; min-height: 64px; image-rendering: pixelated; object-fit: contain; border-radius: 10px; background: #000; box-shadow: inset 0 0 0 1px #ffffff18, 0 8px 30px #0008; }
        .tabs { display: flex; gap: 6px; padding: 0 18px 12px; overflow-x: auto; }
        .tab { flex: 1 0 auto; }
        .tab, button { border: 0; border-radius: 9px; color: var(--primary-text-color); background: #ffffff0d; cursor: pointer; padding: 9px; font: inherit; }
        .tab.active { color: #001018; background: var(--busy-accent); font-weight: 700; }
        .panel { padding: 0 18px 18px; }
        .hidden { display: none; }
        .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
        label { display: grid; gap: 5px; color: var(--secondary-text-color); font-size: 12px; }
        input, select { box-sizing: border-box; width: 100%; min-width: 0; border: 1px solid #ffffff20; border-radius: 8px; color: var(--primary-text-color); background: #0005; padding: 9px; font: inherit; }
        input[type=color] { padding: 2px; min-height: 39px; }
        .wide { grid-column: 1 / -1; }
        .send { grid-column: 1 / -1; color: #001018; font-weight: 800; background: linear-gradient(90deg, var(--busy-accent), var(--busy-pink)); }
        .chips { display: flex; flex-wrap: wrap; gap: 7px; }
        h3 { margin: 3px 0 9px; color: var(--secondary-text-color); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }
        .pixel-stage { position: relative; width: 100%; aspect-ratio: 4.5; grid-column: 1 / -1; overflow: hidden; touch-action: none; background: #000; border: 1px solid #ffffff30; border-radius: 10px; image-rendering: pixelated; box-shadow: inset 0 0 24px #000; cursor: crosshair; }
        .pixel-stage::after { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .15; background-image: linear-gradient(#fff3 1px, transparent 1px), linear-gradient(90deg, #fff3 1px, transparent 1px); background-size: calc(100% / var(--grid-width, 72)) calc(100% / var(--grid-height, 16)); }
        .pixel-copy { position: absolute; transform: translate(-50%, -50%); z-index: 1; max-width: 95%; color: #22d3ee; font: 800 20px/1 monospace; white-space: nowrap; text-shadow: 0 0 8px currentColor; cursor: grab; user-select: none; }
        .pixel-copy:active { cursor: grabbing; }
        .hint { grid-column: 1 / -1; color: var(--secondary-text-color); font-size: 11px; }
        .chip { text-transform: capitalize; }
        .chip:hover, button:hover { background: #ffffff20; }
        .danger { color: #fecaca; }
        .toast { min-height: 18px; margin-top: 9px; color: var(--busy-accent); font-size: 12px; }
        @media (max-width: 420px) { .grid { grid-template-columns: 1fr; } }
      </style>
      <ha-card>
        <div class="hero"><div><h2></h2><div class="status">Local canvas • front + rear</div></div><button id="clear">Clear</button></div>
        <div class="preview-wrap"><img class="preview" alt="BUSY Bar screen preview" /></div>
        <div class="tabs">
          <button class="tab active" data-panel="compose">Compose</button>
          <button class="tab" data-panel="canvas">Canvas</button>
          <button class="tab" data-panel="effects">Effects</button>
          <button class="tab" data-panel="games">Games</button>
          <button class="tab" data-panel="profiles">Profiles</button>
          <button class="tab" data-panel="media">Media</button>
        </div>
        <div class="panel" id="compose">
          <div class="grid">
            <label>Widget<select id="widget"></select></label>
            <label>Display<select id="display"><option>front</option><option>back</option></select></label>
            <label class="wide">Title<input id="title" placeholder="Next meeting" /></label>
            <label class="wide">Value<input id="value" placeholder="Design review • 2:30" /></label>
            <label>Color<input id="color" type="color" value="#22d3ee" /></label>
            <label>Background<input id="background" type="color" value="#000000" /></label>
            <label>Duration (seconds)<input id="duration" type="number" min="0" max="3600" value="15" /></label>
            <label>Priority<input id="priority" type="number" min="1" max="100" value="50" /></label>
            <button class="send" id="send">Send to BUSY Bar</button>
          </div>
          <div class="toast" aria-live="polite"></div>
        </div>
        <div class="panel hidden" id="canvas">
          <div class="grid">
            <div class="pixel-stage" id="canvas-stage"><div class="pixel-copy" id="canvas-copy">HELLO!</div></div>
            <div class="hint">Drag the words to place them on the real pixel canvas.</div>
            <label class="wide">Text<input id="canvas-text" value="HELLO!" maxlength="64" /></label>
            <label>Display<select id="canvas-display"><option>front</option><option>back</option></select></label>
            <label>Font<select id="canvas-font"><option>tiny</option><option selected>normal</option><option>large</option></select></label>
            <label>X<input id="canvas-x" type="number" min="0" max="71" value="36" /></label>
            <label>Y<input id="canvas-y" type="number" min="0" max="15" value="8" /></label>
            <label>Text color<input id="canvas-color" type="color" value="#22d3ee" /></label>
            <label>Background<input id="canvas-background" type="color" value="#000000" /></label>
            <label>Duration<input id="canvas-duration" type="number" min="0" max="3600" value="20" /></label>
            <label>Priority<input id="canvas-priority" type="number" min="1" max="100" value="50" /></label>
            <button class="send" id="send-canvas">Draw this canvas</button>
          </div>
          <div class="toast" aria-live="polite"></div>
        </div>
        <div class="panel hidden" id="effects"><h3>Household shortcuts</h3><div class="chips" id="preset-chips"></div><h3>Animation lab</h3><div class="chips" id="effect-chips"></div><div class="toast" aria-live="polite"></div></div>
        <div class="panel hidden" id="games"><div class="chips" id="game-chips"></div><div class="toast" aria-live="polite"></div></div>
        <div class="panel hidden" id="profiles">
          <div class="grid">
            <label>Profile<select id="profile-slot"><option>busy</option><option>custom</option></select></label>
            <label>Timer type<select id="profile-type"><option>infinite</option><option>simple</option><option>interval</option></select></label>
            <label class="wide">Title<input id="profile-title" value="FOCUS" /></label>
            <label>Minutes<input id="profile-minutes" type="number" min="1" value="25" /></label>
            <label>Rest minutes<input id="profile-rest" type="number" min="1" value="5" /></label>
            <label>Cycles<input id="profile-cycles" type="number" min="1" value="4" /></label>
            <label>Theme<input id="profile-theme" value="busy" /></label>
            <button class="send" id="save-profile">Save physical profile</button>
          </div>
          <div class="toast" aria-live="polite"></div>
        </div>
        <div class="panel hidden" id="media">
          <div class="grid">
            <label class="wide">Media-source ID<input id="media-id" placeholder="media-source://media_source/local/picture.png" /></label>
            <button id="show-front">Show on front</button><button id="show-back">Show on rear</button>
            <button class="wide" id="play-audio">Play audio</button>
            <label class="wide">QR text or URL<input id="qr-value" placeholder="https://homeassistant.local" /></label>
            <button class="send" id="show-qr">Show QR on rear</button>
          </div>
          <div class="toast" aria-live="polite"></div>
        </div>
      </ha-card>`;

    this.shadowRoot.querySelector("h2").textContent = this._config.title;
    const widget = this.shadowRoot.querySelector("#widget");
    BUSYBAR_WIDGETS.forEach((name) => widget.add(new Option(this._label(name), name)));
    this._makeChips("#effect-chips", BUSYBAR_EFFECTS, (effect) =>
      this._call("play_effect", { effect, duration: 8, fps: 8 }),
    );
    this._makeChips("#preset-chips", BUSYBAR_PRESETS, (preset) =>
      this._call("play_preset", { preset }),
    );
    this._makeChips("#game-chips", BUSYBAR_GAMES, (game) =>
      this._call("play_game", { game, duration: 30, fps: 8 }),
    );
    this.shadowRoot.querySelectorAll(".tab").forEach((tab) =>
      tab.addEventListener("click", () => this._selectPanel(tab.dataset.panel)),
    );
    this.shadowRoot.querySelector("#send").addEventListener("click", () => this._sendWidget());
    this.shadowRoot.querySelector("#send-canvas").addEventListener("click", () => this._sendCanvas());
    this.shadowRoot.querySelector("#clear").addEventListener("click", () => this._call("clear_display", {}));
    this.shadowRoot.querySelector("#save-profile").addEventListener("click", () => this._saveProfile());
    this.shadowRoot.querySelector("#show-front").addEventListener("click", () => this._showMedia("front"));
    this.shadowRoot.querySelector("#show-back").addEventListener("click", () => this._showMedia("back"));
    this.shadowRoot.querySelector("#play-audio").addEventListener("click", () => this._call("play_media", { media_content_id: this.shadowRoot.querySelector("#media-id").value }));
    this.shadowRoot.querySelector("#show-qr").addEventListener("click", () => this._call("show_qr", { value: this.shadowRoot.querySelector("#qr-value").value, duration: 30 }));
    ["canvas-text", "canvas-display", "canvas-font", "canvas-x", "canvas-y", "canvas-color", "canvas-background"].forEach((id) =>
      this.shadowRoot.querySelector(`#${id}`).addEventListener("input", () => this._updateCanvas()),
    );
    const stage = this.shadowRoot.querySelector("#canvas-stage");
    const placeText = (event) => {
      const dimensions = this.shadowRoot.querySelector("#canvas-display").value === "front" ? [72, 16] : [160, 80];
      const bounds = stage.getBoundingClientRect();
      const x = Math.max(0, Math.min(dimensions[0] - 1, Math.round((event.clientX - bounds.left) / bounds.width * dimensions[0])));
      const y = Math.max(0, Math.min(dimensions[1] - 1, Math.round((event.clientY - bounds.top) / bounds.height * dimensions[1])));
      this.shadowRoot.querySelector("#canvas-x").value = x;
      this.shadowRoot.querySelector("#canvas-y").value = y;
      this._updateCanvas();
    };
    stage.addEventListener("pointerdown", (event) => { stage.setPointerCapture(event.pointerId); placeText(event); });
    stage.addEventListener("pointermove", (event) => { if (stage.hasPointerCapture(event.pointerId)) placeText(event); });
    this._updateCanvas();
    this._updatePreview();
  }

  _makeChips(selector, values, callback) {
    const host = this.shadowRoot.querySelector(selector);
    values.forEach((value) => {
      const button = document.createElement("button");
      button.className = "chip";
      button.textContent = this._label(value);
      button.addEventListener("click", () => callback(value));
      host.appendChild(button);
    });
  }

  _selectPanel(panel) {
    this.shadowRoot.querySelectorAll(".panel").forEach((element) => element.classList.toggle("hidden", element.id !== panel));
    this.shadowRoot.querySelectorAll(".tab").forEach((element) => element.classList.toggle("active", element.dataset.panel === panel));
  }

  _sendWidget() {
    const get = (id) => this.shadowRoot.querySelector(`#${id}`).value;
    const data = {
      widget: get("widget"),
      display: get("display"),
      title: get("title"),
      value: get("value"),
      color: get("color"),
      background: get("background"),
      duration: Number(get("duration")),
      priority: Number(get("priority")),
      restore: true,
    };
    if (data.widget === "progress") data.progress = Number(data.value) || 0;
    if (data.widget === "countdown") data.timestamp = data.value;
    if (data.widget === "chart") data.values = data.value.split(",").map(Number).filter(Number.isFinite);
    this._call("show_widget", data);
  }

  _saveProfile() {
    const get = (id) => this.shadowRoot.querySelector(`#${id}`).value;
    const minutes = Number(get("profile-minutes"));
    this._call("set_profile", {
      slot: get("profile-slot"),
      title: get("profile-title"),
      timer_type: get("profile-type"),
      minutes,
      work_minutes: minutes,
      rest_minutes: Number(get("profile-rest")),
      cycles: Number(get("profile-cycles")),
      theme: get("profile-theme"),
      autostart: false,
      show_work_only: true,
      trigger_smart_home: true,
    });
  }

  _showMedia(display) {
    this._call("show_media", {
      media_content_id: this.shadowRoot.querySelector("#media-id").value,
      display,
      duration: 30,
      loop: true,
      opacity: 100,
    });
  }

  _updateCanvas() {
    if (!this.shadowRoot) return;
    const get = (id) => this.shadowRoot.querySelector(`#${id}`).value;
    const display = get("canvas-display");
    const dimensions = display === "front" ? [72, 16] : [160, 80];
    const stage = this.shadowRoot.querySelector("#canvas-stage");
    const copy = this.shadowRoot.querySelector("#canvas-copy");
    const xInput = this.shadowRoot.querySelector("#canvas-x");
    const yInput = this.shadowRoot.querySelector("#canvas-y");
    xInput.max = dimensions[0] - 1;
    yInput.max = dimensions[1] - 1;
    const x = Math.max(0, Math.min(dimensions[0] - 1, Number(xInput.value) || 0));
    const y = Math.max(0, Math.min(dimensions[1] - 1, Number(yInput.value) || 0));
    stage.style.aspectRatio = `${dimensions[0]} / ${dimensions[1]}`;
    stage.style.setProperty("--grid-width", dimensions[0]);
    stage.style.setProperty("--grid-height", dimensions[1]);
    stage.style.background = get("canvas-background");
    copy.textContent = get("canvas-text") || " ";
    copy.style.left = `${x / dimensions[0] * 100}%`;
    copy.style.top = `${y / dimensions[1] * 100}%`;
    copy.style.color = get("canvas-color");
    copy.style.fontSize = { tiny: "12px", normal: "20px", large: "30px" }[get("canvas-font")];
  }

  _sendCanvas() {
    const get = (id) => this.shadowRoot.querySelector(`#${id}`).value;
    const display = get("canvas-display");
    const dimensions = display === "front" ? [72, 16] : [160, 80];
    const duration = Number(get("canvas-duration"));
    this._call("draw", {
      clear_before_draw: true,
      payload: {
        priority: Number(get("canvas-priority")),
        elements: [
          { id: "canvas-bg", type: "rectangle", x: 0, y: 0, width: dimensions[0], height: dimensions[1], fill: "solid", fill_colors: [get("canvas-background")], border_width: 0, border_color: "#00000000", display, timeout: duration },
          { id: "canvas-text", type: "text", text: get("canvas-text"), font: get("canvas-font"), color: get("canvas-color"), x: Number(get("canvas-x")), y: Number(get("canvas-y")), align: "center", display, timeout: duration },
        ],
      },
    });
  }

  async _call(service, data) {
    if (!this._hass) return;
    const panel = this.shadowRoot.querySelector(".panel:not(.hidden)");
    const toast = panel?.querySelector(".toast");
    try {
      await this._hass.callService("busybar", service, { device_id: [this._config.device_id], ...data });
      if (toast) toast.textContent = `${this._label(service)} sent`;
    } catch (error) {
      if (toast) toast.textContent = error?.message || String(error);
    }
  }

  _updatePreview() {
    const image = this.shadowRoot?.querySelector(".preview");
    if (!image || !this._hass || !this._config.preview_entity) return;
    const state = this._hass.states[this._config.preview_entity];
    const picture = state?.attributes?.entity_picture;
    if (picture) image.src = picture;
  }

  _label(value) {
    return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }
}

class BusyBarCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(value) {
    this._hass = value;
  }

  _render() {
    this.shadowRoot.innerHTML = `<style>.form{display:grid;gap:12px;padding:12px}label{display:grid;gap:5px}input{padding:9px}</style><div class="form"><label>Device ID<input id="device" /></label><label>Front preview image entity<input id="preview" /></label><label>Title<input id="title" /></label></div>`;
    const fields = {
      device: "device_id",
      preview: "preview_entity",
      title: "title",
    };
    Object.entries(fields).forEach(([id, key]) => {
      const input = this.shadowRoot.querySelector(`#${id}`);
      input.value = this._config?.[key] || "";
      input.addEventListener("input", () => {
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: { ...this._config, [key]: input.value } }, bubbles: true, composed: true }));
      });
    });
  }
}

customElements.define("busybar-card", BusyBarCard);
customElements.define("busybar-card-editor", BusyBarCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({ type: "busybar-card", name: "BUSY Bar Playground", description: "Compose widgets, effects, and tiny games for a local BUSY Bar", preview: true });
