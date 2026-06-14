const $ = (id) => document.getElementById(id);

const urlInput = $("url");
const fetchBtn = $("fetch-btn");
const inputError = $("input-error");
const preview = $("preview");
const thumb = $("thumb");
const titleInput = $("title");
const artistInput = $("artist");
const durationEl = $("duration");
const addBtn = $("add-btn");
const progress = $("progress");
const progressBar = $("progress-bar");
const progressMsg = $("progress-msg");

let currentMeta = null;

function fmtDuration(s) {
  if (!s) return "";
  const m = Math.floor(s / 60), sec = String(s % 60).padStart(2, "0");
  return `${m}:${sec}`;
}

function showError(msg) {
  inputError.textContent = msg;
  inputError.hidden = false;
}
function clearError() { inputError.hidden = true; }

async function refreshStatus() {
  const el = $("rb-status");
  try {
    const r = await fetch("/api/status");
    const { rekordbox_running } = await r.json();
    el.className = "rb-status " + (rekordbox_running ? "running" : "closed");
    el.querySelector(".label").textContent = rekordbox_running
      ? "rekordbox open — close to add" : "rekordbox closed — ready";
  } catch {
    el.querySelector(".label").textContent = "offline";
  }
}

async function fetchMeta() {
  const url = urlInput.value.trim();
  if (!url) return showError("Paste a YouTube link first.");
  clearError();
  fetchBtn.disabled = true;
  fetchBtn.textContent = "Fetching…";
  try {
    const r = await fetch("/api/probe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    currentMeta = data;
    thumb.src = data.thumbnail || "";
    titleInput.value = data.title || "";
    artistInput.value = data.artist || "";
    durationEl.textContent = data.duration ? `Duration ${fmtDuration(data.duration)}` : "";
    preview.hidden = false;
    progress.hidden = true;
    addBtn.disabled = false;
    addBtn.querySelector(".btn-text").textContent = "Add to Rekordbox";
  } catch (e) {
    showError("Couldn't read that link: " + e.message);
  } finally {
    fetchBtn.disabled = false;
    fetchBtn.textContent = "Fetch";
  }
}

function startAdd() {
  if (!currentMeta) return;
  addBtn.disabled = true;
  addBtn.querySelector(".btn-text").textContent = "Working…";
  progress.hidden = false;
  progressBar.style.width = "0%";
  progressMsg.className = "progress-msg";
  progressMsg.textContent = "Starting…";

  fetch("/api/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: urlInput.value.trim(),
      title: titleInput.value.trim(),
      artist: artistInput.value.trim(),
      thumbnail: currentMeta.thumbnail,
    }),
  })
    .then((r) => r.json())
    .then(({ job_id }) => listen(job_id))
    .catch((e) => fail(e.message));
}

function listen(jobId) {
  const es = new EventSource(`/api/events/${jobId}`);
  es.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    if (d.stage === "error") {
      fail(d.message);
      es.close();
      return;
    }
    progressBar.style.width = (d.percent || 0) + "%";
    progressMsg.textContent = d.message;
    if (d.stage === "done") {
      progressBar.style.width = "100%";
      progressMsg.className = "progress-msg done";
      addBtn.querySelector(".btn-text").textContent = "Add another";
      addBtn.disabled = false;
      loadRecent();
      es.close();
    }
  };
  es.onerror = () => { es.close(); };
}

function fail(msg) {
  progressMsg.className = "progress-msg error";
  progressMsg.textContent = "✗ " + msg;
  addBtn.disabled = false;
  addBtn.querySelector(".btn-text").textContent = "Try again";
  refreshStatus();
}

async function loadRecent() {
  const list = $("recent-list");
  const r = await fetch("/api/recent");
  const items = await r.json();
  if (!items.length) return;
  list.innerHTML = items
    .map(
      (it) => `
    <div class="recent-item">
      <img src="${it.thumbnail || ""}" alt="" />
      <div class="ri-meta">
        <div class="ri-title">${escapeHtml(it.title)}</div>
        <div class="ri-artist">${escapeHtml(it.artist)}</div>
      </div>
      <div class="ri-badge">${escapeHtml(it.playlist)}</div>
    </div>`
    )
    .join("");
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

fetchBtn.addEventListener("click", fetchMeta);
urlInput.addEventListener("keydown", (e) => { if (e.key === "Enter") fetchMeta(); });
addBtn.addEventListener("click", startAdd);

refreshStatus();
setInterval(refreshStatus, 5000);
loadRecent();
