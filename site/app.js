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

      <div class="flex justify-end mt-2">
        <a href="docs.html" class="btn btn-ghost btn-sm">Docs</a>
        <a href="docs.html" class="btn btn-outline btn-sm ml-2">Deploy / Self-host</a>
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
      renderActionView(
        currentFilename,
        data.total_pages || 0,
        data.word_count || 0,
      );
    } catch (err) {
      console.error("Import error", err);
      stageContainer.innerHTML = `<div class="alert alert-error"><span>Error: ${err.message}</span></div><button id="backBtn" class="btn btn-ghost mt-4">Back</button>`;
      document
        .getElementById("backBtn")
        .addEventListener("click", () => renderUploadView());
    }
  });
}

function renderActionView(filename, pages, wordCount) {
  const pageInfo =
    pages > 0
      ? `${pages} pages`
      : wordCount > 0
        ? `~${wordCount.toLocaleString()} words`
        : "parsed";
  stageContainer.innerHTML = `
    <div class="alert alert-success shadow-sm mb-4"><span><strong>Ready:</strong> ${filename} (${pageInfo})</span></div>
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
    renderActionView(
      currentFilename,
      data.total_pages || 0,
      data.word_count || 0,
    );
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
  area.innerHTML = `<div class="mockup-window border border-base-300 bg-base-200 mt-4"><div class="p-6 bg-base-100 min-h-[100px]" id="audioContainer"><div class="flex flex-col gap-4"><p class="text-sm font-semibold" id="statusMsg">Starting...</p><progress class="progress progress-secondary w-full" value="5" max="100" id="mainBar"></progress></div></div></div>`;

  const startTime = Date.now();
  function elapsedSec() {
    return Math.round((Date.now() - startTime) / 1000);
  }
  let _ticker = null;
  function startTicker(msgFn) {
    if (_ticker) clearInterval(_ticker);
    _ticker = setInterval(() => {
      const el = document.getElementById("statusMsg");
      if (el) el.textContent = msgFn();
    }, 1000);
  }
  function stopTicker() {
    if (_ticker) {
      clearInterval(_ticker);
      _ticker = null;
    }
  }

  // Decode a base64 audio chunk into a Uint8Array
  function decodeChunk(b64) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes;
  }

  // Read an NDJSON stream, calling onLine(obj) for each parsed JSON line,
  // onKeepalive() for blank keepalive lines, and returning when the stream ends.
  async function readNdjsonStream(resp, onLine, onKeepalive) {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) {
        if (!line.trim()) {
          onKeepalive && onKeepalive();
          continue;
        }
        try {
          const obj = JSON.parse(line);
          onLine(obj);
        } catch (e) {
          console.warn("NDJSON parse error:", e, line);
        }
      }
    }
  }

  const controller = new AbortController();

  try {
    // -------------------------------------------------------------------------
    // Full / Summary — single stream call, no LLM pre-call needed for "full"
    // -------------------------------------------------------------------------
    if (mode !== "podcast") {
      const streamMode = mode === "summary" ? "summarise" : "full";
      const initMsg =
        mode === "summary" ? "Summarising paper" : "Processing paper";
      startTicker(() => `${initMsg}... (${elapsedSec()}s)`);

      const resp = await fetch(`${API_BASE}/read_aloud/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({ filename: currentFilename, mode: streamMode }),
      });
      if (!resp.ok) throw new Error(`Stream request failed: ${resp.status}`);

      const container = document.getElementById("audioContainer");
      container.innerHTML = `<div class="flex flex-col gap-4"><p class="text-sm font-semibold" id="statusMsg">${initMsg}...</p><progress class="progress progress-secondary w-full" value="5" max="100" id="mainBar"></progress><p class="text-xs text-base-content/50">The server sends keepalive updates — this won't time out.</p></div>`;

      const audioChunks = [];
      await readNdjsonStream(
        resp,
        (obj) => {
          if (obj.error) throw new Error(obj.error);
          if (obj.audio_b64) {
            audioChunks.push(decodeChunk(obj.audio_b64));
            const bar = document.getElementById("mainBar");
            const msg = document.getElementById("statusMsg");
            if (bar) bar.value = Math.min(95, 5 + audioChunks.length * 25);
            if (msg)
              msg.textContent = `Receiving audio... chunk ${audioChunks.length} (${elapsedSec()}s)`;
          }
        },
        () => {
          const msg = document.getElementById("statusMsg");
          if (msg) msg.textContent = `${initMsg}... (${elapsedSec()}s)`;
        },
      );

      stopTicker();
      if (!audioChunks.length) throw new Error("No audio received from server");

      const audioBlob = new Blob(audioChunks, { type: "audio/mpeg" });
      const audioUrl = URL.createObjectURL(audioBlob);
      container.innerHTML = `<div class="flex flex-col gap-4"><div class="alert alert-success"><span>Ready in ${elapsedSec()}s</span></div><audio controls autoplay class="w-full" src="${audioUrl}"></audio><a href="${audioUrl}" download="journal-club.mp3" class="btn btn-outline btn-sm w-fit">⬇ Download</a></div>`;
      return;
    }

    // -------------------------------------------------------------------------
    // Podcast — single stream call; dialog text now included in each chunk
    // -------------------------------------------------------------------------
    startTicker(() => `Generating podcast... (${elapsedSec()}s)`);

    const resp = await fetch(`${API_BASE}/read_aloud/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({ filename: currentFilename, mode: "podcast" }),
    });
    if (!resp.ok) throw new Error(`Podcast stream failed: ${resp.status}`);

    const container = document.getElementById("audioContainer");
    container.innerHTML = `<div class="flex flex-col gap-4"><p class="text-sm font-semibold" id="statusMsg">Generating podcast dialog...</p><progress class="progress progress-info w-full" value="0" max="100" id="mainBar"></progress><div id="dialogList" class="space-y-2 mt-2"></div></div>`;

    const audioUrls = {};
    const statusEls = {};
    let totalTurns = 0;
    let nextToPlay = 1;
    let isPlaying = false;

    function playAudioUrl(url) {
      return new Promise((resolve) => {
        const a = new Audio(url);
        a.addEventListener("ended", resolve);
        a.addEventListener("error", resolve);
        a.play().catch(resolve);
      });
    }

    async function playNext() {
      if (isPlaying) return;
      isPlaying = true;
      while (audioUrls[String(nextToPlay)]) {
        const key = String(nextToPlay);
        if (statusEls[key]) statusEls[key].textContent = "▶ playing";
        await playAudioUrl(audioUrls[key]);
        if (statusEls[key]) statusEls[key].textContent = "✓";
        nextToPlay++;
      }
      isPlaying = false;
    }

    await readNdjsonStream(
      resp,
      (obj) => {
        if (obj.error) throw new Error(obj.error);
        if (obj.audio_b64) {
          totalTurns++;
          const key = String(obj.idx);

          // Add dialog turn to UI
          const dialogList = document.getElementById("dialogList");
          if (dialogList) {
            const div = document.createElement("div");
            div.className =
              "p-3 bg-base-200 rounded-box flex items-start gap-3";
            div.innerHTML = `<strong class="shrink-0">${(obj.speaker || "host").toUpperCase()}:</strong><p class="flex-1 text-sm">${obj.text || ""}</p><span class="text-xs text-base-content/50 shrink-0" id="turn-status-${key}">buffered</span>`;
            dialogList.appendChild(div);
            statusEls[key] = document.getElementById(`turn-status-${key}`);
          }

          audioUrls[key] = URL.createObjectURL(
            new Blob([decodeChunk(obj.audio_b64)], { type: "audio/mpeg" }),
          );
          const bar = document.getElementById("mainBar");
          const msg = document.getElementById("statusMsg");
          if (bar) bar.value = Math.min(95, totalTurns * 10);
          if (msg)
            msg.textContent = `Buffered ${totalTurns} turn${totalTurns > 1 ? "s" : ""}... (${elapsedSec()}s)`;

          if (totalTurns >= 2 && !isPlaying) playNext();
        }
      },
      () => {
        const msg = document.getElementById("statusMsg");
        if (msg) msg.textContent = `Generating podcast... (${elapsedSec()}s)`;
      },
    );

    stopTicker();
    // Play anything remaining
    playNext();
    const msg = document.getElementById("statusMsg");
    if (msg)
      msg.textContent = `Podcast ready (${elapsedSec()}s) — ${totalTurns} turns`;
    const bar = document.getElementById("mainBar");
    if (bar) bar.value = 100;
  } catch (err) {
    stopTicker();
    console.error("Read aloud error:", err);
    const audioContainer = document.getElementById("audioContainer");
    if (audioContainer) {
      const isAbort = err.name === "AbortError";
      const msg = isAbort ? "Cancelled." : `Error: ${err.message}`;
      audioContainer.innerHTML = `<div class="flex flex-col gap-4"><div class="alert alert-error"><span>${msg}</span></div><button id="retryBtn" class="btn btn-primary btn-sm w-fit">Try Again</button></div>`;
      document
        .getElementById("retryBtn")
        ?.addEventListener("click", () => handleReadAloud(mode));
    }
  }
}

// Initialize
renderUploadView();
