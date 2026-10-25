const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const fileQueue = document.getElementById("fileQueue");
const previewRow = document.getElementById("previewRow");
const imagePreview = document.getElementById("imagePreview");
const exifPanel = document.getElementById("exifPanel");
const exifSummary = document.getElementById("exifSummary");
const exifTable = document.getElementById("exifTable").querySelector("tbody");
const exifEmpty = document.getElementById("exifEmpty");
const submitBtn = document.getElementById("submitBtn");
const btnText = submitBtn.querySelector(".btn-text");
const btnSpinner = submitBtn.querySelector(".btn-spinner");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const resultBox = document.getElementById("resultBox");
const resultName = document.getElementById("resultName");
const resultMeta = document.getElementById("resultMeta");
const downloadLink = document.getElementById("downloadLink");

let selectedFiles = [];
let activeIndex = 0;
let downloadUrl = null;
let previewUrl = null;
let busy = false;
let lastExif = null;
let lastResult = null;

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

function parseFilename(disposition, fallback) {
  const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
  return match ? decodeURIComponent(match[1].replace(/"/g, "")) : fallback;
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
    ? t("exif.batchStart", { n: selectedFiles.length })
    : t("exif.start");
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
  activeIndex = 0;
  lastExif = null;
  lastResult = null;
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
  }
  resultBox.classList.add("hidden");
  statusBox.classList.add("hidden");
  submitBtn.disabled = !files.length;
  btnText.textContent = startLabel();

  if (!files.length) {
    filePreview.classList.add("hidden");
    fileQueue.classList.add("hidden");
    fileQueue.innerHTML = "";
    previewRow.classList.add("hidden");
    exifPanel.classList.add("hidden");
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    }
    return;
  }

  const total = files.reduce((sum, file) => sum + file.size, 0);
  fileName.textContent = filesCaption(files);
  fileSize.textContent = formatBytes(total);
  filePreview.classList.remove("hidden");
  renderQueue();
  inspectActive();
}

function renderQueue() {
  fileQueue.innerHTML = selectedFiles
    .map((file, index) => {
      const current = index === activeIndex ? " is-active" : "";
      return `<li class="queue-item${current}" data-index="${index}"><span class="queue-name">${index + 1}. ${escapeHtml(file.name)}</span><span class="queue-size">${formatBytes(file.size)}</span></li>`;
    })
    .join("");
  fileQueue.classList.toggle("hidden", !selectedFiles.length);
}

async function inspectActive() {
  const file = selectedFiles[activeIndex];
  if (!file) return;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  imagePreview.src = previewUrl;
  previewRow.classList.remove("hidden");

  const formData = new FormData();
  formData.append("file", file);
  try {
    const res = await fetch("/api/image/exif", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(typeof err.detail === "string" ? err.detail : t("exif.readFail"));
    }
    lastExif = await res.json();
    renderExif(lastExif);
  } catch (err) {
    lastExif = null;
    exifPanel.classList.remove("hidden");
    exifSummary.textContent = err.message;
    exifTable.innerHTML = "";
    exifEmpty.classList.add("hidden");
    document.getElementById("exifTable").classList.add("hidden");
    document.querySelector(".exif-table-wrap").classList.add("hidden");
  }
}

function renderExif(data) {
  exifPanel.classList.remove("hidden");
  const bits = [`${data.width} × ${data.height}`, data.format];
  if (data.has_gps) bits.push(t("exif.gps"));
  if (data.sensitive_count) bits.push(t("exif.sensitive", { n: data.sensitive_count }));
  else if (!data.has_exif) bits.push(t("exif.none"));
  exifSummary.textContent = bits.join(" · ");

  exifTable.innerHTML = (data.fields || [])
    .map((item) => `<tr class="${item.sensitive ? "is-sensitive" : ""}"><td>${escapeHtml(item.key)}</td><td>${escapeHtml(item.value)}</td></tr>`)
    .join("");
  const hasFields = Boolean(data.fields && data.fields.length);
  exifEmpty.classList.toggle("hidden", hasFields);
  document.getElementById("exifTable").classList.toggle("hidden", !hasFields);
  document.querySelector(".exif-table-wrap").classList.toggle("hidden", !hasFields);
}

function showStatus(message, isError = false) {
  statusBox.classList.remove("hidden");
  statusBox.classList.toggle("error", isError);
  statusText.textContent = message;
}

function paintResult() {
  if (!lastResult || !downloadUrl) return;
  downloadLink.href = downloadUrl;
  downloadLink.download = lastResult.name;
  downloadLink.textContent = lastResult.batch ? t("common.downloadZip") : t("common.downloadImage");
  resultName.textContent = lastResult.name;
  resultMeta.textContent = lastResult.batch
    ? t("common.batchResult", { ok: lastResult.ok, fail: lastResult.fail })
    : lastResult.message;
  resultBox.classList.remove("hidden");
}

function refreshI18n() {
  if (selectedFiles.length) fileName.textContent = filesCaption(selectedFiles);
  if (busy) {
    btnText.textContent = t("common.processing");
  } else {
    btnText.textContent = startLabel();
  }
  if (lastExif) renderExif(lastExif);
  if (!resultBox.classList.contains("hidden")) paintResult();
}

async function submit() {
  if (!selectedFiles.length) return;
  const batch = selectedFiles.length > 1;
  lastResult = null;
  busy = true;
  submitBtn.disabled = true;
  btnText.textContent = t("common.processing");
  btnSpinner.classList.remove("hidden");
  showStatus(batch ? t("exif.batchWorking", { n: selectedFiles.length }) : t("exif.working"));

  const formData = new FormData();
  if (batch) {
    selectedFiles.forEach((file) => formData.append("files", file));
  } else {
    formData.append("file", selectedFiles[0]);
  }

  try {
    const res = await fetch(batch ? "/api/image/exif-strip-batch" : "/api/image/exif-strip", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(typeof err.detail === "string" ? err.detail : t("common.fail"));
    }
    const blob = await res.blob();
    const outName = parseFilename(
      res.headers.get("Content-Disposition") || "",
      batch ? "images-noexif.zip" : "noexif.jpg",
    );
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(blob);
    lastResult = batch
      ? {
          batch: true,
          name: outName,
          ok: res.headers.get("X-Batch-Ok") || "?",
          fail: res.headers.get("X-Batch-Failed") || "0",
        }
      : {
          batch: false,
          name: outName,
          message: decodeURIComponent(res.headers.get("X-Exif-Message") || t("exif.doneFallback")),
        };
    statusBox.classList.add("hidden");
    paintResult();
  } catch (err) {
    showStatus(err.message || t("common.fail"), true);
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
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  addFiles(Array.from(e.dataTransfer.files));
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
  const item = e.target.closest("[data-index]");
  if (!item) return;
  activeIndex = Number(item.dataset.index);
  renderQueue();
  inspectActive();
});
submitBtn.addEventListener("click", submit);
document.addEventListener("lt-i18n", refreshI18n);
