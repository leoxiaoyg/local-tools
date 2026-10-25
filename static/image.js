const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const fileQueue = document.getElementById("fileQueue");
const previewRow = document.getElementById("previewRow");
const imagePreview = document.getElementById("imagePreview");
const resultErrors = document.getElementById("resultErrors");
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

let selectedFiles = [];
let downloadUrl = null;
let previewUrl = null;
let busy = false;
let lastResult = null;

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function calcReduction(original, compressed) {
  if (original <= 0) return "0";
  return (((original - compressed) / original) * 100).toFixed(1);
}

function fileKey(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function filesCaption(files) {
  if (files.length === 1) return files[0].name;
  return t("common.andMoreImages", { name: files[0].name, n: files.length });
}

function startLabel() {
  return selectedFiles.length > 1
    ? t("image.batchStart", { n: selectedFiles.length })
    : t("image.start");
}

function addFiles(incoming) {
  const merged = new Map(selectedFiles.map((file) => [fileKey(file), file]));
  for (const file of incoming) {
    merged.set(fileKey(file), file);
  }
  setFiles([...merged.values()].slice(0, 50));
}

function setFiles(files) {
  selectedFiles = files;
  lastResult = null;
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }

  if (files.length) {
    const total = files.reduce((sum, file) => sum + file.size, 0);
    fileName.textContent = filesCaption(files);
    fileSize.textContent = formatBytes(total);
    filePreview.classList.remove("hidden");
    compressBtn.disabled = false;
    btnText.textContent = startLabel();

    fileQueue.innerHTML = files
      .map((file) => `<li><span class="queue-name">${escapeHtml(file.name)}</span><span class="queue-size">${formatBytes(file.size)}</span></li>`)
      .join("");
    fileQueue.classList.toggle("hidden", !files.length);

    if (files.length === 1) {
      previewUrl = URL.createObjectURL(files[0]);
      imagePreview.src = previewUrl;
      previewRow.classList.remove("hidden");
    } else {
      previewRow.classList.add("hidden");
      imagePreview.removeAttribute("src");
    }
  } else {
    filePreview.classList.add("hidden");
    fileQueue.classList.add("hidden");
    fileQueue.innerHTML = "";
    previewRow.classList.add("hidden");
    imagePreview.removeAttribute("src");
    compressBtn.disabled = true;
    btnText.textContent = t("image.start");
  }
  hideResult();
  hideStatus();
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function parseFilename(disposition, fallback) {
  const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
  return match ? decodeURIComponent(match[1].replace(/"/g, "")) : fallback;
}

function parseBatchErrors(header) {
  if (!header) return [];
  try {
    const parsed = JSON.parse(decodeURIComponent(header));
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function renderBatchErrors(items) {
  if (!items.length) {
    resultErrors.classList.add("hidden");
    resultErrors.innerHTML = "";
    return;
  }
  resultErrors.innerHTML = items
    .map((item) => `<li>${escapeHtml(item.name)}：${escapeHtml(item.detail || t("common.failed"))}</li>`)
    .join("");
  resultErrors.classList.remove("hidden");
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
  renderBatchErrors([]);
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
  }
}

function paintResult() {
  if (!lastResult || !downloadUrl) return;
  downloadLink.href = downloadUrl;
  downloadLink.download = lastResult.name;
  resultName.textContent = lastResult.name;
  if (lastResult.batch) {
    downloadLink.textContent = t("common.downloadZip");
    sizeStats.innerHTML = `<span>${t("common.batchResult", { ok: lastResult.ok, fail: lastResult.fail })}</span>`;
    resultNote.textContent = lastResult.fail ? t("image.errorsInZip") : t("image.allOk");
    renderBatchErrors(lastResult.errors);
  } else {
    downloadLink.textContent = t("common.downloadImage");
    sizeStats.innerHTML = `
      <span><strong>${formatBytes(lastResult.original)}</strong> → <strong>${formatBytes(lastResult.compressed)}</strong></span>
      <span class="size-reduction">${t("image.reduced", { n: calcReduction(lastResult.original, lastResult.compressed) })}</span>
    `;
    resultNote.textContent = lastResult.message || "";
    renderBatchErrors([]);
  }
  resultBox.classList.remove("hidden");
}

function refreshI18n() {
  if (selectedFiles.length) fileName.textContent = filesCaption(selectedFiles);
  if (busy) {
    btnText.textContent = selectedFiles.length > 1 ? t("image.batchWorking") : t("image.working");
  } else {
    btnText.textContent = startLabel();
  }
  if (!resultBox.classList.contains("hidden")) paintResult();
}

async function loadFormats() {
  const current = formatSelect.value;
  try {
    const res = await fetch("/api/image/formats");
    const formats = await res.json();
    formatSelect.innerHTML = formats
      .map((f) => `<option value="${f.id}">${f.label}</option>`)
      .join("");
  } catch {
    formatSelect.innerHTML = `
      <option value="auto">${t("common.keepFormat")}</option>
      <option value="jpeg">JPEG</option>
      <option value="png">PNG</option>
      <option value="webp">WebP</option>
    `;
  }
  if ([...formatSelect.options].some((opt) => opt.value === current)) {
    formatSelect.value = current;
  }
}

modeSelect.addEventListener("change", () => {
  targetField.classList.toggle("hidden", modeSelect.value !== "target");
});

async function compress() {
  if (!selectedFiles.length) return;

  lastResult = null;
  hideResult();
  busy = true;
  compressBtn.disabled = true;
  const batch = selectedFiles.length > 1;
  btnText.textContent = batch ? t("image.batchWorking") : t("image.working");
  btnSpinner.classList.remove("hidden");
  showStatus(batch ? t("image.statusMany", { n: selectedFiles.length }) : t("image.statusOne"));

  const formData = new FormData();
  formData.append("mode", modeSelect.value);
  formData.append("output_format", formatSelect.value);
  if (modeSelect.value === "target") {
    formData.append("target_kb", targetKb.value.trim());
  }
  if (batch) {
    selectedFiles.forEach((file) => formData.append("files", file));
  } else {
    formData.append("file", selectedFiles[0]);
  }

  try {
    const res = await fetch(batch ? "/api/image/compress-batch" : "/api/image/compress", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      let detail = t("image.failRetry");
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : t("image.failRetry"));
    }

    const blob = await res.blob();
    hideStatus();
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(blob);
    if (batch) {
      lastResult = {
        batch: true,
        name: parseFilename(res.headers.get("Content-Disposition") || "", "compressed-images.zip"),
        ok: Number(res.headers.get("X-Batch-Ok") || 0),
        fail: Number(res.headers.get("X-Batch-Failed") || 0),
        errors: parseBatchErrors(res.headers.get("X-Batch-Errors")),
      };
    } else {
      lastResult = {
        batch: false,
        name: parseFilename(res.headers.get("Content-Disposition") || "", "compressed.jpg"),
        original: Number(res.headers.get("X-Original-Size")),
        compressed: Number(res.headers.get("X-Compressed-Size")),
        message: decodeURIComponent(res.headers.get("X-Compress-Message") || ""),
      };
    }
    paintResult();
  } catch (err) {
    showStatus(err.message || t("common.fail"), true);
  } finally {
    busy = false;
    compressBtn.disabled = !selectedFiles.length;
    btnText.textContent = startLabel();
    btnSpinner.classList.add("hidden");
  }
}

dropzone.addEventListener("click", (e) => {
  e.preventDefault();
  fileInput.click();
});
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
  const files = Array.from(e.dataTransfer.files);
  if (files.length) addFiles(files);
});

fileInput.addEventListener("click", (e) => e.stopPropagation());
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) addFiles(Array.from(fileInput.files));
  fileInput.value = "";
});

clearBtn.addEventListener("click", () => {
  fileInput.value = "";
  setFiles([]);
});

compressBtn.addEventListener("click", compress);
document.addEventListener("lt-i18n", () => {
  refreshI18n();
  loadFormats();
});

loadFormats();
