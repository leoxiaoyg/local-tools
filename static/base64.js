const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");
const fileHint = document.getElementById("fileHint");

let selectedName = "";

function showStatus(msg, isError = false) {
  statusBox.classList.remove("hidden");
  statusBox.classList.toggle("error", isError);
  statusText.textContent = msg;
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("panelText").classList.toggle("hidden", tab.dataset.tab !== "text");
    document.getElementById("panelFile").classList.toggle("hidden", tab.dataset.tab !== "file");
  });
});

function stripDataUrl(value) {
  const raw = value.trim();
  return raw.includes(",") && raw.startsWith("data:") ? raw.split(",", 2)[1] : raw;
}

function bytesToBase64(bytes) {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

document.getElementById("btnEncodeText").addEventListener("click", () => {
  try {
    const bytes = new TextEncoder().encode(document.getElementById("textInput").value);
    let b64 = bytesToBase64(bytes);
    if (document.getElementById("urlSafe").checked) {
      b64 = b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    }
    document.getElementById("textOutput").value = b64;
    statusBox.classList.add("hidden");
  } catch {
    showStatus(t("b64.encodeFail"), true);
  }
});

document.getElementById("btnDecodeText").addEventListener("click", () => {
  try {
    let b64 = stripDataUrl(document.getElementById("textInput").value);
    if (document.getElementById("urlSafe").checked) {
      b64 = b64.replace(/-/g, "+").replace(/_/g, "/");
      while (b64.length % 4) b64 += "=";
    }
    const bin = atob(b64);
    const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
    document.getElementById("textOutput").value = new TextDecoder().decode(bytes);
    statusBox.classList.add("hidden");
  } catch {
    showStatus(t("b64.decodeFail"), true);
  }
});

document.getElementById("btnCopyText").addEventListener("click", async () => {
  const out = document.getElementById("textOutput").value;
  if (!out) return;
  await navigator.clipboard.writeText(out);
  showStatus(t("b64.copied"));
  statusBox.classList.remove("error");
});

document.getElementById("fileInput").addEventListener("change", async () => {
  const file = document.getElementById("fileInput").files[0];
  if (!file) return;
  selectedName = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  fileHint.textContent = selectedName;
  const formData = new FormData();
  formData.append("file", file);
  try {
    const res = await fetch("/api/base64/encode", { method: "POST", body: formData });
    if (!res.ok) throw new Error((await res.json()).detail || t("b64.encodeFail"));
    const data = await res.json();
    document.getElementById("fileOutput").value = data.text;
    statusBox.classList.add("hidden");
  } catch (e) {
    showStatus(e.message, true);
  }
});

document.getElementById("btnDecodeFile").addEventListener("click", async () => {
  const text = document.getElementById("decodeInput").value.trim();
  if (!text) { showStatus(t("b64.needB64"), true); return; }
  const formData = new FormData();
  formData.append("text", text);
  formData.append("filename", document.getElementById("decodeFilename").value || "decoded.bin");
  try {
    const res = await fetch("/api/base64/decode", { method: "POST", body: formData });
    if (!res.ok) throw new Error((await res.json()).detail || t("b64.decodeFail"));
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = formData.get("filename");
    a.click();
    URL.revokeObjectURL(a.href);
    showStatus(t("b64.fileDone"));
    statusBox.classList.remove("error");
  } catch (e) {
    showStatus(e.message, true);
  }
});

document.addEventListener("lt-i18n", () => {
  if (selectedName) fileHint.textContent = selectedName;
});
