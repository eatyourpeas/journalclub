const API_BASE =
  API_BASE_URL == "__API_BASE_URL__"
    ? "http://localhost:8000/api/papers"
    : `${API_BASE_URL}/api/papers`;
const stageContainer = document.getElementById("stageContainer");
let currentFilename = null;
let isUploading = false;
let pollInterval = null;

// Prevent form submissions globally
document.addEventListener(
  "submit",
  (e) => {
    e.preventDefault();
    return false;
  },
  true,
);

// --- View 1: The Upload UI ---
function renderUploadView() {
  stageContainer.innerHTML = `
        <label for="fileInput" id="uploadBox" class="border-2 border-dashed border-primary/30 rounded-box p-12 text-center bg-base-200/50 hover:bg-base-200 cursor-pointer block">
            <input type="file" id="fileInput" accept=".pdf" class="hidden">
            <div class="flex flex-col items-center gap-2">
                <svg class="w-12 h-12 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                <p class="text-lg font-semibold">Click to upload Journal article as PDF</p>
            </div>
        </label>`;

  const input = document.getElementById("fileInput");

  input.addEventListener("change", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.target.files[0] && !isUploading) {
      const file = e.target.files[0];
      // Reset the input immediately to prevent any navigation
      e.target.value = "";
      uploadFile(file);
    }
  });
}

// --- View 2: The Success & Actions UI ---
function renderActionView(filename, pages) {
  stageContainer.innerHTML = `
        <div class="alert alert-success shadow-sm mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span><strong>Ready:</strong> ${filename} (${pages} pages)</span>
        </div>
        <div class="flex gap-4">
            <button id="summarizeBtn" type="button" class="btn btn-primary flex-1">Summarise</button>
            <button id="listenBtn" type="button" class="btn btn-secondary flex-1">Listen</button>
            <button id="resetBtn" type="button" class="btn btn-ghost">Reset</button>
        </div>
        <div id="resultArea" class="mt-6 hidden"></div>
    `;

  // Add event listeners
  const summarizeBtn = document.getElementById("summarizeBtn");
  const listenBtn = document.getElementById("listenBtn");
  const resetBtn = document.getElementById("resetBtn");

  summarizeBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    handleSummarize();
  });

  listenBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    handleReadAloud();
  });

  resetBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    // Clean up any polling
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    renderUploadView();
  });
}

// --- Logic ---
async function uploadFile(file) {
  isUploading = true;

  // Show immediate loading feedback
  stageContainer.innerHTML = `<div class="py-20 text-center"><span class="loading loading-spinner loading-lg text-primary"></span><p class="mt-4">Uploading and Parsing...</p></div>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload Failed: ${response.status}`);
    }

    const data = await response.json();
    currentFilename = data.filename;
    renderActionView(data.filename, data.total_pages);
  } catch (err) {
    console.error("Upload error:", err);
    stageContainer.innerHTML = `
      <div class="alert alert-error">Error: ${err.message}</div>
      <button id="tryAgainBtn" type="button" class="btn mt-4">Try Again</button>
    `;

    const tryAgainBtn = document.getElementById("tryAgainBtn");
    tryAgainBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      renderUploadView();
    });
  } finally {
    isUploading = false;
  }
}

async function handleSummarize() {
  const area = document.getElementById("resultArea");
  area.classList.remove("hidden");
  area.innerHTML = `
    <div class="mockup-window border border-base-300 bg-base-200 mt-4">
      <div class="p-6 bg-base-100 min-h-[100px]" id="summaryText">
        <span class="loading loading-spinner loading-md"></span> 
        <span id="progressText">Starting analysis...</span>
      </div>
    </div>`;

  try {
    // Step 1: Start the summarization task
    const response = await fetch(`${API_BASE}/summarise`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename: currentFilename,
      }),
    });

    if (!response.ok) {
      throw new Error(`Summary generation failed: ${response.status}`);
    }

    const { task_id } = await response.json();

    // Step 2: Poll for status
    pollInterval = setInterval(async () => {
      try {
        const statusResponse = await fetch(`${API_BASE}/summarise/${task_id}`);

        if (!statusResponse.ok) {
          throw new Error(`Status check failed: ${statusResponse.status}`);
        }

        const status = await statusResponse.json();
        const progressText = document.getElementById("progressText");

        if (status.status === "completed") {
          // Clear the polling
          clearInterval(pollInterval);
          pollInterval = null;

          // Display the summary
          const summaryText = document.getElementById("summaryText");
          const summary = status.summary;

          summaryText.innerHTML = `
            <div class="prose max-w-none">
              <h3 class="text-lg font-bold mb-2">Summary</h3>
              <p class="whitespace-pre-wrap">${summary.summary}</p>
              
              <h4 class="text-md font-bold mt-4 mb-2">Key Points</h4>
              ${summary.key_points.map((point) => `<p class="whitespace-pre-wrap">${point}</p>`).join("")}
              
              <h4 class="text-md font-bold mt-4 mb-2">Methodology</h4>
              ${summary.methodology.map((point) => `<p class="whitespace-pre-wrap">${point}</p>`).join("")}
              
              <h4 class="text-md font-bold mt-4 mb-2">Conclusions</h4>
              ${summary.conclusions.map((point) => `<p class="whitespace-pre-wrap">${point}</p>`).join("")}
            </div>
          `;
        } else if (status.status === "failed") {
          clearInterval(pollInterval);
          pollInterval = null;

          const summaryText = document.getElementById("summaryText");
          summaryText.innerHTML = `<div class="alert alert-error">Error: ${status.error}</div>`;
        } else {
          // Update progress
          if (progressText) {
            progressText.textContent = status.progress || "Processing...";
          }
        }
      } catch (pollErr) {
        console.error("Polling error:", pollErr);
        clearInterval(pollInterval);
        pollInterval = null;

        const summaryText = document.getElementById("summaryText");
        summaryText.innerHTML = `<div class="alert alert-error">Error checking status: ${pollErr.message}</div>`;
      }
    }, 2000); // Poll every 2 seconds
  } catch (err) {
    console.error("Summarise error:", err);
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    const summaryText = document.getElementById("summaryText");
    summaryText.innerHTML = `<div class="alert alert-error">Error: ${err.message}</div>`;
  }
}

async function handleReadAloud() {
  const area = document.getElementById("resultArea");
  area.classList.remove("hidden");
  area.innerHTML = `<div class="mockup-window border border-base-300 bg-base-200 mt-4"><div class="p-6 bg-base-100 min-h-[100px]" id="audioContainer"><span class="loading loading-spinner loading-md"></span> Generating optimized script...</div></div>`;

  try {
    // Step 1: Generate TTS-optimized script
    const scriptResponse = await fetch(`${API_BASE}/tts-script`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename: currentFilename,
      }),
    });

    if (!scriptResponse.ok) {
      throw new Error(`Script generation failed: ${scriptResponse.status}`);
    }

    const scriptData = await scriptResponse.json();

    // Update status
    const audioContainer = document.getElementById("audioContainer");
    audioContainer.innerHTML = `<div class="p-6 bg-base-100 min-h-[100px]"><span class="loading loading-spinner loading-md"></span> Converting to audio...</div>`;

    // Step 2: Convert script to audio
    const audioResponse = await fetch(`${API_BASE}/read_aloud`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename: currentFilename,
      }),
    });

    if (!audioResponse.ok) {
      throw new Error(`Audio generation failed: ${audioResponse.status}`);
    }

    // Get the audio blob from the response
    const audioBlob = await audioResponse.blob();
    const audioUrl = URL.createObjectURL(audioBlob);

    // Display the audio player with the script preview
    audioContainer.innerHTML = `
      <div class="flex flex-col gap-4">
        <h3 class="text-lg font-bold">Listen to Paper</h3>
        <audio controls class="w-full" autoplay>
          <source src="${audioUrl}" type="audio/mpeg">
          Your browser does not support the audio element.
        </audio>
        <div class="collapse collapse-arrow bg-base-200">
          <input type="checkbox" /> 
          <div class="collapse-title font-medium">
            View TTS Script
          </div>
          <div class="collapse-content"> 
            <p class="text-sm whitespace-pre-wrap">${scriptData.script}</p>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error("Read aloud error:", err);
    const audioContainer = document.getElementById("audioContainer");
    audioContainer.innerHTML = `<div class="alert alert-error">Error: ${err.message}</div>`;
  }
}

// Initialize
renderUploadView();
