const actionSelect = document.getElementById("actionSelect");
const actionHint = document.getElementById("actionHint");
const presetField = document.getElementById("presetField");
const presetSelect = document.getElementById("presetSelect");
const splitModeField = document.getElementById("splitModeField");
const splitModeSelect = document.getElementById("splitModeSelect");
const rangeField = document.getElementById("rangeField");
const rangeInput = document.getElementById("rangeInput");
const dropzone = document.getElementById("dropzone");
const dropHint = document.getElementById("dropHint");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const fileQueue = document.getElementById("fileQueue");
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
let downloadUrl = null;
let busy = false;
let lastResult = null;

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

function fileKey(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function filesCaption(files) {
  if (files.length === 1) return files[0].name;
  return t("common.andMoreFiles", { name: files[0].name, n: files.length });
}

function addFiles(incoming) {
  const pdfs = incoming.filter((file) => file.name.toLowerCase().endsWith(".pdf"));
  if (!pdfs.length) return;
  if (actionSelect.value === "split") {
    setFiles([pdfs[0]]);
    return;
  }
  const merged = new Map(selectedFiles.map((file) => [fileKey(file), file]));
  for (const file of pdfs) {
    merged.set(fileKey(file), file);
  }
  setFiles([...merged.values()].slice(0, 30));
}

function setFiles(files) {
  selectedFiles = files;
  lastResult = null;
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
  }
  resultBox.classList.add("hidden");
  statusBox.classList.add("hidden");

  if (!files.length) {
    filePreview.classList.add("hidden");
    fileQueue.classList.add("hidden");
    fileQueue.innerHTML = "";
    submitBtn.disabled = true;
    return;
  }

  const total = files.reduce((sum, file) => sum + file.size, 0);
  fileName.textContent = filesCaption(files);
  fileSize.textContent = formatBytes(total);
  filePreview.classList.remove("hidden");
  fileQueue.innerHTML = files
    .map((file, index) => `<li><span class="queue-name">${index + 1}. ${escapeHtml(file.name)}</span><span class="queue-size">${formatBytes(file.size)}</span></li>`)
    .join("");
  fileQueue.classList.toggle("hidden", !files.length);
  submitBtn.disabled = actionSelect.value === "merge" ? files.length < 2 : !files.length;
}

function applyActionChrome() {
  const action = actionSelect.value;
  actionHint.textContent = t(`pdf.hint.${action}`);
  presetField.classList.toggle("hidden", action !== "compress");
  splitModeField.classList.toggle("hidden", action !== "split");
  rangeField.classList.toggle("hidden", action !== "split" || splitModeSelect.value !== "range");
  fileInput.multiple = action !== "split";
  dropHint.textContent = action === "split" ? t("pdf.dropOne") : t("pdf.dropMany");
}

function applyActionUI() {
  applyActionChrome();
  setFiles(actionSelect.value === "split" ? selectedFiles.slice(0, 1) : selectedFiles);
}

function showStatus(message, isError = false) {
  statusBox.classList.remove("hidden");
  statusBox.classList.toggle("error", isError);
  statusText.textContent = message;
}

async function loadPresets() {
  const current = presetSelect.value || "standard";
  try {
    const res = await fetch("/api/pdf/options");
    const data = await res.json();
    presetSelect.innerHTML = (data.compress_presets || [])
      .map((item) => `<option value="${item.id}">${item.label}</option>`)
      .join("");
    if (!presetSelect.value) {
      presetSelect.innerHTML = `<option value="standard">${t("pdf.preset.standard")}</option>`;
    }
  } catch {
    presetSelect.innerHTML = `
      <option value="light">${t("pdf.preset.light")}</option>
      <option value="standard" selected>${t("pdf.preset.standard")}</option>
      <option value="strong">${t("pdf.preset.strong")}</option>
    `;
  }
  if ([...presetSelect.options].some((opt) => opt.value === current)) {
    presetSelect.value = current;
  }
}

function paintResult() {
  if (!lastResult || !downloadUrl) return;
  downloadLink.href = downloadUrl;
  downloadLink.download = lastResult.name;
  downloadLink.textContent = lastResult.zip ? t("common.downloadZip") : t("common.downloadPdf");
  resultName.textContent = lastResult.name;
  if (lastResult.failed != null) {
    resultMeta.textContent = t("common.batchResult", { ok: lastResult.ok, fail: lastResult.failed });
  } else if (lastResult.original && lastResult.output) {
    const prefix = lastResult.message ? `${lastResult.message} · ` : "";
    resultMeta.textContent = `${prefix}${formatBytes(lastResult.original)} → ${formatBytes(lastResult.output)}`;
  } else {
    resultMeta.textContent = lastResult.message || "";
  }
  resultBox.classList.remove("hidden");
}

function refreshI18n() {
  applyActionChrome();
  if (selectedFiles.length) fileName.textContent = filesCaption(selectedFiles);
  if (!busy) btnText.textContent = t("pdf.start");
  if (!resultBox.classList.contains("hidden")) paintResult();
  loadPresets();
}

async function submit() {
  const action = actionSelect.value;
  if (!selectedFiles.length) return;
  if (action === "merge" && selectedFiles.length < 2) {
    showStatus(t("pdf.needTwo"), true);
    return;
  }

  lastResult = null;
  busy = true;
  submitBtn.disabled = true;
  btnText.textContent = t("common.processing");
  btnSpinner.classList.remove("hidden");
  showStatus(t("common.wait"));

  const formData = new FormData();
  let url = "/api/pdf/merge";
  let fallbackName = "merged.pdf";

  if (action === "merge") {
    selectedFiles.forEach((file) => formData.append("files", file));
  } else if (action === "compress") {
    formData.append("preset", presetSelect.value || "standard");
    if (selectedFiles.length > 1) {
      selectedFiles.forEach((file) => formData.append("files", file));
      url = "/api/pdf/compress-batch";
      fallbackName = "compressed-pdfs.zip";
    } else {
      formData.append("file", selectedFiles[0]);
      url = "/api/pdf/compress";
      fallbackName = "compressed.pdf";
    }
  } else {
    formData.append("file", selectedFiles[0]);
    formData.append("mode", splitModeSelect.value);
    formData.append("ranges", rangeInput.value.trim());
    url = "/api/pdf/split";
    fallbackName = splitModeSelect.value === "pages" ? "pages.zip" : "extracted.pdf";
  }

  try {
    const res = await fetch(url, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(typeof err.detail === "string" ? err.detail : t("common.fail"));
    }
    const blob = await res.blob();
    const outName = parseFilename(res.headers.get("Content-Disposition") || "", fallbackName);
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(blob);
    const failed = res.headers.get("X-Batch-Failed");
    lastResult = {
      name: outName,
      zip: outName.toLowerCase().endsWith(".zip"),
      message: decodeURIComponent(res.headers.get("X-Pdf-Message") || ""),
      original: res.headers.get("X-Original-Size") ? Number(res.headers.get("X-Original-Size")) : null,
      output: (res.headers.get("X-Output-Size") || res.headers.get("X-Compressed-Size"))
        ? Number(res.headers.get("X-Output-Size") || res.headers.get("X-Compressed-Size"))
        : null,
      failed: failed != null ? failed : null,
      ok: res.headers.get("X-Batch-Ok") || "?",
    };
    statusBox.classList.add("hidden");
    paintResult();
  } catch (err) {
    showStatus(err.message || t("common.fail"), true);
  } finally {
    busy = false;
    submitBtn.disabled = action === "merge" ? selectedFiles.length < 2 : !selectedFiles.length;
    btnText.textContent = t("pdf.start");
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
actionSelect.addEventListener("change", applyActionUI);
splitModeSelect.addEventListener("change", applyActionUI);
submitBtn.addEventListener("click", submit);
document.addEventListener("lt-i18n", refreshI18n);

loadPresets().then(applyActionUI);
