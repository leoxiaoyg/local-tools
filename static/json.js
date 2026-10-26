const inputArea = document.getElementById("inputArea");
const outputArea = document.getElementById("outputArea");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");

let lastStatus = null;

function showStatus(msg, isError = false) {
  statusBox.classList.remove("hidden");
  statusBox.classList.toggle("error", isError);
  statusText.textContent = msg;
}

function recordHistory(summary) {
  window.ltHistory?.record({
    toolKey: "hub.text.json",
    href: "/json.html",
    summary,
  });
}

function hideStatus() {
  lastStatus = null;
  statusBox.classList.add("hidden");
}

function parseInput() {
  const text = inputArea.value.trim();
  if (!text) throw new Error(t("json.needText"));
  return JSON.parse(text);
}

function syntaxMessage(err) {
  return err instanceof SyntaxError ? t("json.syntax", { msg: err.message }) : err.message;
}

function rememberError(err) {
  lastStatus = err instanceof SyntaxError
    ? { kind: "syntax", raw: err.message }
    : { kind: "need" };
}

document.getElementById("btnFormat").addEventListener("click", () => {
  try {
    const obj = parseInput();
    outputArea.value = JSON.stringify(obj, null, 2);
    hideStatus();
    recordHistory(t("history.json.format"));
  } catch (e) {
    outputArea.value = "";
    rememberError(e);
    showStatus(syntaxMessage(e), true);
  }
});

document.getElementById("btnMinify").addEventListener("click", () => {
  try {
    const obj = parseInput();
    outputArea.value = JSON.stringify(obj);
    hideStatus();
    recordHistory(t("history.json.minify"));
  } catch (e) {
    outputArea.value = "";
    rememberError(e);
    showStatus(syntaxMessage(e), true);
  }
});

document.getElementById("btnValidate").addEventListener("click", () => {
  try {
    parseInput();
    outputArea.value = t("json.valid");
    lastStatus = { kind: "ok" };
    showStatus(t("json.ok"));
    statusBox.classList.remove("error");
    recordHistory(t("history.json.validate"));
  } catch (e) {
    outputArea.value = "";
    rememberError(e);
    showStatus(syntaxMessage(e), true);
  }
});

document.getElementById("btnClear").addEventListener("click", () => {
  inputArea.value = "";
  outputArea.value = "";
  hideStatus();
});

document.getElementById("btnCopy").addEventListener("click", async () => {
  if (!outputArea.value) return;
  await navigator.clipboard.writeText(outputArea.value);
  lastStatus = { kind: "copied" };
  showStatus(t("json.copied"));
  statusBox.classList.remove("error");
});

document.addEventListener("lt-i18n", () => {
  if (!lastStatus) return;
  if (lastStatus.kind === "ok") {
    outputArea.value = t("json.valid");
    showStatus(t("json.ok"));
    statusBox.classList.remove("error");
  } else if (lastStatus.kind === "copied") {
    showStatus(t("json.copied"));
    statusBox.classList.remove("error");
  } else if (lastStatus.kind === "syntax") {
    showStatus(t("json.syntax", { msg: lastStatus.raw }), true);
  } else if (lastStatus.kind === "need") {
    showStatus(t("json.needText"), true);
  }
});
