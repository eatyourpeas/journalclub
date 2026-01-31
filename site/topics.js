const API_BASE =
  API_BASE_URL == "__API_BASE_URL__"
    ? "http://localhost:8000/api/papers"
    : `${API_BASE_URL}/api/papers`;

const topicsContainer = document.getElementById("topicsContainer");
const createBtn = document.getElementById("createTopicBtn");
const submitCreateBtn = document.getElementById("submitCreateBtn");
const papersListEl = document.getElementById("papersList");
const topicNameInput = document.getElementById("topicNameInput");

async function fetchTopics() {
  try {
    const res = await fetch(`${API_BASE}/topics`);
    if (!res.ok) throw new Error("Failed to load topics");
    const data = await res.json();
    renderTopics(data);
  } catch (err) {
    console.error(err);
    topicsContainer.innerHTML = `<div class="alert alert-error">Failed to load topics: ${err.message}</div>`;
  }
}

async function fetchActivePapers() {
  try {
    const res = await fetch(`${API_BASE}/active`);
    if (!res.ok) throw new Error("Failed to load active papers");
    const data = await res.json();
    return data.papers || [];
  } catch (err) {
    console.error(err);
    return [];
  }
}

function renderTopics({ topics }) {
  if (!topics || topics.length === 0) {
    topicsContainer.innerHTML = `
      <div class="text-center py-12">
        <p class="text-lg text-base-content/70">No topics created yet.</p>
        <button id="createFirstBtn" class="btn btn-primary mt-4">Create Topic</button>
      </div>
    `;

    const btn = document.getElementById("createFirstBtn");
    if (btn) btn.addEventListener("click", openCreateModal);
    return;
  }

  topicsContainer.innerHTML = `<div class="space-y-4">${topics
    .map(
      (t) => `
    <div class="card bg-base-200">
      <div class="card-body">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="card-title">${t.name}</h3>
            <p class="text-sm text-base-content/70">${t.paper_count} papers • ${new Date(
              t.created_at,
            ).toLocaleString()}</p>
          </div>
          <div class="flex gap-2">
            <button class="btn btn-primary btn-sm" onclick="playTopicAudio('${t.topic_id}')">Play</button>
            <button class="btn btn-ghost btn-sm" onclick="deleteTopic('${t.topic_id}')">Delete</button>
          </div>
        </div>
      </div>
    </div>
  `,
    )
    .join("")}</div>`;
}

function openCreateModal() {
  // populate papers list
  document.getElementById("create-topic-modal").checked = true;
  loadPapersIntoModal();
}

async function loadPapersIntoModal() {
  papersListEl.innerHTML = `<div class="text-center py-6"><span class="loading loading-spinner loading-lg text-primary"></span></div>`;
  const papers = await fetchActivePapers();
  if (!papers || papers.length === 0) {
    papersListEl.innerHTML = `<div class="text-sm text-base-content/70">No active papers to add. Upload a paper first.</div>`;
    return;
  }

  papersListEl.innerHTML = papers
    .map(
      (p) => `
    <label class="flex items-center gap-2 p-2 rounded hover:bg-base-100">
      <input type="checkbox" class="paper-checkbox" data-filename="${p.filename}" />
      <div class="flex-1">
        <div class="font-semibold">${p.title}</div>
        <div class="text-xs text-base-content/70">${p.authors ? p.authors.join(', ') : ''}</div>
        <div class="text-xs text-base-content/70">${p.filename} • ${p.pages} pages</div>
      </div>
      <div class="flex-none">
        <button class="btn btn-ghost btn-sm" onclick="copyCitation('${p.filename}')">Copy citation</button>
      </div>
    </label>
  `,
    )
    .join("");
}

async function createTopic() {
  const name = topicNameInput.value.trim();
  if (!name) return alert("Please enter a topic name");

  const checked = Array.from(
    document.querySelectorAll(".paper-checkbox:checked"),
  ).map((el) => el.dataset.filename);

  if (checked.length < 1) return alert("Select at least one paper");
  if (checked.length > 5) return alert("Maximum 5 papers");

  try {
    submitCreateBtn.disabled = true;
    const res = await fetch(`${API_BASE}/topics`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic_name: name, filenames: checked }),
    });
    if (!res.ok) throw new Error(`Create failed: ${res.status}`);
    await fetchTopics();
    // close modal
    document.getElementById("create-topic-modal").checked = false;
    topicNameInput.value = "";
  } catch (err) {
    alert("Error creating topic: " + err.message);
    console.error(err);
  } finally {
    submitCreateBtn.disabled = false;
  }
}

// copy citation helper: look up loaded papers and copy citation or filename
function copyCitation(filename) {
  try {
    // find checkbox element and its container to extract displayed text
    const el = document.querySelector(`.paper-checkbox[data-filename="${filename}"]`);
    if (!el) return;
    // attempt to find sibling citation text in the same label
    const label = el.closest('label');
    const citationEl = label.querySelector('.text-xs.text-base-content\/70');
    let text = citationEl ? citationEl.textContent.trim() : filename;
    navigator.clipboard.writeText(text).then(() => {
      alert('Citation copied to clipboard');
    });
  } catch (e) {
    console.error(e);
  }
}

async function deleteTopic(id) {
  if (!confirm("Delete this topic?")) return;
  try {
    const res = await fetch(`${API_BASE}/topics/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    await fetchTopics();
  } catch (err) {
    alert("Error deleting topic: " + err.message);
  }
}

function playTopicAudio(id) {
  // open in new tab for streaming
  window.open(`${API_BASE}/topics/${id}/read_aloud`, "_blank");
}

// Attach handlers
createBtn.addEventListener("click", openCreateModal);
submitCreateBtn.addEventListener("click", createTopic);

// Expose functions for inline onclick handlers
window.playTopicAudio = playTopicAudio;
window.deleteTopic = deleteTopic;

// Load initial list
fetchTopics();
