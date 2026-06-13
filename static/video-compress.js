let selectedFile = null;
let downloadUrl = null;

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const formatSelect = document.getElementById("formatSelect");
const resolutionSelect = document.getElementById("resolutionSelect");
const crfRange = document.getElementById("crfRange");
const crfValue = document.getElementById("crfValue");
const submitBtn = document.getElementById("submitBtn");
const btnText = submitBtn.querySelector(".btn-text");
const btnSpinner = submitBtn.querySelector(".btn-spinner");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const resultBox = document.getElementById("resultBox");
const resultName = document.getElementById("resultName");
const sizeStats = document.getElementById("sizeStats");
const downloadLink = document.getElementById("downloadLink");

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
    submitBtn.disabled = false;
  } else {
    filePreview.classList.add("hidden");
    submitBtn.disabled = true;
  }
  resultBox.classList.add("hidden");
  statusBox.classList.add("hidden");
  if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = null; }
}

crfRange.addEventListener("input", () => { crfValue.textContent = crfRange.value; });

async function loadOptions() {
  const res = await fetch("/api/video/compress-options");
  const data = await res.json();
  formatSelect.innerHTML = data.formats.map((f) => `<option value="${f.id}">${f.label}</option>`).join("");
  resolutionSelect.innerHTML = data.resolutions.map((r) => `<option value="${r.id}">${r.label}</option>`).join("");
}

async function submit() {
  if (!selectedFile) return;
  submitBtn.disabled = true;
  btnText.textContent = "正在压缩…";
  btnSpinner.classList.remove("hidden");
  statusBox.classList.remove("hidden");
  statusText.textContent = "视频压缩中，请耐心等待…";

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("format", formatSelect.value);
  formData.append("crf", crfRange.value);
  formData.append("resolution", resolutionSelect.value);

  try {
    const res = await fetch("/api/video/compress", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "压缩失败");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
    const outName = match ? decodeURIComponent(match[1].replace(/"/g, "")) : "compressed.mp4";
    const orig = res.headers.get("X-Original-Size");
    const comp = res.headers.get("X-Compressed-Size");
    downloadUrl = URL.createObjectURL(blob);
    downloadLink.href = downloadUrl;
    downloadLink.download = outName;
    resultName.textContent = outName;
    if (orig && comp) {
      const pct = (((orig - comp) / orig) * 100).toFixed(1);
      sizeStats.innerHTML = `<span><strong>${formatBytes(+orig)}</strong> → <strong>${formatBytes(+comp)}</strong></span><span class="size-reduction">减小 ${pct}%</span>`;
    }
    statusBox.classList.add("hidden");
    resultBox.classList.remove("hidden");
  } catch (e) {
    statusBox.classList.remove("hidden");
    statusBox.classList.add("error");
    statusText.textContent = e.message;
  } finally {
    submitBtn.disabled = !selectedFile;
    btnText.textContent = "开始压缩";
    btnSpinner.classList.add("hidden");
  }
}

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });
fileInput.addEventListener("change", () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });
clearBtn.addEventListener("click", () => { fileInput.value = ""; setFile(null); });
submitBtn.addEventListener("click", submit);
loadOptions();
