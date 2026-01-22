// API_BASE is defined in config.js
const API_BASE =
  typeof CONFIG !== "undefined"
    ? CONFIG.API_BASE_URL
    : "http://localhost:8000/api/papers";

let uploadedFile = null;
let currentFilename = null;

// DOM Elements
const uploadBox = document.getElementById("uploadBox");
const fileInput = document.getElementById("fileInput");
const fileInfo = document.getElementById("fileInfo");
const actionButtons = document.getElementById("actionButtons");
const summarizeBtn = document.getElementById("summarizeBtn");
const readAloudBtn = document.getElementById("readAloudBtn");
const resultSection = document.getElementById("resultSection");
const resultTitle = document.getElementById("resultTitle");
const resultContent = document.getElementById("resultContent");
const copyBtn = document.getElementById("copyBtn");

// Upload box click handler
uploadBox.addEventListener("click", () => {
  fileInput.click();
});

// File input change handler
fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) {
    handleFile(file);
  }
});

// Drag and drop handlers
uploadBox.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadBox.classList.add("dragover");
});

uploadBox.addEventListener("dragleave", () => {
  uploadBox.classList.remove("dragover");
});

uploadBox.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadBox.classList.remove("dragover");

  const file = e.dataTransfer.files[0];
  if (file && file.type === "application/pdf") {
    handleFile(file);
  } else {
    alert("Please upload a PDF file");
  }
});

// Handle file upload
async function handleFile(file) {
  uploadedFile = file;

  const formData = new FormData();
  formData.append("file", file);

  try {
    // Show loading state
    fileInfo.innerHTML = `<p>Uploading ${file.name}...</p>`;
    fileInfo.classList.remove("hidden");

    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("Upload failed");
    }

    const data = await response.json();
    currentFilename = data.filename;

    // Show success message
    fileInfo.innerHTML = `
            <div>
                <strong>${data.filename}</strong><br>
                <small>${data.total_pages} pages • ${data.word_count.toLocaleString()} words</small>
            </div>
        `;

    // Show action buttons
    actionButtons.classList.remove("hidden");
    resultSection.classList.add("hidden");
  } catch (error) {
    fileInfo.innerHTML = `<p style="color: red;">Error uploading file: ${error.message}</p>`;
  }
}

// Summarize button handler
summarizeBtn.addEventListener("click", async () => {
  if (!currentFilename) return;

  // Disable buttons
  summarizeBtn.disabled = true;
  readAloudBtn.disabled = true;

  // Show result section with loading
  resultSection.classList.remove("hidden");
  resultTitle.textContent = "Summary";
  resultContent.innerHTML =
    '<div class="loading"><div class="spinner"></div><p>Generating summary...</p></div>';

  try {
    // Use streaming endpoint
    await streamResponse(`${API_BASE}/summarise/stream`, "Summary");
  } catch (error) {
    resultContent.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
  } finally {
    summarizeBtn.disabled = false;
    readAloudBtn.disabled = false;
  }
});

// Read Aloud button handler
readAloudBtn.addEventListener("click", async () => {
  if (!currentFilename) return;

  // Disable buttons
  summarizeBtn.disabled = true;
  readAloudBtn.disabled = true;

  // Show result section with loading
  resultSection.classList.remove("hidden");
  resultTitle.textContent = "Text-to-Speech Script";
  resultContent.innerHTML =
    '<div class="loading"><div class="spinner"></div><p>Generating TTS script...</p></div>';

  try {
    const response = await fetch(`${API_BASE}/tts-script`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ filename: currentFilename }),
    });

    if (!response.ok) {
      throw new Error("Failed to generate TTS script");
    }

    const data = await response.json();
    resultContent.innerHTML = `<p class="streaming-cursor">${data.script}</p>`;

    // Remove cursor after a moment
    setTimeout(() => {
      const p = resultContent.querySelector("p");
      if (p) p.classList.remove("streaming-cursor");
    }, 500);
  } catch (error) {
    resultContent.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
  } finally {
    summarizeBtn.disabled = false;
    readAloudBtn.disabled = false;
  }
});

// Stream response from API
async function streamResponse(url, title) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ filename: currentFilename }),
  });

  if (!response.ok) {
    throw new Error("Failed to generate response");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let accumulatedText = "";
  resultContent.innerHTML = '<p class="streaming-cursor"></p>';
  const textElement = resultContent.querySelector("p");

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      // Remove streaming cursor
      textElement.classList.remove("streaming-cursor");
      break;
    }

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));

          if (data.content) {
            accumulatedText += data.content;
            textElement.textContent = accumulatedText;
          }

          if (data.error) {
            textElement.innerHTML = `<span style="color: red;">Error: ${data.error}</span>`;
            textElement.classList.remove("streaming-cursor");
            return;
          }
        } catch (e) {
          // Skip invalid JSON
          continue;
        }
      }
    }
  }
}

// Copy button handler
copyBtn.addEventListener("click", () => {
  const text = resultContent.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const originalText = copyBtn.innerHTML;
    copyBtn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!';

    setTimeout(() => {
      copyBtn.innerHTML = originalText;
    }, 2000);
  });
});
