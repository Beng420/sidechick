let state = null;
let captureTarget = null;
let coordinateSearchActive = false;

const els = {};

window.addEventListener("DOMContentLoaded", () => {
  for (const id of [
    "script-list",
    "script-tabs",
    "status-grid",
    "settings-form",
    "settings-title",
    "app-title",
    "app-subtitle",
    "log-output",
    "update-line",
    "update-status",
    "start-button",
    "pause-button",
    "stop-button",
    "save-button",
    "reload-button",
    "check-updates-button",
    "install-update-button",
    "requirements-button",
    "sidebar-toggle",
    "capture-overlay",
    "changelog-overlay",
    "changelog-title",
    "changelog-body",
    "changelog-close-button",
    "coordinate-overlay",
    "coordinate-status",
    "coordinate-cancel-button",
    "settings-tooltip",
  ]) {
    els[toCamel(id)] = document.getElementById(id);
  }

  els.sidebarToggle.addEventListener("click", toggleSidebar);
  els.startButton.addEventListener("click", startSelectedScript);
  els.pauseButton.addEventListener("click", pauseSelectedScript);
  els.stopButton.addEventListener("click", stopSelectedScript);
  els.saveButton.addEventListener("click", saveSelectedConfig);
  els.reloadButton.addEventListener("click", refreshState);
  els.checkUpdatesButton.addEventListener("click", () => checkUpdates());
  els.installUpdateButton.addEventListener("click", installUpdate);
  els.requirementsButton.addEventListener("click", installRequirements);
  els.changelogCloseButton.addEventListener("click", dismissChangelog);
  els.coordinateCancelButton.addEventListener("click", cancelFihRegionSearch);
});

window.addEventListener("pywebviewready", async () => {
  await refreshState();
  await checkUpdates({ automatic: true });
  setInterval(pollRuntime, 450);
});

window.addEventListener("keydown", event => {
  if (coordinateSearchActive && event.key === "Escape") {
    event.preventDefault();
    cancelFihRegionSearch();
    return;
  }
  if (!captureTarget) {
    return;
  }
  event.preventDefault();
  const binding = event.key === "Escape" ? "" : keyBinding(event);
  finishCapture(binding);
});

window.addEventListener("mousedown", event => {
  if (!captureTarget) {
    return;
  }
  event.preventDefault();
  const mouseMap = {
    0: "mouse:left",
    1: "mouse:middle",
    2: "mouse:right",
    3: "mouse:x",
    4: "mouse:x2",
  };
  finishCapture(mouseMap[event.button] || `mouse:${event.button}`);
});

window.addEventListener("contextmenu", event => {
  if (captureTarget) {
    event.preventDefault();
  }
});

function toCamel(id) {
  return id.replace(/-([a-z])/g, (_, char) => char.toUpperCase());
}

async function refreshState() {
  state = await window.pywebview.api.get_state();
  normalizeState();
  render();
}

function normalizeState() {
  if (state && state.process && state.process.processes) {
    state.processes = state.process.processes;
  }
}

async function pollRuntime() {
  if (!window.pywebview || !state) {
    return;
  }
  const result = await window.pywebview.api.drain_logs(state.selected_script);
  if (result.logs.length) {
    appendLogs(result.logs);
  }
  state.process = result.process;
  state.processes = result.process.processes || state.processes || {};
  renderStatus();
  renderScripts();
  updateRuntimeButtons();
}

function render() {
  renderHeader();
  renderScripts();
  renderSettings();
  renderStatus();
  renderUpdate();
  renderChangelog();
  updateRuntimeButtons();
}

function selectedScript() {
  return state.scripts.find(script => script.id === state.selected_script) || state.scripts[0];
}

function processFor(scriptId) {
  if (state.processes && state.processes[scriptId]) {
    return state.processes[scriptId];
  }
  if (state.process && state.process.script_id === scriptId) {
    return state.process;
  }
  return { running: false, state: "stopped", mode_cards: {} };
}

function renderHeader() {
  const script = selectedScript();
  els.appTitle.textContent = `Sidechick ${state.app_version}`;
  els.appSubtitle.textContent = `${script.name} - ${script.description}`;
}

function renderScripts() {
  els.scriptList.innerHTML = "";
  els.scriptTabs.innerHTML = "";

  for (const script of state.scripts) {
    const runtime = processFor(script.id);
    const item = document.createElement("button");
    item.className = `script-item ${script.id === state.selected_script ? "active" : ""} ${runtime.state || "stopped"}`;
    item.disabled = !script.available;
    item.innerHTML = `<span class="script-name">${script.name}</span><span class="script-meta">${script.description}</span><span class="script-state">${runtime.running ? runtime.state : "stopped"}</span>`;
    item.addEventListener("click", () => selectScript(script.id));
    els.scriptList.appendChild(item);

    const tab = document.createElement("button");
    tab.className = `script-tab ${script.id === state.selected_script ? "active" : ""}`;
    tab.disabled = !script.available;
    tab.textContent = script.name;
    tab.addEventListener("click", () => selectScript(script.id));
    els.scriptTabs.appendChild(tab);
  }
}

async function selectScript(scriptId) {
  const result = await window.pywebview.api.select_script(scriptId);
  if (!result.ok) {
    appendLogs([result.message]);
    return;
  }
  state = result.state;
  render();
}

function renderSettings() {
  const script = selectedScript();
  els.settingsTitle.textContent = `${script.name} settings`;
  els.settingsForm.innerHTML = "";

  for (const group of script.schema) {
    const section = document.createElement("section");
    section.className = "settings-group";
    section.innerHTML = `<h3>${group.title}</h3>`;

    const grid = document.createElement("div");
    grid.className = "form-grid";
    for (const field of group.fields) {
      grid.appendChild(renderField(field));
    }
    section.appendChild(grid);
    els.settingsForm.appendChild(section);
  }
}

function renderField(field) {
  const value = getByPath(state.selected_config, field.key);
  const wrapper = document.createElement("div");
  wrapper.className = "field";
  wrapper.dataset.key = field.key;
  wrapper.dataset.type = field.type;
  if (field.help) {
    wrapper.dataset.help = field.help;
    wrapper.addEventListener("mouseenter", showSettingTooltip);
    wrapper.addEventListener("mousemove", moveSettingTooltip);
    wrapper.addEventListener("mouseleave", hideSettingTooltip);
  }

  const label = document.createElement("label");
  label.textContent = field.label;
  wrapper.appendChild(label);

  let control;
  if (field.type === "select") {
    control = document.createElement("select");
    for (const option of field.options) {
      const item = document.createElement("option");
      item.value = option;
      item.textContent = option;
      control.appendChild(item);
    }
    control.value = value;
  } else if (field.type === "bool") {
    control = document.createElement("select");
    for (const [raw, labelText] of [["true", "On"], ["false", "Off"]]) {
      const item = document.createElement("option");
      item.value = raw;
      item.textContent = labelText;
      control.appendChild(item);
    }
    control.value = value ? "true" : "false";
  } else if (field.type === "json") {
    control = document.createElement("textarea");
    control.value = JSON.stringify(value, null, 2);
  } else if (field.type === "action") {
    control = document.createElement("button");
    control.type = "button";
    control.className = "secondary action-button";
    control.textContent = "Start";
    if (field.action === "find_fih_region") {
      control.addEventListener("click", findFihRegion);
    }
  } else if (field.type === "binding" || field.type === "bindings") {
    const row = document.createElement("div");
    row.className = "binding-row";
    control = document.createElement("input");
    control.value = Array.isArray(value) ? value.join(", ") : (value || "");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Set";
    button.addEventListener("click", () => startCapture(control, field.type === "bindings"));
    row.appendChild(control);
    row.appendChild(button);
    wrapper.appendChild(row);
    return wrapper;
  } else {
    control = document.createElement("input");
    control.type = field.type === "int" || field.type === "float" ? "number" : "text";
    control.step = field.type === "float" ? "0.01" : "1";
    control.value = value;
  }

  wrapper.appendChild(control);
  return wrapper;
}

function collectConfig() {
  const config = JSON.parse(JSON.stringify(state.selected_config));
  for (const field of els.settingsForm.querySelectorAll(".field")) {
    const key = field.dataset.key;
    const type = field.dataset.type;
    if (type === "action") {
      continue;
    }
    const control = field.querySelector("input, select, textarea");
    let value = control.value;

    if (type === "int") {
      value = parseInt(value, 10);
    } else if (type === "float") {
      value = parseFloat(value);
    } else if (type === "bool") {
      value = value === "true";
    } else if (type === "bindings") {
      value = bindingList(value);
    } else if (type === "binding") {
      value = bindingList(value)[0] || "";
    } else if (type === "json") {
      try {
        value = JSON.parse(value);
      } catch (_error) {
        appendLogs([`Invalid JSON in ${key}.`]);
        throw new Error(`Invalid JSON in ${key}`);
      }
    }
    setByPath(config, key, value);
  }
  return config;
}

async function saveSelectedConfig() {
  try {
    const config = collectConfig();
    const result = await window.pywebview.api.save_script_config(state.selected_script, config);
    if (result.ok) {
      state.selected_config = result.config;
      appendLogs([`${selectedScript().name} config saved.`]);
      renderSettings();
      return true;
    }
  } catch (_error) {
    return false;
  }
  return false;
}

async function startSelectedScript() {
  const saved = await saveSelectedConfig();
  if (!saved) {
    return;
  }
  const result = await window.pywebview.api.start_script(state.selected_script);
  appendLogs([result.message]);
  await refreshState();
}

async function pauseSelectedScript() {
  const runtime = processFor(state.selected_script);
  const shouldPause = runtime.state !== "paused";
  const result = await window.pywebview.api.pause_script(state.selected_script, shouldPause);
  appendLogs([result.message]);
  await refreshState();
}

async function stopSelectedScript() {
  const result = await window.pywebview.api.stop_script(state.selected_script);
  appendLogs([result.message]);
  await refreshState();
}

async function setRuntimeOption(key, value) {
  const result = await window.pywebview.api.set_runtime_option(state.selected_script, key, value);
  if (!result.ok) {
    appendLogs([result.message]);
    return;
  }
  state.selected_config = result.config;
  state.process = result.process;
  state.processes = result.process.processes || state.processes || {};
  renderSettings();
  renderStatus();
}

async function findFihRegion() {
  let config;
  try {
    config = collectConfig();
  } catch (_error) {
    return;
  }

  coordinateSearchActive = true;
  els.coordinateCancelButton.disabled = false;
  els.coordinateStatus.textContent = "Left-click near the red bite overlay. Click again anytime to move the marker. Sidechick calibrates position, size, and target color.";
  els.coordinateOverlay.classList.remove("hidden");
  appendLogs(["Coordinate search started. Left-click near the red bite overlay. Yellow overlays are ignored. Press Escape or cancel to stop."]);
  try {
    const result = await window.pywebview.api.find_fih_region(config);
    appendLogs([result.message]);
    if (result.config) {
      state.selected_config = result.config;
      renderSettings();
      renderStatus();
    }
  } finally {
    coordinateSearchActive = false;
    els.coordinateOverlay.classList.add("hidden");
  }
}

async function cancelFihRegionSearch() {
  if (!coordinateSearchActive) {
    return;
  }
  els.coordinateCancelButton.disabled = true;
  els.coordinateStatus.textContent = "Cancelling coordinate search...";
  await window.pywebview.api.cancel_fih_region_search();
}

async function checkUpdates(options = {}) {
  const automatic = options.automatic === true;
  els.checkUpdatesButton.disabled = true;
  els.updateLine.textContent = "Checking updates...";
  if (!automatic) {
    els.updateStatus.textContent = "";
  }
  const result = await window.pywebview.api.check_updates();
  if (!result.ok) {
    els.updateLine.textContent = result.message;
    if (!automatic) {
      appendLogs([`Update check failed: ${result.message}`]);
    }
  } else {
    state.update = result.update;
    renderUpdate();
  }
  els.checkUpdatesButton.disabled = false;
}

async function installUpdate() {
  els.installUpdateButton.disabled = true;
  const result = await window.pywebview.api.install_update();
  appendLogs([result.message]);
  await refreshState();
}

async function dismissChangelog() {
  els.changelogOverlay.classList.add("hidden");
  state.pending_changelog = null;
  await window.pywebview.api.dismiss_update_changelog();
}

async function installRequirements() {
  els.requirementsButton.disabled = true;
  appendLogs(["Installing requirements..."]);
  const result = await window.pywebview.api.install_requirements();
  if (result.output) {
    appendLogs(result.output.split(/\r?\n/).filter(Boolean));
  }
  appendLogs([result.message]);
  els.requirementsButton.disabled = false;
}

function renderStatus() {
  const process = processFor(state.selected_script);
  const cards = process.mode_cards || {};
  const script = selectedScript();
  els.statusGrid.innerHTML = "";

  if (script.mode_status) {
    const fishingValue = cards.fishing || state.selected_config.start_mode || "UNKNOWN";
    els.statusGrid.appendChild(statusCard("Fishing", fishingValue, fishingControls(fishingValue)));
    els.statusGrid.appendChild(statusCard("Timer", cards.timer || boolStatus(state.selected_config.timer_mode_enabled), toggleControl("timer_mode_enabled", "Timer")));
    els.statusGrid.appendChild(statusCard("Orb", cards.orb || boolStatus(state.selected_config.orb_mode_enabled), toggleControl("orb_mode_enabled", "Orb")));
    els.statusGrid.appendChild(statusCard("Placement", cards.placement || "OFF", placementControls()));
    els.statusGrid.appendChild(statusCard("Status", process.running ? process.state : "stopped"));
    return;
  }

  const items = [
    ["Script", script.name],
    ["Status", process.running ? process.state : "stopped"],
    ["Config", "READY"],
    ["Updates", state.update && state.update.available ? "UPDATE" : "OK"],
    ["Logs", "LIVE"],
  ];

  for (const [label, value] of items) {
    els.statusGrid.appendChild(statusCard(label, value));
  }
}

function statusCard(label, value, controls = null) {
  const card = document.createElement("article");
  card.className = `status-card ${toneClass(value)}`;
  card.innerHTML = `<span>${label}</span><strong>${String(value).toUpperCase()}</strong>`;
  if (controls) {
    card.appendChild(controls);
  }
  return card;
}

function fishingControls(currentValue) {
  const row = document.createElement("div");
  row.className = "card-controls segmented";
  for (const mode of ["trophy", "hype", "flay"]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = String(currentValue).toLowerCase() === mode ? "active" : "";
    button.textContent = mode;
    button.addEventListener("click", () => setRuntimeOption("start_mode", mode));
    row.appendChild(button);
  }
  return row;
}

function toggleControl(key, label) {
  const row = document.createElement("div");
  row.className = "card-controls";
  const enabled = Boolean(getByPath(state.selected_config, key));
  const button = document.createElement("button");
  button.type = "button";
  button.className = enabled ? "active" : "";
  button.textContent = enabled ? "On" : "Off";
  button.addEventListener("click", () => setRuntimeOption(key, !enabled));
  button.title = `${label} ${enabled ? "deaktivieren" : "aktivieren"}`;
  row.appendChild(button);
  return row;
}

function placementControls() {
  const row = document.createElement("div");
  row.className = "card-controls";
  const enabled = Boolean(state.selected_config.orb_mode_enabled);
  const queue = document.createElement("button");
  queue.type = "button";
  queue.textContent = "Queue";
  queue.disabled = !enabled;
  queue.addEventListener("click", () => setRuntimeOption("orb_mode_enabled", true));
  row.appendChild(queue);
  return row;
}

function boolStatus(value) {
  return value ? "ON" : "OFF";
}

function renderUpdate() {
  els.updateLine.textContent = state.update ? state.update.message : "Updates not checked.";
  els.installUpdateButton.disabled = !(state.update && state.update.available);
  els.updateStatus.textContent = state.update && state.update.available ? "Update available!" : "";
}

function renderChangelog() {
  const changelog = state.pending_changelog;
  if (!changelog) {
    els.changelogOverlay.classList.add("hidden");
    return;
  }
  const version = changelog.version || "new version";
  els.changelogTitle.textContent = `${changelog.name || "Sidechick"} ${version}`;
  els.changelogBody.textContent = changelog.body || "No changelog was provided for this release.";
  els.changelogOverlay.classList.remove("hidden");
}

function showSettingTooltip(event) {
  const help = event.currentTarget.dataset.help;
  if (!help) {
    return;
  }
  els.settingsTooltip.textContent = help;
  els.settingsTooltip.classList.remove("hidden");
  moveSettingTooltip(event);
}

function moveSettingTooltip(event) {
  if (els.settingsTooltip.classList.contains("hidden")) {
    return;
  }
  const offset = 14;
  const margin = 10;
  const rect = els.settingsTooltip.getBoundingClientRect();
  let left = event.clientX + offset;
  let top = event.clientY + offset;

  if (left + rect.width + margin > window.innerWidth) {
    left = event.clientX - rect.width - offset;
  }
  if (top + rect.height + margin > window.innerHeight) {
    top = event.clientY - rect.height - offset;
  }

  els.settingsTooltip.style.left = `${Math.max(margin, left)}px`;
  els.settingsTooltip.style.top = `${Math.max(margin, top)}px`;
}

function hideSettingTooltip() {
  els.settingsTooltip.classList.add("hidden");
}

function updateRuntimeButtons() {
  const runtime = processFor(state.selected_script);
  const running = runtime.running;
  els.startButton.disabled = running;
  els.pauseButton.disabled = !running;
  els.pauseButton.textContent = runtime.state === "paused" ? "Resume" : "Pause";
  els.stopButton.disabled = !running;
}

function appendLogs(lines) {
  if (!lines.length) {
    return;
  }
  els.logOutput.textContent += `${lines.join("\n")}\n`;
  els.logOutput.scrollTop = els.logOutput.scrollHeight;
}

function startCapture(input, multiple) {
  captureTarget = { input, multiple };
  els.captureOverlay.classList.remove("hidden");
}

function finishCapture(binding) {
  if (!captureTarget) {
    return;
  }
  if (captureTarget.multiple && binding) {
    const values = bindingList(captureTarget.input.value);
    if (!values.includes(binding)) {
      values.push(binding);
    }
    captureTarget.input.value = values.join(", ");
  } else {
    captureTarget.input.value = binding;
  }
  captureTarget = null;
  els.captureOverlay.classList.add("hidden");
}

function keyBinding(event) {
  const aliases = {
    Enter: "enter",
    Escape: "esc",
    " ": "space",
    Spacebar: "space",
    Backspace: "backspace",
    Tab: "tab",
    ",": "comma",
    "-": "minus",
    ".": "period",
    "/": "slash",
    "\\": "backslash",
    ";": "semicolon",
    "'": "apostrophe",
    "`": "backtick",
    "=": "equals",
    "[": "left bracket",
    "]": "right bracket",
    Control: "ctrl",
    Shift: "shift",
    Alt: "alt",
    AltGraph: "alt gr",
    Meta: "windows",
    ArrowLeft: "left",
    ArrowRight: "right",
    ArrowUp: "up",
    ArrowDown: "down",
    PageUp: "page up",
    PageDown: "page down",
    CapsLock: "caps lock",
    NumLock: "num lock",
    ScrollLock: "scroll lock",
    PrintScreen: "print screen",
    ContextMenu: "menu",
    Delete: "delete",
    Insert: "insert",
    Home: "home",
    End: "end",
    Pause: "pause",
  };
  const numpad = numpadBinding(event.code);
  if (numpad) {
    return numpad;
  }
  if (event.key === "Dead") {
    return deadKeyBinding(event.code);
  }
  return aliases[event.key] || event.key.toLowerCase();
}

function numpadBinding(code) {
  const map = {
    Numpad0: "num 0",
    Numpad1: "num 1",
    Numpad2: "num 2",
    Numpad3: "num 3",
    Numpad4: "num 4",
    Numpad5: "num 5",
    Numpad6: "num 6",
    Numpad7: "num 7",
    Numpad8: "num 8",
    Numpad9: "num 9",
    NumpadDecimal: "num .",
    NumpadDivide: "num /",
    NumpadMultiply: "num *",
    NumpadSubtract: "num -",
    NumpadAdd: "num +",
    NumpadEnter: "num enter",
    NumpadEqual: "num =",
  };
  return map[code] || "";
}

function deadKeyBinding(code) {
  const germanDeadKeys = {
    Backquote: "^",
    Equal: "\u00b4",
  };
  return germanDeadKeys[code] || "dead";
}

function bindingList(value) {
  return String(value || "")
    .split(",")
    .map(item => normalizeBinding(item))
    .filter(Boolean)
    .filter((item, index, items) => items.indexOf(item) === index);
}

function normalizeBinding(value) {
  const raw = String(value || "").trim().toLowerCase().replace(/_+/g, " ").replace(/\s+/g, " ");
  const compact = raw.replace(/\s+/g, "");
  const aliases = {
    left: "mouse:left",
    mouse1: "mouse:left",
    right: "mouse:right",
    mouse2: "mouse:right",
    middle: "mouse:middle",
    mouse3: "mouse:middle",
    x: "mouse:x",
    x1: "mouse:x",
    mouse4: "mouse:x",
    x2: "mouse:x2",
    mouse5: "mouse:x2",
    ",": "comma",
    comma: "comma",
    "-": "minus",
    minus: "minus",
    ".": "period",
    period: "period",
    dot: "period",
    "/": "slash",
    slash: "slash",
    "\\": "backslash",
    backslash: "backslash",
    ";": "semicolon",
    semicolon: "semicolon",
    "'": "apostrophe",
    apostrophe: "apostrophe",
    quote: "apostrophe",
    "`": "backtick",
    backtick: "backtick",
    grave: "backtick",
    "=": "equals",
    equals: "equals",
    "[": "left bracket",
    leftbracket: "left bracket",
    "]": "right bracket",
    rightbracket: "right bracket",
    escape: "esc",
    control: "ctrl",
    strg: "ctrl",
    altgraph: "alt gr",
    altgr: "alt gr",
    windows: "windows",
    win: "windows",
    meta: "windows",
    cmd: "windows",
    command: "windows",
    pageup: "page up",
    pagedown: "page down",
    capslock: "caps lock",
    numlock: "num lock",
    scrolllock: "scroll lock",
    printscreen: "print screen",
    contextmenu: "menu",
    arrowleft: "left",
    arrowright: "right",
    arrowup: "up",
    arrowdown: "down",
    numpad0: "num 0",
    numpad1: "num 1",
    numpad2: "num 2",
    numpad3: "num 3",
    numpad4: "num 4",
    numpad5: "num 5",
    numpad6: "num 6",
    numpad7: "num 7",
    numpad8: "num 8",
    numpad9: "num 9",
    num0: "num 0",
    num1: "num 1",
    num2: "num 2",
    num3: "num 3",
    num4: "num 4",
    num5: "num 5",
    num6: "num 6",
    num7: "num 7",
    num8: "num 8",
    num9: "num 9",
    numpaddecimal: "num .",
    numpaddivide: "num /",
    numpadmultiply: "num *",
    numpadsubtract: "num -",
    numpadadd: "num +",
    numpadenter: "num enter",
    numpadequal: "num =",
  };
  if (!raw || raw === "none" || raw === "off") {
    return "";
  }
  return aliases[raw] || aliases[compact] || raw;
}

function getByPath(object, path) {
  return path.split(".").reduce((value, key) => value && value[key], object);
}

function setByPath(object, path, value) {
  const parts = path.split(".");
  let current = object;
  for (let index = 0; index < parts.length - 1; index += 1) {
    current = current[parts[index]];
  }
  current[parts[parts.length - 1]] = value;
}

function toneClass(value) {
  const text = String(value).toLowerCase();
  if (["on", "running", "ready", "ok", "flay", "hype", "trophy", "live"].includes(text)) {
    return "tone-good";
  }
  if (["pending", "paused", "update"].includes(text)) {
    return "tone-warn";
  }
  if (["off", "stopped", "unknown"].includes(text)) {
    return "tone-off";
  }
  return "tone-neutral";
}

function toggleSidebar() {
  document.body.classList.toggle("sidebar-collapsed");
  els.sidebarToggle.textContent = document.body.classList.contains("sidebar-collapsed") ? ">" : "<";
}
