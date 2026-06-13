const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const previewRow = document.getElementById("previewRow");
const imagePreview = document.getElementById("imagePreview");
const modeSelect = document.getElementById("modeSelect");
const targetField = document.getElementById("targetField");
const targetKb = document.getElementById("targetKb");
const formatSelect = document.getElementById("formatSelect");
const compressBtn = document.getElementById("compressBtn");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const resultBox = document.getElementById("resultBox");
const resultName = document.getElementById("resultName");
const sizeStats = document.getElementById("sizeStats");
const resultNote = document.getElementById("resultNote");
const downloadLink = document.getElementById("downloadLink");
const btnText = compressBtn.querySelector(".btn-text");
const btnSpinner = compressBtn.querySelector(".btn-spinner");

let selectedFile = null;
let downloadUrl = null;
let previewUrl = null;

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function calcReduction(original, compressed) {
  if (original <= 0) return "0";
  return (((original - compressed) / original) * 100).toFixed(1);
}

function setFile(file) {
  selectedFile = file;
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }

  if (file) {
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    filePreview.classList.remove("hidden");
    previewUrl = URL.createObjectURL(file);
    imagePreview.src = previewUrl;
    previewRow.classList.remove("hidden");
    compressBtn.disabled = false;
  } else {
    filePreview.classList.add("hidden");
    previewRow.classList.add("hidden");
    imagePreview.removeAttribute("src");
    compressBtn.disabled = true;
  }
  hideResult();
  hideStatus();
}

function hideStatus() {
  statusBox.classList.add("hidden");
  statusBox.classList.remove("error");
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

function showResult(name, blob, meta) {
  hideResult();
  downloadUrl = URL.createObjectURL(blob);
  resultName.textContent = name;
  downloadLink.href = downloadUrl;
  downloadLink.download = name;

  const original = Number(meta.originalSize);
  const compressed = Number(meta.compressedSize);
  sizeStats.innerHTML = `
    <span><strong>${formatBytes(original)}</strong> → <strong>${formatBytes(compressed)}</strong></span>
    <span class="size-reduction">减小 ${calcReduction(original, compressed)}%</span>
  `;
  resultNote.textContent = meta.message || "";
  resultBox.classList.remove("hidden");
}

async function loadFormats() {
  try {
    const res = await fetch("/api/image/formats");
    const formats = await res.json();
    formatSelect.innerHTML = formats
      .map((f) => `<option value="${f.id}">${f.label}</option>`)
      .join("");
  } catch {
    formatSelect.innerHTML = `
      <option value="auto">保持原格式</option>
      <option value="jpeg">JPEG</option>
      <option value="png">PNG</option>
      <option value="webp">WebP</option>
    `;
  }
}

modeSelect.addEventListener("change", () => {
  targetField.classList.toggle("hidden", modeSelect.value !== "target");
});

async function compress() {
  if (!selectedFile) return;

  hideResult();
  compressBtn.disabled = true;
  btnText.textContent = "正在压缩…";
  btnSpinner.classList.remove("hidden");
  showStatus("正在优化图片，请稍候…");

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("mode", modeSelect.value);
  formData.append("output_format", formatSelect.value);
  if (modeSelect.value === "target") {
    formData.append("target_kb", targetKb.value.trim());
  }

  try {
    const res = await fetch("/api/image/compress", { method: "POST", body: formData });

    if (!res.ok) {
      let detail = "压缩失败，请重试";
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : "压缩失败，请重试");
    }

    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
    const outName = match
      ? decodeURIComponent(match[1].replace(/"/g, ""))
      : "compressed.jpg";

    const blob = await res.blob();
    hideStatus();
    showResult(outName, blob, {
      originalSize: res.headers.get("X-Original-Size"),
      compressedSize: res.headers.get("X-Compressed-Size"),
      message: decodeURIComponent(res.headers.get("X-Compress-Message") || ""),
    });
  } catch (err) {
    showStatus(err.message || "压缩失败", true);
  } finally {
    compressBtn.disabled = !selectedFile;
    btnText.textContent = "开始压缩";
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

compressBtn.addEventListener("click", compress);

loadFormats();
