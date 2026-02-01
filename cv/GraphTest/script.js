const LOG_PATH = "../pose_log.jsonl";

function showError(msg) {
  const loading = document.getElementById("loading");
  const errEl = document.getElementById("error");
  if (loading) loading.style.display = "none";
  if (errEl) {
    errEl.textContent = msg;
    errEl.style.display = "block";
  }
}

function showContent() {
  const loading = document.getElementById("loading");
  const controls = document.getElementById("controls");
  if (loading) loading.style.display = "none";
  if (controls) controls.style.display = "block";
}

const LABEL_MAP = {
  right_elbow: "Right arm (elbow)",
  left_elbow: "Left arm (elbow)",
  right_knee: "Right leg (knee)",
  left_knee: "Left leg (knee)",
  right_shoulder: "Right shoulder",
  left_shoulder: "Left shoulder",
  right_hip: "Right hip",
  left_hip: "Left hip",
  right_ankle: "Right ankle angle",
  left_ankle: "Left ankle angle",
  right_ankle_roll: "Right ankle roll",
  left_ankle_roll: "Left ankle roll",
  right_ankle_yaw: "Right ankle yaw",
  left_ankle_yaw: "Left ankle yaw",
  torso: "Torso",
};

// Default to elbows (often have data); script will prefer keys that have at least one value
const FALLBACK_SELECTED = new Set(["right_elbow", "left_elbow"]);

let chart = null;
let time = [];
let samples = [];
let angleKeys = [];

fetch(LOG_PATH)
  .then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.text();
  })
  .then((text) => {
    const lines = text.trim().split("\n").filter(Boolean);
    if (lines.length === 0) {
      showError("pose_log.jsonl is empty. Run a workout or cv-mp4f to generate pose data.");
      return;
    }
    for (const line of lines) {
      const obj = JSON.parse(line);
      time.push(obj.timestamp_ms / 1000);
      samples.push(obj.angles || {});
    }
    angleKeys = discoverKeys(samples);
    // Prefer keys that have at least one non-null value so the graph isn't empty
    const keysWithData = angleKeys.filter((k) =>
      samples.some((s) => s[k] != null)
    );
    const defaultSelected = keysWithData.length > 0
      ? new Set(keysWithData.slice(0, 4))
      : FALLBACK_SELECTED;
    buildControls(angleKeys, defaultSelected);
    showContent();
    plotSelected();
  })
  .catch((err) => {
    showError(
      "Could not load pose_log.jsonl.\n\n" +
      "Open this page via a local server (fetch from file:// is blocked by browsers).\n\n" +
      "From the cv/ folder run:\n  python -m http.server 8080\n" +
      "Then visit: http://localhost:8080/GraphTest/\n\n" +
      "Error: " + (err.message || String(err))
    );
  });

function discoverKeys(sampleList) {
  const keys = new Set();
  for (const s of sampleList) {
    Object.keys(s || {}).forEach(k => keys.add(k));
  }
  return Array.from(keys).sort();
}

function buildControls(keys, defaultSelected) {
  const container = document.getElementById("angleControls");
  if (!container) return;
  container.innerHTML = "";
  const useDefault = defaultSelected || FALLBACK_SELECTED;
  keys.forEach((key) => {
    const label = LABEL_MAP[key] || key;
    const wrapper = document.createElement("label");
    wrapper.style.display = "block";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = key;
    checkbox.checked = useDefault.has(key);
    checkbox.addEventListener("change", plotSelected);
    wrapper.appendChild(checkbox);
    wrapper.appendChild(document.createTextNode(` ${label}`));
    container.appendChild(wrapper);
  });
}

function getSelectedKeys() {
  return Array.from(document.querySelectorAll("#angleControls input[type=checkbox]:checked"))
    .map(el => el.value);
}

function buildDatasets(selected) {
  const palette = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    "#bcbd22", "#17becf"
  ];
  return selected.map((key, idx) => {
    const data = samples.map(s => {
      const v = s[key];
      return v === null || v === undefined ? null : v;
    });
    return {
      label: `${LABEL_MAP[key] || key}`,
      data,
      borderColor: palette[idx % palette.length],
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.15,
      spanGaps: true
    };
  });
}

function plotSelected() {
  const canvas = document.getElementById("angleChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const selected = getSelectedKeys();
  const datasets = buildDatasets(selected);

  if (chart) {
    chart.data.labels = time;
    chart.data.datasets = datasets;
    chart.update();
    return;
  }

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: time,
      datasets
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: { display: true, text: "Time (s)" }
        },
        y: {
          title: { display: true, text: "Angle (°)" },
          min: 0,
          max: 180
        }
      }
    }
  });
}
