const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const formatSelect = document.getElementById("formatSelect");
const convertBtn = document.getElementById("convertBtn");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const progressBar = document.getElementById("progressBar");
const progressFill = document.getElementById("progressFill");
const resultBox = document.getElementById("resultBox");
const resultName = document.getElementById("resultName");
const downloadLink = document.getElementById("downloadLink");
const btnText = convertBtn.querySelector(".btn-text");
const btnSpinner = convertBtn.querySelector(".btn-spinner");

let selectedFile = null;
let downloadUrl = null;

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setFile(file) {
  selectedFile = file;
  if (file) {
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    filePreview.classList.remove("hidden");
    convertBtn.disabled = false;
  } else {
    filePreview.classList.add("hidden");
    convertBtn.disabled = true;
  }
  hideResult();
  hideStatus();
}

function hideStatus() {
  statusBox.classList.add("hidden");
  statusBox.classList.remove("error");
  progressBar.classList.add("hidden");
  progressFill.style.width = "0%";
}

function showStatus(message, isError = false) {
  statusBox.classList.remove("hidden");
  statusBox.classList.toggle("error", isError);
  statusText.textContent = message;
}

function hideResult() {
  resultBox.classList.add("hidden");
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
  }
}

function showResult(name, blob) {
  hideResult();
  downloadUrl = URL.createObjectURL(blob);
  resultName.textContent = name;
  downloadLink.href = downloadUrl;
  downloadLink.download = name;
  resultBox.classList.remove("hidden");
}

async function loadFormats() {
  try {
    const res = await fetch("/api/formats");
    const formats = await res.json();
    formatSelect.innerHTML = formats
      .map((f) => `<option value="${f.id}">${f.label} (.${f.ext})</option>`)
      .join("");
  } catch {
    formatSelect.innerHTML = `
      <option value="mp3">MP3 (.mp3)</option>
      <option value="wav">WAV (.wav)</option>
      <option value="aac">AAC (.aac)</option>
      <option value="m4a">M4A (.m4a)</option>
      <option value="ogg">OGG (.ogg)</option>
      <option value="flac">FLAC (.flac)</option>
    `;
  }
}

function simulateProgress() {
  progressBar.classList.remove("hidden");
  let progress = 0;
  const timer = setInterval(() => {
    progress += Math.random() * 12;
    if (progress > 90) progress = 90;
    progressFill.style.width = `${progress}%`;
  }, 300);
  return () => {
    clearInterval(timer);
    progressFill.style.width = "100%";
  };
}

async function convert() {
  if (!selectedFile) return;

  hideResult();
  convertBtn.disabled = true;
  btnText.textContent = "正在提取…";
  btnSpinner.classList.remove("hidden");
  showStatus("正在从视频中提取音频，请稍候…");
  const stopProgress = simulateProgress();

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("format", formatSelect.value);

  try {
    const res = await fetch("/api/convert", { method: "POST", body: formData });

    if (!res.ok) {
      let detail = "转换失败，请重试";
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }

    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
    const outName = match
      ? decodeURIComponent(match[1].replace(/"/g, ""))
      : `audio.${formatSelect.value}`;

    const blob = await res.blob();
    stopProgress();
    hideStatus();
    showResult(outName, blob);
  } catch (err) {
    stopProgress();
    showStatus(err.message || "转换失败", true);
  } finally {
    convertBtn.disabled = !selectedFile;
    btnText.textContent = "开始提取";
    btnSpinner.classList.add("hidden");
  }
}

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file) setFile(file);
});

clearBtn.addEventListener("click", () => {
  fileInput.value = "";
  setFile(null);
});

convertBtn.addEventListener("click", convert);

loadFormats();
