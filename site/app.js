const API_BASE =
  API_BASE_URL == "__API_BASE_URL__"
    ? "http://localhost:8000/api/papers"
    : `${API_BASE_URL}/api/papers`;

const stageContainer = document.getElementById("stageContainer");
let currentFilename = null;
let isUploading = false;
let pollInterval = null;

function renderUploadView() {
  stageContainer.innerHTML = `
    <div class="grid grid-cols-1 gap-4">
      <label for="fileInput" id="uploadBox" class="border-2 border-dashed border-primary/30 rounded-box p-8 text-center bg-base-200/50 hover:bg-base-200 cursor-pointer block transition-colors">
        <input type="file" id="fileInput" accept=".pdf" class="hidden">
        <div class="flex flex-col items-center gap-2">
          <svg class="w-12 h-12 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
          <p class="text-lg font-semibold text-primary">Click to upload Journal article as PDF</p>
        </div>
      </label>

      <div class="flex gap-2 items-center">
        <select id="idTypeSelect" class="select select-bordered w-40">
          <option value="pmid" selected>PMID</option>
          <option value="pmcid">PMCID</option>
          <option value="doi">DOI</option>
        </select>
        <input id="pmidInput" type="text" placeholder="Enter ID (e.g. 12345678 or PMC12779737 or 10.1000/xyz)" class="input input-bordered w-full" />
        <button id="importPmidBtn" class="btn btn-primary">Import</button>
      </div>
    </div>`;

  const input = document.getElementById("fileInput");
  input.addEventListener("change", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.target.files[0] && !isUploading) uploadFile(e.target.files[0]);
  });

  const importBtn = document.getElementById("importPmidBtn");
  importBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    const id = document.getElementById("pmidInput").value.trim();
    const idType = document.getElementById("idTypeSelect").value;
    if (!id) return;
    stageContainer.innerHTML = `<div class="py-12 text-center"><span class="loading loading-spinner loading-lg text-primary"></span><p class="mt-4">Checking PubMed and fetching full text...</p></div>`;
    try {
      const resp = await fetch(`${API_BASE}/import_pmid`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_type: idType, id }),
      });
      if (!resp.ok) throw new Error(`Import failed: ${resp.status}`);
      const data = await resp.json();
      if (!data || !data.filename) throw new Error("No filename returned");
      currentFilename = data.filename;
      renderActionView(currentFilename, data.total_pages || 0);
    } catch (err) {
      console.error("Import error", err);
      stageContainer.innerHTML = `<div class="alert alert-error"><span>Error: ${err.message}</span></div><button id="backBtn" class="btn btn-ghost mt-4">Back</button>`;
      document
        .getElementById("backBtn")
        .addEventListener("click", () => renderUploadView());
    }
  });
}

function renderActionView(filename, pages) {
  stageContainer.innerHTML = `
    <div class="alert alert-success shadow-sm mb-4"><span><strong>Ready:</strong> ${filename} (${pages} pages)</span></div>
    <div class="flex gap-4">
      <div class="flex gap-2 items-center flex-1">
        <select id="listenModeSelect" class="select select-bordered w-full">
          <option value="full" selected>Full Read</option>
          <option value="summary">Summary</option>
          <option value="podcast">Podcast</option>
        </select>
        <button id="listenBtn" class="btn btn-secondary">Listen</button>
        <button id="readBtn" class="btn btn-outline">Read</button>
      </div>
      <button id="resetBtn" class="btn btn-ghost">Reset</button>
    </div>
    <div id="resultArea" class="mt-6 hidden"></div>`;

  document.getElementById("listenBtn").addEventListener("click", (e) => {
    e.preventDefault();
    const mode = document.getElementById("listenModeSelect").value;
    handleReadAloud(mode);
  });
  document.getElementById("readBtn").addEventListener("click", (e) => {
    e.preventDefault();
    const mode = document.getElementById("listenModeSelect").value;
    handleRead(mode);
  });
  document.getElementById("resetBtn").addEventListener("click", (e) => {
    e.preventDefault();
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    renderUploadView();
  });
}

async function uploadFile(file) {
  isUploading = true;
  stageContainer.innerHTML = `<div class="py-20 text-center"><span class="loading loading-spinner loading-lg text-primary"></span><p class="mt-4 text-base-content">Uploading and Parsing...</p></div>`;
  const form = new FormData();
  form.append("file", file);
  try {
    const resp = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: form,
    });
    if (!resp.ok) throw new Error(`Upload Failed: ${resp.status}`);
    const data = await resp.json();
    currentFilename = data.filename;
    renderActionView(currentFilename, data.total_pages || 0);
  } catch (err) {
    console.error("Upload error", err);
    stageContainer.innerHTML = `<div class="alert alert-error"><span>Error: ${err.message}</span></div><button id="tryAgainBtn" class="btn btn-primary mt-4">Try Again</button>`;
    document
      .getElementById("tryAgainBtn")
      .addEventListener("click", () => renderUploadView());
  } finally {
    isUploading = false;
  }
}

async function handleRead(mode = "full") {
  const area = document.getElementById("resultArea");
  area.classList.remove("hidden");
  area.innerHTML = `<div class="mockup-window border border-base-300 bg-base-200 mt-4"><div class="p-6 bg-base-100 min-h-[100px]" id="previewArea"><p class="text-sm">Generating script preview...</p></div></div>`;
  try {
    const resp = await fetch(`${API_BASE}/tts-script`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFilename,
        mode:
          mode === "full"
            ? "read_aloud_full"
            : mode === "summary"
              ? "spoken_summary"
              : "podcast",
      }),
    });
    if (!resp.ok) throw new Error(`Script failed: ${resp.status}`);
    const data = await resp.json();
    const preview = document.getElementById("previewArea");
    preview.innerHTML = `<pre class="whitespace-pre-wrap">${data.script || data.dialog || JSON.stringify(data, null, 2)}</pre>`;
  } catch (err) {
    console.error("Preview error", err);
    const preview = document.getElementById("previewArea");
    preview.innerHTML = `<div class="alert alert-error"><span>Error: ${err.message}</span></div>`;
  }
}

async function handleReadAloud(mode = "full") {
  const area = document.getElementById("resultArea");
  area.classList.remove("hidden");
  area.innerHTML = `<div class="mockup-window border border-base-300 bg-base-200 mt-4"><div class="p-6 bg-base-100 min-h-[100px]" id="audioContainer"><div class="flex flex-col gap-4"><ul class="steps steps-vertical"><li id="step1" class="step step-primary">Generating script...</li><li id="step2" class="step">Converting to audio...</li><li id="step3" class="step">Ready to play</li></ul><progress class="progress progress-secondary w-full" value="33" max="100"></progress><p class="text-sm text-base-content/70">This may take 1-2 minutes</p></div></div></div>`;
  const startTime = Date.now();
  try {
    const scriptResp = await fetch(`${API_BASE}/tts-script`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFilename,
        mode:
          mode === "full"
            ? "read_aloud_full"
            : mode === "summary"
              ? "spoken_summary"
              : "podcast",
      }),
    });
    if (!scriptResp.ok)
      throw new Error(`Script generation failed: ${scriptResp.status}`);
    const scriptData = await scriptResp.json();
    const container = document.getElementById("audioContainer");
    container.innerHTML = `<div class="flex flex-col gap-4"><ul class="steps steps-vertical"><li class="step step-primary">Generating script ✓</li><li id="step2" class="step step-primary">Converting to audio...</li><li id="step3" class="step">Ready to play</li></ul><progress class="progress progress-secondary w-full" value="66" max="100"></progress><p class="text-sm text-base-content/70">Almost done...</p></div>`;

    if (mode === "podcast") {
      const dialogResp = await fetch(`${API_BASE}/read_aloud`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: currentFilename, mode: "podcast" }),
      });
      if (!dialogResp.ok)
        throw new Error(`Dialog generation failed: ${dialogResp.status}`);
      const dialogJson = await dialogResp.json();
      const turns = dialogJson.dialog || [];
      container.innerHTML = `<div class="flex flex-col gap-4"><div class="alert alert-success"><span>Dialog ready! (Generated in ${Math.round((Date.now() - startTime) / 1000)}s)</span></div><h3 class="text-lg font-bold text-neutral">Podcast Dialog</h3><div class="mb-2">Buffer: <progress id="bufferBar" class="progress progress-info w-full" value="0" max="100"></progress></div><div id="dialogList" class="space-y-2"></div></div>`;
      const dialogList = document.getElementById("dialogList");
      const audioUrls = {};
      const statusEls = {};
      const totalTurns = turns.length;
      let bufferedCount = 0;
      const bufferThreshold = Math.min(2, totalTurns);
      let nextToPlay = 1;
      let isPlaying = false;
      function updateBufferBar() {
        const bar = document.getElementById("bufferBar");
        if (!bar) return;
        bar.value = Math.round((bufferedCount / totalTurns) * 100);
      }
      function playAudioUrl(url) {
        return new Promise((resolve) => {
          const a = new Audio(url);
          a.addEventListener("ended", () => resolve());
          a.addEventListener("error", () => resolve());
          a.play().catch(() => resolve());
        });
      }
      async function playSequence() {
        if (isPlaying) return;
        isPlaying = true;
        while (nextToPlay <= totalTurns) {
          const key = String(nextToPlay);
          if (!audioUrls[key]) {
            await new Promise((r) => setTimeout(r, 250));
            if (!audioUrls[key]) break;
          }
          try {
            if (statusEls[key]) statusEls[key].textContent = "playing";
            await playAudioUrl(audioUrls[key]);
            if (statusEls[key]) statusEls[key].textContent = "played";
          } catch (e) {
            console.error("Playback error for turn", nextToPlay, e);
            if (statusEls[key]) statusEls[key].textContent = "error";
          }
          nextToPlay += 1;
        }
        isPlaying = false;
      }
      turns.forEach((turn, idx) => {
        const div = document.createElement("div");
        div.className = "p-3 bg-base-200 rounded-box flex items-start gap-3";
        const speaker = document.createElement("strong");
        speaker.textContent = (turn.speaker || "host").toUpperCase() + ": ";
        const p = document.createElement("p");
        p.className = "flex-1 text-sm whitespace-pre-wrap";
        p.textContent = turn.text || "";
        const status = document.createElement("span");
        status.className = "text-xs text-base-content/60";
        status.textContent = "pending";
        const btn = document.createElement("button");
        btn.className = "btn btn-sm btn-outline";
        btn.textContent = "Play";
        btn.dataset.idx = idx + 1;
        statusEls[String(idx + 1)] = status;
        btn.addEventListener("click", async () => {
          try {
            const idxKey = btn.dataset.idx;
            if (audioUrls[idxKey]) {
              new Audio(audioUrls[idxKey]).play();
              return;
            }
            const sp = (turn.speaker || "host").toLowerCase();
            const speakerVoice =
              sp === "guest" || sp === "female" ? "female" : "male";
            const resp = await fetch("/api/tts/speak", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ speaker: speakerVoice, text: turn.text }),
            });
            if (!resp.ok) throw new Error(`TTS speak failed: ${resp.status}`);
            const b = await resp.blob();
            const url = URL.createObjectURL(b);
            audioUrls[idxKey] = url;
            new Audio(url).play();
          } catch (e) {
            console.error("Play turn error:", e);
            alert("Error playing turn: " + e.message);
          }
        });
        div.appendChild(speaker);
        div.appendChild(p);
        div.appendChild(status);
        div.appendChild(btn);
        dialogList.appendChild(div);
      });

      try {
        const streamResp = await fetch(`${API_BASE}/read_aloud/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename: currentFilename, mode: "podcast" }),
        });
        if (streamResp.ok && streamResp.body) {
          const reader = streamResp.body.getReader();
          const decoder = new TextDecoder();
          let buf = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buf += decoder.decode(value, { stream: true });
            const parts = buf.split("\n");
            buf = parts.pop();
            for (const line of parts) {
              if (!line.trim()) continue;
              try {
                const obj = JSON.parse(line);
                if (obj && obj.audio_b64) {
                  const binary = atob(obj.audio_b64);
                  const len = binary.length;
                  const bytes = new Uint8Array(len);
                  for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
                  const blob = new Blob([bytes.buffer], { type: "audio/wav" });
                  const url = URL.createObjectURL(blob);
                  const key = String(obj.idx);
                  if (!audioUrls[key]) {
                    audioUrls[key] = url;
                    bufferedCount += 1;
                    if (statusEls[key]) statusEls[key].textContent = "buffered";
                    updateBufferBar();
                  }
                  if (bufferedCount >= bufferThreshold && !isPlaying)
                    playSequence();
                }
              } catch (e) {
                console.error("Error parsing podcast stream line:", e, line);
              }
            }
          }
        }
      } catch (e) {
        console.error("Podcast audio stream error:", e);
      }

      return;
    }
  } catch (err) {
    console.error("Read aloud error:", err);
    const audioContainer = document.getElementById("audioContainer");
    if (audioContainer)
      audioContainer.innerHTML = `<div class="alert alert-error"><span>Error: ${err.message}</span></div>`;
  }
}

// Initialize
renderUploadView();
