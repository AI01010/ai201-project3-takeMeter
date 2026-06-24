"use strict";
const TAX = window.TAXONOMY;
const $ = (id) => document.getElementById(id);

// label -> keyboard keys
const BUTTONS = [
  { label: "analysis", keys: ["1", "a"], desc: "stats / tactics / argument" },
  { label: "hot_take", keys: ["2", "h"], desc: "bold claim, no evidence" },
  { label: "reaction", keys: ["3", "r"], desc: "in-the-moment emotion" },
  { label: "mixed",    keys: ["4", "m"], desc: "real blend, neither dominates" },
  { label: "skip",     keys: ["0", "s"], desc: "unreadable / off-topic" },
];
const KEYMAP = {};
BUTTONS.forEach((b) => b.keys.forEach((k) => (KEYMAP[k] = b.label)));

let examples = [];
let i = 0;

// build label buttons
const lb = $("label-buttons");
BUTTONS.forEach((b) => {
  const el = document.createElement("button");
  el.className = "label-btn";
  el.dataset.label = b.label;
  el.innerHTML = `${b.label.replace("_", " ")} <span class="kbd">${b.keys[0]}</span><small>${b.desc}</small>`;
  el.onclick = () => setLabel(b.label);
  lb.appendChild(el);
});

function toast(msg) {
  let t = document.querySelector(".toast");
  if (!t) { t = document.createElement("div"); t.className = "toast"; document.body.appendChild(t); }
  t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1100);
}

async function load() {
  const r = await fetch("/api/examples");
  const data = await r.json();
  examples = data.examples;
  // jump to first unlabeled so you resume where you left off
  const firstUnlabeled = examples.findIndex((e) => !e.label);
  i = firstUnlabeled === -1 ? 0 : firstUnlabeled;
  render();
}

function counts() {
  const c = {};
  examples.forEach((e) => { if (e.label) c[e.label] = (c[e.label] || 0) + 1; });
  return c;
}

function renderStats() {
  const c = counts();
  const labeled = Object.values(c).reduce((a, b) => a + b, 0);
  const total = examples.length;
  $("progress-text").textContent = `${labeled} / ${total} labeled`;
  $("progress-fill").style.width = total ? `${(labeled / total) * 100}%` : "0";

  const pills = $("counts");
  pills.innerHTML = "";
  [...BUTTONS.map((b) => b.label)].forEach((l) => {
    const span = document.createElement("span");
    span.className = "count-pill";
    span.innerHTML = `<b class="lab-${l}">${l.replace("_", " ")}</b>: <b>${c[l] || 0}</b>`;
    pills.appendChild(span);
  });
}

function render() {
  if (!examples.length) { $("card-text").textContent = "No examples found. Run data/build_dataset.py first."; return; }
  const e = examples[i];
  $("card-index").textContent = `#${i + 1} of ${examples.length} · id ${e.id}`;
  $("card-source").textContent = e.source || "";
  $("card-text").textContent = e.text;
  $("card-notes").value = e.notes || "";
  const cur = $("card-current");
  cur.textContent = e.label ? e.label.replace("_", " ") : "unlabeled";
  cur.className = "cur-label" + (e.label ? " lab-" + e.label : "");
  // highlight selected button
  document.querySelectorAll(".label-btn").forEach((btn) =>
    btn.classList.toggle("sel", btn.dataset.label === e.label));
  renderStats();
}

async function setLabel(label) {
  const e = examples[i];
  const notes = $("card-notes").value.trim();
  e.label = label; e.notes = notes;
  render();
  try {
    await fetch("/api/label", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: e.id, label, notes }),
    });
  } catch (_) { toast("⚠ save failed (offline?)"); }
  // auto-advance to next unlabeled (or just next)
  setTimeout(advanceSmart, 90);
}

function advanceSmart() {
  const next = nextUnlabeledFrom(i + 1);
  if (next === -1) {
    if (i < examples.length - 1) i++;
    else { toast("🎉 all examples labeled — Export your CSV"); }
  } else { i = next; }
  render();
}

function nextUnlabeledFrom(start) {
  for (let k = start; k < examples.length; k++) if (!examples[k].label) return k;
  for (let k = 0; k < start && k < examples.length; k++) if (!examples[k].label) return k;
  return -1;
}

function go(delta) { i = (i + delta + examples.length) % examples.length; render(); }

$("prev-btn").onclick = () => go(-1);
$("next-btn").onclick = () => go(1);
$("next-unlabeled-btn").onclick = () => {
  const n = nextUnlabeledFrom(i + 1);
  if (n === -1) toast("no unlabeled examples left"); else { i = n; render(); }
};

// persist notes when edited then navigating
$("card-notes").addEventListener("change", async () => {
  const e = examples[i];
  if (!e.label) return; // only persist notes once a label exists
  e.notes = $("card-notes").value.trim();
  await fetch("/api/label", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: e.id, label: e.label, notes: e.notes }),
  });
});

document.addEventListener("keydown", (ev) => {
  if (ev.target.tagName === "INPUT" || ev.target.tagName === "TEXTAREA") {
    if (ev.key === "Escape") ev.target.blur();
    return; // don't hijack typing in the notes field
  }
  if (ev.key in KEYMAP) { ev.preventDefault(); setLabel(KEYMAP[ev.key]); }
  else if (ev.key === "ArrowLeft") { ev.preventDefault(); go(-1); }
  else if (ev.key === "ArrowRight") { ev.preventDefault(); go(1); }
  else if (ev.key === "Tab") { ev.preventDefault(); $("next-unlabeled-btn").click(); }
});

load();
