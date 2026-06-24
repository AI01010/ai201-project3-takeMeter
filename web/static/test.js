"use strict";
const TAX = window.TAXONOMY;
const LABELS = TAX.train_labels; // [analysis, hot_take, reaction, mixed]

const $ = (id) => document.getElementById(id);
const post = $("post");
const result = $("result");

const EXAMPLES = [
  "Haaland's npxG is 0.78 per 90 but he's finishing at 1.05. That overperformance regresses almost every time.",
  "Pep is overrated, anyone could win with that budget. Change my mind.",
  "97th-minute winner in the derby I AM SHAKING I cannot breathe right now!!!",
  "Gutted we lost but the xG was 0.4 to 2.1, we got battered, same broken midfield all season.",
];

// render the "try" chips
const chips = $("example-chips");
EXAMPLES.forEach((ex) => {
  const c = document.createElement("span");
  c.className = "chip";
  c.textContent = ex.length > 42 ? ex.slice(0, 40) + "…" : ex;
  c.title = ex;
  c.onclick = () => { post.value = ex; post.focus(); };
  chips.appendChild(c);
});

// render definitions
const defs = $("defs");
LABELS.forEach((l) => {
  const li = document.createElement("li");
  li.innerHTML = `<b class="lab-${l}">${l.replace("_", " ")}</b> — ${TAX.definitions[l]}`;
  defs.appendChild(li);
});

async function classify() {
  const text = post.value.trim();
  if (!text) { post.focus(); return; }
  const btn = $("classify-btn");
  btn.disabled = true; btn.textContent = "Classifying…";
  try {
    const r = await fetch("/api/classify", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await r.json();
    if (!data.ok) throw new Error(data.error || "error");
    render(data);
  } catch (e) {
    $("result-note").textContent = "Error: " + e.message;
    result.classList.remove("hidden");
  } finally {
    btn.disabled = false; btn.innerHTML = 'Classify <span class="kbd">Ctrl ↵</span>';
  }
}

function render(data) {
  const label = data.label;
  const vl = $("verdict-label");
  vl.textContent = label.replace("_", " ");
  vl.className = "verdict-label lab-" + label;
  $("verdict-conf").textContent =
    data.confidence != null ? `${(data.confidence * 100).toFixed(1)}% confidence` : "label only";

  // bars sorted high→low
  const bars = $("bars");
  bars.innerHTML = "";
  const entries = LABELS.map((l) => [l, data.scores[l] ?? 0]).sort((a, b) => b[1] - a[1]);
  for (const [l, v] of entries) {
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML =
      `<span class="bar-name">${l.replace("_", " ")}</span>` +
      `<span class="bar-track"><span class="bar-fill bg-${l}" style="width:${(v * 100).toFixed(1)}%"></span></span>` +
      `<span class="bar-val">${(v * 100).toFixed(0)}%</span>`;
    bars.appendChild(row);
  }
  $("result-note").textContent = data.note || "";
  result.classList.remove("hidden");
}

$("classify-btn").onclick = classify;
$("clear-btn").onclick = () => { post.value = ""; result.classList.add("hidden"); post.focus(); };
post.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); classify(); }
});
post.focus();
