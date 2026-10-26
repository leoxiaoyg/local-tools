let conversions = [];
let selectedFiles = [];
let downloadUrl = null;
let busy = false;

const conversionSelect = document.getElementById("conversionSelect");
const conversionHint = document.getElementById("conversionHint");
const officeWarning = document.getElementById("officeWarning");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const dropHint = document.getElementById("dropHint");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const submitBtn = document.getElementById("submitBtn");
const btnText = submitBtn.querySelector(".btn-text");
const btnSpinner = submitBtn.querySelector(".btn-spinner");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const resultBox = document.getElementById("resultBox");
const resultName = document.getElementById("resultName");
const downloadLink = document.getElementById("downloadLink");

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function currentMeta() {
  return conversions.find((c) => c.id === conversionSelect.value) || null;
}

function filesCaption(files) {
  if (files.length === 1) return files[0].name;
  return t("common.andMoreFilesLong", { name: files[0].name, n: files.length });
}

function recordHistory(summary) {
  window.ltHistory?.record({
    toolKey: "hub.doc.convert",
    href: "/doc-convert.html",
    summary,
  });
}

function setFiles(files) {
  selectedFiles = files;
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
  }
  resultBox.classList.add("hidden");
  statusBox.classList.add("hidden");
  statusBox.classList.remove("error");

  if (!files.length) {
    filePreview.classList.add("hidden");
    submitBtn.disabled = true;
    return;
  }

  const total = files.reduce((sum, f) => sum + f.size, 0);
  fileName.textContent = filesCaption(files);
  fileSize.textContent = formatBytes(total);
  filePreview.classList.remove("hidden");
  submitBtn.disabled = false;
}

function fillConversionOptions() {
  const current = conversionSelect.value;
  conversionSelect.innerHTML = conversions
    .map((c) => {
      const mark = c.needs_office && !c.available ? t("doc.needOffice") : "";
      return `<option value="${c.id}">${c.label}${mark}</option>`;
    })
    .join("");
  if (current && conversions.some((c) => c.id === current)) {
    conversionSelect.value = current;
  }
}

function applyConversionLabels() {
  const meta = currentMeta();
  if (!meta) {
    dropHint.textContent = t("doc.pickType");
    return;
  }

  conversionHint.textContent = meta.hint || "";
  fileInput.accept = meta.accept || "";
  fileInput.multiple = !!meta.multiple;
  dropHint.textContent = meta.multiple
    ? t("doc.acceptMany", { accept: meta.accept })
    : t("doc.acceptOne", { accept: meta.accept });

  if (meta.needs_office && !meta.available) {
    officeWarning.textContent = t("doc.officeMissing");
    officeWarning.classList.remove("hidden");
  } else if (meta.needs_office) {
    officeWarning.textContent = t("doc.officeOk");
    officeWarning.classList.remove("hidden");
  } else {
    officeWarning.classList.add("hidden");
  }
}

function applyConversionUI() {
  applyConversionLabels();
  setFiles([]);
  fileInput.value = "";
}

async function loadConversions(resetFiles = true) {
  const res = await fetch("/api/doc/conversions");
  if (!res.ok) throw new Error(t("doc.loadFail"));
  const data = await res.json();
  conversions = data.conversions || [];
  fillConversionOptions();
  if (resetFiles) applyConversionUI();
  else applyConversionLabels();
}

async function submit() {
  const meta = currentMeta();
  if (!meta || !selectedFiles.length) return;
  if (meta.needs_office && !meta.available) {
    statusBox.classList.remove("hidden");
    statusBox.classList.add("error");
    statusText.textContent = t("doc.noEngine");
    return;
  }

  busy = true;
  submitBtn.disabled = true;
  btnText.textContent = t("doc.working");
  btnSpinner.classList.remove("hidden");
  statusBox.classList.remove("hidden", "error");
  statusText.textContent = t("doc.wait");
  resultBox.classList.add("hidden");

  const formData = new FormData();
  formData.append("conversion", meta.id);
  selectedFiles.forEach((f) => formData.append("files", f));

  try {
    const res = await fetch("/api/doc/convert", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail;
      throw new Error(typeof detail === "string" ? detail : t("doc.fail"));
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
    const outName = match ? decodeURIComponent(match[1].replace(/"/g, "")) : "converted.bin";
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(blob);
    downloadLink.href = downloadUrl;
    downloadLink.download = outName;
    resultName.textContent = outName;
    statusBox.classList.add("hidden");
    recordHistory(`${filesCaption(selectedFiles)} -> ${outName}`);
    resultBox.classList.remove("hidden");
  } catch (e) {
    statusBox.classList.add("error");
    statusText.textContent = e.message;
  } finally {
    busy = false;
    submitBtn.disabled = !selectedFiles.length;
    btnText.textContent = t("doc.start");
    btnSpinner.classList.add("hidden");
  }
}

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  const files = [...e.dataTransfer.files];
  if (!files.length) return;
  const meta = currentMeta();
  setFiles(meta && meta.multiple ? files : [files[0]]);
});
fileInput.addEventListener("change", () => {
  if (!fileInput.files.length) return;
  setFiles([...fileInput.files]);
});
clearBtn.addEventListener("click", () => {
  fileInput.value = "";
  setFiles([]);
});
conversionSelect.addEventListener("change", applyConversionUI);
submitBtn.addEventListener("click", submit);
document.addEventListener("lt-i18n", () => {
  loadConversions(false).then(() => {
    if (selectedFiles.length) fileName.textContent = filesCaption(selectedFiles);
    if (!busy) btnText.textContent = t("doc.start");
  }).catch((e) => {
    statusBox.classList.remove("hidden");
    statusBox.classList.add("error");
    statusText.textContent = e.message;
  });
});
loadConversions().catch((e) => {
  statusBox.classList.remove("hidden");
  statusBox.classList.add("error");
  statusText.textContent = e.message;
});
