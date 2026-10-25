let csvFile = null;
let excelFile = null;

const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const csvTitle = document.getElementById("dropCsv").querySelector(".dropzone-title");
const excelTitle = document.getElementById("dropExcel").querySelector(".dropzone-title");

function showStatus(msg, isError = false) {
  statusBox.classList.remove("hidden");
  statusBox.classList.toggle("error", isError);
  statusText.textContent = msg;
}

async function downloadFromResponse(res, fallbackName) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || t("csv.fail"));
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
  const name = match ? decodeURIComponent(match[1].replace(/"/g, "")) : fallbackName;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

function bindDropzone(zone, input, onFile) {
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => { if (input.files[0]) onFile(input.files[0]); });
}

bindDropzone(document.getElementById("dropCsv"), document.getElementById("csvInput"), (f) => {
  csvFile = f;
  document.getElementById("btnCsvToExcel").disabled = false;
  csvTitle.textContent = f.name;
});

bindDropzone(document.getElementById("dropExcel"), document.getElementById("excelInput"), (f) => {
  excelFile = f;
  document.getElementById("btnExcelToCsv").disabled = false;
  excelTitle.textContent = f.name;
});

document.getElementById("btnCsvToExcel").addEventListener("click", async () => {
  if (!csvFile) return;
  const formData = new FormData();
  formData.append("file", csvFile);
  try {
    showStatus(t("csv.working"));
    await downloadFromResponse(await fetch("/api/csv/to-excel", { method: "POST", body: formData }), "output.xlsx");
    showStatus(t("csv.excelDone"));
    statusBox.classList.remove("error");
  } catch (e) {
    showStatus(e.message, true);
  }
});

document.getElementById("btnExcelToCsv").addEventListener("click", async () => {
  if (!excelFile) return;
  const formData = new FormData();
  formData.append("file", excelFile);
  formData.append("sheet", document.getElementById("sheetName").value.trim() || "0");
  try {
    showStatus(t("csv.working"));
    await downloadFromResponse(await fetch("/api/excel/to-csv", { method: "POST", body: formData }), "output.csv");
    showStatus(t("csv.csvDone"));
    statusBox.classList.remove("error");
  } catch (e) {
    showStatus(e.message, true);
  }
});

document.addEventListener("lt-i18n", () => {
  if (csvFile) csvTitle.textContent = csvFile.name;
  if (excelFile) excelTitle.textContent = excelFile.name;
});
