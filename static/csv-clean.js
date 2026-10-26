const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const fileQueue = document.getElementById("fileQueue");
const dropEmpty = document.getElementById("dropEmpty");
const dedupe = document.getElementById("dedupe");
const keepInput = document.getElementById("keepInput");
const submitBtn = document.getElementById("submitBtn");
const btnText = submitBtn.querySelector(".btn-text");
const btnSpinner = submitBtn.querySelector(".btn-spinner");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const resultBox = document.getElementById("resultBox");
const resultName = document.getElementById("resultName");
const resultMeta = document.getElementById("resultMeta");
const resultErrors = document.getElementById("resultErrors");
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
  return t("common.andMoreFiles", { name: files[0].name, n: files.length });
}

function recordHistory(summary) {
  window.ltHistory?.record({
    toolKey: "hub.text.clean",
    href: "/csv-clean.html",
    summary,
  });
}

function startLabel() {
  return selectedFiles.length > 1 ? t("clean.batchStart", { n: selectedFiles.length }) : t("clean.start");
}

function addFiles(incoming) {
  const csvs = incoming.filter((file) => file.name.toLowerCase().endsWith(".csv"));
  if (!csvs.length) return;
  const merged = new Map(selectedFiles.map((file) => [fileKey(file), file]));
  for (const file of csvs) merged.set(fileKey(file), file);
  setFiles([...merged.values()].slice(0, 50));
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
  renderBatchErrors([]);
  if (!files.length) {
    filePreview.classList.add("hidden");
    fileQueue.classList.add("hidden");
    fileQueue.innerHTML = "";
    submitBtn.disabled = true;
    btnText.textContent = t("clean.start");
    return;
  }
  const total = files.reduce((sum, file) => sum + file.size, 0);
  fileName.textContent = filesCaption(files);
  fileSize.textContent = formatBytes(total);
  filePreview.classList.remove("hidden");
  submitBtn.disabled = false;
  btnText.textContent = startLabel();
  renderQueue();
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
  downloadLink.textContent = lastResult.batch ? t("common.downloadZip") : t("common.download");
  resultName.textContent = lastResult.name;
  resultMeta.textContent = lastResult.batch
    ? t("common.batchResult", { ok: lastResult.ok, fail: lastResult.fail })
    : (lastResult.message || "");
  renderBatchErrors(lastResult.errors || []);
  resultBox.classList.remove("hidden");
}

function refreshI18n() {
  if (selectedFiles.length) {
    fileName.textContent = filesCaption(selectedFiles);
    renderQueue();
  }
  if (!busy) btnText.textContent = selectedFiles.length ? startLabel() : t("clean.start");
  if (!resultBox.classList.contains("hidden")) paintResult();
}

async function submit() {
  if (!selectedFiles.length) return;
  const batch = selectedFiles.length > 1;
  lastResult = null;
  resultBox.classList.add("hidden");
  busy = true;
  submitBtn.disabled = true;
  btnText.textContent = t("common.processing");
  btnSpinner.classList.remove("hidden");
  statusBox.classList.remove("hidden", "error");
  statusText.textContent = t("common.wait");

  const formData = new FormData();
  formData.append("drop_empty", dropEmpty.checked ? "true" : "false");
  formData.append("dedupe", dedupe.checked ? "true" : "false");
  formData.append("keep", keepInput.value.trim());
  if (batch) selectedFiles.forEach((file) => formData.append("files", file));
  else formData.append("file", selectedFiles[0]);

  try {
    const res = await fetch(batch ? "/api/csv/clean-batch" : "/api/csv/clean", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(typeof err.detail === "string" ? err.detail : t("common.fail"));
    }
    const blob = await res.blob();
    const outName = parseFilename(res.headers.get("Content-Disposition") || "", batch ? "cleaned-csv.zip" : "clean.csv");
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(blob);
    lastResult = batch
      ? {
          batch: true,
          name: outName,
          ok: Number(res.headers.get("X-Batch-Ok") || 0),
          fail: Number(res.headers.get("X-Batch-Failed") || 0),
          errors: parseBatchErrors(res.headers.get("X-Batch-Errors")),
        }
      : {
          batch: false,
          name: outName,
          message: decodeURIComponent(res.headers.get("X-Csv-Message") || ""),
        };
    statusBox.classList.add("hidden");
    recordHistory(
      batch
        ? `${filesCaption(selectedFiles)} -> ${lastResult.name} (${t("common.batchResult", { ok: lastResult.ok, fail: lastResult.fail })})`
        : `${selectedFiles[0].name} -> ${lastResult.name}`
    );
    paintResult();
  } catch (err) {
    statusBox.classList.add("error");
    statusText.textContent = err.message || t("common.fail");
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
  const btn = e.target.closest("[data-remove-index]");
  if (!btn) return;
  setFiles(selectedFiles.filter((_, index) => index !== Number(btn.dataset.removeIndex)));
});
submitBtn.addEventListener("click", submit);
document.addEventListener("lt-i18n", refreshI18n);
