const inputArea = document.getElementById("inputArea");
const outputArea = document.getElementById("outputArea");
const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("statusText");

function showStatus(msg, isError = false) {
  statusBox.classList.remove("hidden");
  statusBox.classList.toggle("error", isError);
  statusText.textContent = msg;
}

function hideStatus() {
  statusBox.classList.add("hidden");
}

function parseInput() {
  const text = inputArea.value.trim();
  if (!text) throw new Error("请输入 JSON 文本");
  return JSON.parse(text);
}

document.getElementById("btnFormat").addEventListener("click", () => {
  try {
    const obj = parseInput();
    outputArea.value = JSON.stringify(obj, null, 2);
    hideStatus();
  } catch (e) {
    outputArea.value = "";
    showStatus(e instanceof SyntaxError ? `JSON 语法错误：${e.message}` : e.message, true);
  }
});

document.getElementById("btnMinify").addEventListener("click", () => {
  try {
    const obj = parseInput();
    outputArea.value = JSON.stringify(obj);
    hideStatus();
  } catch (e) {
    outputArea.value = "";
    showStatus(e instanceof SyntaxError ? `JSON 语法错误：${e.message}` : e.message, true);
  }
});

document.getElementById("btnValidate").addEventListener("click", () => {
  try {
    parseInput();
    outputArea.value = "✓ JSON 格式有效";
    showStatus("校验通过");
    statusBox.classList.remove("error");
  } catch (e) {
    outputArea.value = "";
    showStatus(e instanceof SyntaxError ? `JSON 语法错误：${e.message}` : e.message, true);
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
  showStatus("已复制到剪贴板");
  statusBox.classList.remove("error");
});
