(function () {
  const KEY = "lt-history-v1";
  const LIMIT = 20;

  function escapeHtml(text) {
    return String(text || "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[ch]));
  }

  function readEntries() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter((item) => item && item.toolKey) : [];
    } catch {
      return [];
    }
  }

  function writeEntries(entries) {
    try {
      localStorage.setItem(KEY, JSON.stringify(entries));
    } catch {
      /* ignore */
    }
  }

  function dispatch(entries) {
    document.dispatchEvent(new CustomEvent("lt-history", { detail: { entries } }));
  }

  function formatTime(iso) {
    try {
      const lang = window.ltI18n && window.ltI18n.lang === "en" ? "en-US" : "zh-CN";
      return new Intl.DateTimeFormat(lang, {
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(iso));
    } catch {
      return iso;
    }
  }

  function toolLabel(toolKey) {
    if (window.ltI18n && typeof window.ltI18n.t === "function") {
      return window.ltI18n.t(toolKey);
    }
    return toolKey;
  }

  function renderHub() {
    const list = document.getElementById("historyList");
    const empty = document.getElementById("historyEmpty");
    const clearBtn = document.getElementById("historyClear");
    if (!list || !empty || !clearBtn) return;

    const entries = readEntries();
    list.innerHTML = entries.map((item) => `
      <li class="history-item">
        <a class="history-link" href="${escapeHtml(item.href || "/")}">
          <div class="history-row">
            <strong>${escapeHtml(toolLabel(item.toolKey))}</strong>
            <span class="history-time">${escapeHtml(formatTime(item.createdAt))}</span>
          </div>
          <p class="history-summary">${escapeHtml(item.summary || "")}</p>
        </a>
      </li>
    `).join("");

    list.classList.toggle("hidden", !entries.length);
    empty.classList.toggle("hidden", !!entries.length);
    clearBtn.disabled = !entries.length;
  }

  function record(entry) {
    if (!entry || !entry.toolKey || !entry.summary) return;
    const next = [{
      toolKey: String(entry.toolKey),
      href: entry.href ? String(entry.href) : "/",
      summary: String(entry.summary),
      createdAt: new Date().toISOString(),
    }, ...readEntries()].slice(0, LIMIT);
    writeEntries(next);
    dispatch(next);
  }

  function clear() {
    writeEntries([]);
    dispatch([]);
  }

  function initHub() {
    const clearBtn = document.getElementById("historyClear");
    if (clearBtn && !clearBtn.dataset.bound) {
      clearBtn.dataset.bound = "true";
      clearBtn.addEventListener("click", clear);
    }
    renderHub();
  }

  window.ltHistory = {
    record,
    clear,
    getEntries: readEntries,
    renderHub,
  };

  document.addEventListener("lt-history", renderHub);
  document.addEventListener("lt-i18n", renderHub);
  window.addEventListener("storage", (event) => {
    if (event.key === KEY) renderHub();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initHub, { once: true });
  } else {
    initHub();
  }
})();
