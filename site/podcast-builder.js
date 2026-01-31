const API_BASE =
  API_BASE_URL == "__API_BASE_URL__"
    ? "http://localhost:8000/api/papers"
    : `${API_BASE_URL}/api/papers`;

const papersList = document.getElementById("papersList");
const buildBtn = document.getElementById("buildBtn");
const episodeTitle = document.getElementById("episodeTitle");
const playerArea = document.getElementById("playerArea");

async function loadPapers() {
  papersList.innerHTML = `<div class="text-center py-6"><span class="loading loading-spinner loading-lg text-primary"></span></div>`;
  try {
    const res = await fetch(`${API_BASE}/active`);
    if (!res.ok) throw new Error("Failed to load active papers");
    const { papers } = await res.json();
    if (!papers || papers.length === 0) {
      papersList.innerHTML = `<div class="text-sm text-base-content/70">No active papers available. Upload first.</div>`;
      return;
    }

    papersList.innerHTML = papers
      .map(
        (p) => `
      <label class="flex items-center gap-2 p-2 rounded hover:bg-base-100">
        <input type="checkbox" class="episode-checkbox" data-filename="${p.filename}" />
        <div class="flex-1">
          <div class="font-semibold">${p.title}</div>
          <div class="text-xs text-base-content/70">${p.authors ? p.authors.join(', ') : ''}</div>
          <div class="text-xs text-base-content/70">${p.filename} • ${p.pages} pages • ${p.hours_remaining}h left</div>
        </div>
        <div class="flex-none">
          <button class="btn btn-ghost btn-sm" onclick="copyCitation('${p.filename}')">Copy citation</button>
        </div>
      </label>
    `,
      )
      .join("");
  } catch (err) {
    console.error(err);
    papersList.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
  }
}

async function buildEpisode() {
  const title = (episodeTitle.value || "Custom Episode").trim();
  const chosen = Array.from(
    document.querySelectorAll(".episode-checkbox:checked"),
  ).map((c) => c.dataset.filename);
  if (chosen.length === 0) return alert("Select at least one paper");
  if (chosen.length > 5) return alert("Maximum 5 papers per episode");

  try {
    buildBtn.disabled = true;
    // Reuse the topics create endpoint to group files server-side
    const res = await fetch(`${API_BASE}/topics`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic_name: title, filenames: chosen }),
    });
    if (!res.ok) throw new Error("Failed to create episode");
    const data = await res.json();
    // Open the audio in a new tab so streaming works reliably
    window.open(`${API_BASE}/topics/${data.topic_id}/read_aloud`, "_blank");
  } catch (err) {
    alert("Error building episode: " + err.message);
  } finally {
    buildBtn.disabled = false;
  }
}

buildBtn.addEventListener("click", buildEpisode);

loadPapers();

function copyCitation(filename) {
  try {
    const el = document.querySelector(`.episode-checkbox[data-filename="${filename}"]`);
    if (!el) return;
    const label = el.closest('label');
    const citationEl = label.querySelector('.text-xs.text-base-content\/70');
    let text = citationEl ? citationEl.textContent.trim() : filename;
    navigator.clipboard.writeText(text).then(() => alert('Citation copied to clipboard'));
  } catch (e) {
    console.error(e);
  }
}
