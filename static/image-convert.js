let selectedFile = null;
let downloadUrl = null;
let previewUrl = null;

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const clearBtn = document.getElementById("clearBtn");
const previewRow = document.getElementById("previewRow");
const imagePreview = document.getElementById("imagePreview");
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

function setFile(file) {
  selectedFile = file;
  if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
  if (file) {
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    filePreview.classList.remove("hidden");
    previewUrl = URL.createObjectURL(file);
    imagePreview.src = previewUrl;
    previewRow.classList.remove("hidden");
    submitBtn.disabled = false;
  } else {
    filePreview.classList.add("hidden");
    previewRow.classList.add("hidden");
    submitBtn.disabled = true;
  }
  resultBox.classList.add("hidden");
  statusBox.classList.add("hidden");
  if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = null; }
}

async function loadFormats() {
  const res = await fetch("/api/image/export-formats");
  const formats = await res.json();
  formatSelect.innerHTML = formats.map((f) => `<option value="${f.id}">${f.label}</option>`).join("");
}

async function submit() {
  if (!selectedFile) return;
  submitBtn.disabled = true;
  btnText.textContent = "转换中…";
  btnSpinner.classList.remove("hidden");
  statusBox.classList.remove("hidden");
  statusText.textContent = "正在处理图片…";

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("output_format", formatSelect.value);
  formData.append("width", widthInput.value);
  formData.append("height", heightInput.value);
  formData.append("resize_mode", resizeMode.value);

  try {
    const res = await fetch("/api/image/transform", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "转换失败");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
    const outName = match ? decodeURIComponent(match[1].replace(/"/g, "")) : "converted.jpg";
    const w = res.headers.get("X-Output-Width");
    const h = res.headers.get("X-Output-Height");
    downloadUrl = URL.createObjectURL(blob);
    downloadLink.href = downloadUrl;
    downloadLink.download = outName;
    resultName.textContent = outName;
    resultMeta.textContent = w && h ? `输出尺寸：${w} × ${h} px` : "";
    statusBox.classList.add("hidden");
    resultBox.classList.remove("hidden");
  } catch (e) {
    statusBox.classList.add("error");
    statusText.textContent = e.message;
  } finally {
    submitBtn.disabled = !selectedFile;
    btnText.textContent = "开始转换";
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
loadFormats();
