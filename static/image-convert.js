let selectedFiles = [];
let downloadUrl = null;
let previewUrl = null;
let busy = false;
let lastResult = null;

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
const formatSelect = document.getElementById("formatSelect");
const widthInput = document.getElementById("widthInput");
const heightInput = document.getElementById("heightInput");
const resizeMode = document.getElementById("resizeMode");
const submitBtn = document.getElementById("submitBtn");
const btnText = submitBtn.querySelector(".btn-text");
const btnSpinner = submitBtn.querySelector(".btn-spinner");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const resultBox = document.getElementById("resultBox");
const resultName = document.getElementById("resultName");
const resultMeta = document.getElementById("resultMeta");
const downloadLink = document.getElementById("downloadLink");

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
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

function fileKey(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function filesCaption(files) {
  if (files.length === 1) return files[0].name;
  return t("common.andMoreImages", { name: files[0].name, n: files.length });
}

function startLabel() {
  return selectedFiles.length > 1
    ? t("convert.batchStart", { n: selectedFiles.length })
    : t("convert.start");
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
  if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
  if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = null; }
  resultBox.classList.add("hidden");
  statusBox.classList.add("hidden");
  renderBatchErrors([]);

  if (files.length) {
    const total = files.reduce((sum, file) => sum + file.size, 0);
    fileName.textContent = filesCaption(files);
    fileSize.textContent = formatBytes(total);
    filePreview.classList.remove("hidden");
    submitBtn.disabled = false;
    btnText.textContent = startLabel();
    renderQueue();
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
    submitBtn.disabled = true;
    btnText.textContent = t("convert.start");
  }
}

function renderQueue() {
  const removable = selectedFiles.length > 1;
  fileQueue.innerHTML = selectedFiles
    .map((file, index) => {
      const remove = removable
        ? `<button type="button" class="queue-remove" data-remove-index="${index}">${t("common.removeFile")}</button>`
        : "";
      return `<li><span class="queue-name">${escapeHtml(file.name)}</span><span class="queue-side"><span class="queue-size">${formatBytes(file.size)}</span>${remove}</span></li>`;
    })
    .join("");
  fileQueue.classList.toggle("hidden", !selectedFiles.length);
}

function paintResult() {
  if (!lastResult || !downloadUrl) return;
  downloadLink.href = downloadUrl;
  downloadLink.download = lastResult.name;
  downloadLink.textContent = lastResult.batch ? t("common.downloadZip") : t("common.downloadImage");
  resultName.textContent = lastResult.name;
  if (lastResult.batch) {
    resultMeta.textContent = lastResult.fail
      ? t("convert.batchMetaFail", { ok: lastResult.ok, fail: lastResult.fail })
      : t("common.batchResult", { ok: lastResult.ok, fail: lastResult.fail });
    renderBatchErrors(lastResult.errors);
  } else {
    resultMeta.textContent = lastResult.w && lastResult.h
      ? t("convert.size", { w: lastResult.w, h: lastResult.h })
      : "";
    renderBatchErrors([]);
  }
  resultBox.classList.remove("hidden");
}

function refreshI18n() {
  if (selectedFiles.length) {
    fileName.textContent = filesCaption(selectedFiles);
    renderQueue();
  }
  if (busy) {
    btnText.textContent = selectedFiles.length > 1 ? t("convert.batchWorking") : t("convert.working");
  } else {
    btnText.textContent = startLabel();
  }
  if (!resultBox.classList.contains("hidden")) paintResult();
}

async function loadFormats() {
  const current = formatSelect.value;
  const res = await fetch("/api/image/export-formats");
  const formats = await res.json();
  formatSelect.innerHTML = formats.map((f) => `<option value="${f.id}">${f.label}</option>`).join("");
  if ([...formatSelect.options].some((opt) => opt.value === current)) {
    formatSelect.value = current;
  }
}

async function submit() {
  if (!selectedFiles.length) return;
  const batch = selectedFiles.length > 1;
  lastResult = null;
  busy = true;
  submitBtn.disabled = true;
  btnText.textContent = batch ? t("convert.batchWorking") : t("convert.working");
  btnSpinner.classList.remove("hidden");
  statusBox.classList.remove("hidden", "error");
  statusText.textContent = batch ? t("convert.statusMany", { n: selectedFiles.length }) : t("convert.statusOne");

  const formData = new FormData();
  formData.append("output_format", formatSelect.value);
  formData.append("width", widthInput.value);
  formData.append("height", heightInput.value);
  formData.append("resize_mode", resizeMode.value);
  if (batch) {
    selectedFiles.forEach((file) => formData.append("files", file));
  } else {
    formData.append("file", selectedFiles[0]);
  }

  try {
    const res = await fetch(batch ? "/api/image/transform-batch" : "/api/image/transform", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(typeof err.detail === "string" ? err.detail : t("convert.fail"));
    }
    const blob = await res.blob();
    const outName = parseFilename(
      res.headers.get("Content-Disposition") || "",
      batch ? "converted-images.zip" : "converted.jpg",
    );
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(blob);
    if (batch) {
      lastResult = {
        batch: true,
        name: outName,
        ok: Number(res.headers.get("X-Batch-Ok") || 0),
        fail: Number(res.headers.get("X-Batch-Failed") || 0),
        errors: parseBatchErrors(res.headers.get("X-Batch-Errors")),
      };
    } else {
      lastResult = {
        batch: false,
        name: outName,
        w: res.headers.get("X-Output-Width"),
        h: res.headers.get("X-Output-Height"),
      };
    }
    statusBox.classList.add("hidden");
    paintResult();
  } catch (e) {
    statusBox.classList.add("error");
    statusText.textContent = e.message;
  } finally {
    busy = false;
    submitBtn.disabled = !selectedFiles.length;
    btnText.textContent = startLabel();
    btnSpinner.classList.add("hidden");
  }
}

dropzone.addEventListener("click", (e) => {
  e.preventDefault();
  fileInput.click();
});
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
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
fileQueue.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-remove-index]");
  if (!btn) return;
  setFiles(selectedFiles.filter((_, index) => index !== Number(btn.dataset.removeIndex)));
});
submitBtn.addEventListener("click", submit);
document.addEventListener("lt-i18n", () => {
  refreshI18n();
  loadFormats();
});
loadFormats();
