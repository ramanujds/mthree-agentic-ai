// Study Buddy UI — plain fetch calls against the FastAPI backend.
// See notes/09-fastapi-essentials.md for the API side of this contract.

const toast = document.getElementById("toast");

function showToast(message, ok = false) {
  toast.textContent = message;
  toast.className = `toast ${ok ? "success" : ""}`;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.add("hidden"), 3000);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.status === 204 ? null : res.json();
}

// --- Notes ---------------------------------------------------------------

function renderNotes(notes) {
  const list = document.getElementById("notes-list");
  list.innerHTML = "";
  if (notes.length === 0) {
    list.innerHTML = "<li>No notes yet.</li>";
    return;
  }
  for (const note of notes) {
    const li = document.createElement("li");
    const when = new Date(note.created_at).toLocaleString();
    li.innerHTML = `
      <div class="item-topic">${note.topic}</div>
      <div>${note.content}</div>
      <div class="item-meta">${when}</div>
    `;
    list.appendChild(li);
  }
}

function renderTopicCounts(counts) {
  const row = document.getElementById("topic-counts");
  row.innerHTML = "";
  for (const { topic, count } of counts) {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = `${topic} (${count})`;
    row.appendChild(span);
  }
}

async function refreshNotes() {
  const [notes, counts] = await Promise.all([
    api("/notes"),
    api("/notes/topic-counts"),
  ]);
  renderNotes(notes);
  renderTopicCounts(counts);
}

document.getElementById("note-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const topic = document.getElementById("note-topic").value.trim();
  const content = document.getElementById("note-content").value.trim();
  try {
    await api("/notes", { method: "POST", body: JSON.stringify({ topic, content }) });
    e.target.reset();
    showToast("Note added", true);
    await refreshNotes();
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("note-search-btn").addEventListener("click", async () => {
  const q = document.getElementById("note-search").value.trim();
  if (!q) return refreshNotes();
  try {
    const notes = await api(`/notes/search?q=${encodeURIComponent(q)}`);
    renderNotes(notes);
  } catch (err) {
    showToast(err.message);
  }
});

document.getElementById("note-clear-btn").addEventListener("click", () => {
  document.getElementById("note-search").value = "";
  refreshNotes();
});

// --- Scores ----------------------------------------------------------------

function renderStats(stats) {
  const summary = document.getElementById("stats-summary");
  const overall = stats.overall_mean_percent;
  summary.innerHTML = `
    <div class="stat-card">Overall<br/><strong>${overall === null ? "—" : overall + "%"}</strong></div>
    <div class="stat-card">Attempts<br/><strong>${stats.total_attempts}</strong></div>
    <div class="stat-card">Best<br/><strong>${stats.best_topic ?? "—"}</strong></div>
    <div class="stat-card">Worst<br/><strong>${stats.worst_topic ?? "—"}</strong></div>
  `;

  const tbody = document.querySelector("#stats-table tbody");
  tbody.innerHTML = "";
  for (const row of stats.by_topic) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.topic}</td><td>${row.mean_percent}%</td><td>${row.attempts}</td>`;
    tbody.appendChild(tr);
  }
}

async function refreshStats() {
  const stats = await api("/scores/stats");
  renderStats(stats);
}

document.getElementById("score-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const topic = document.getElementById("score-topic").value.trim();
  const score = Number(document.getElementById("score-value").value);
  const max_score = Number(document.getElementById("score-max").value);
  try {
    await api("/scores", { method: "POST", body: JSON.stringify({ topic, score, max_score }) });
    e.target.reset();
    showToast("Score logged", true);
    await refreshStats();
  } catch (err) {
    showToast(err.message);
  }
});

// --- Export ------------------------------------------------------------------

document.getElementById("export-btn").addEventListener("click", async () => {
  const resultEl = document.getElementById("export-result");
  resultEl.textContent = "Exporting...";
  try {
    const result = await api("/reports/export", { method: "POST" });
    resultEl.innerHTML = `Saved:<br/>• ${result.json_path}<br/>• ${result.csv_path}`;
    showToast("Report exported", true);
  } catch (err) {
    resultEl.textContent = "";
    showToast(err.message);
  }
});

// --- Init ----------------------------------------------------------------

refreshNotes().catch((err) => showToast(err.message));
refreshStats().catch((err) => showToast(err.message));
