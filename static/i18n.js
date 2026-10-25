(function () {
  const KEY = "lt-lang";
  const LANGS = ["zh", "en"];

  function detect() {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved && LANGS.includes(saved)) return saved;
    } catch {
      /* ignore */
    }
    const nav = String(navigator.language || "zh").toLowerCase();
    return nav.startsWith("zh") ? "zh" : "en";
  }

  let lang = detect();

  function t(key, vars) {
    const pack = window.LT_LOCALES || {};
    const dict = pack[lang] || {};
    const fallback = pack.zh || {};
    let text = dict[key] ?? fallback[key] ?? key;
    if (vars) {
      text = text.replace(/\{(\w+)\}/g, (_, name) => (
        vars[name] == null ? "" : String(vars[name])
      ));
    }
    return text;
  }

  function apply(root) {
    const scope = root || document;
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    const titleEl = document.querySelector("title[data-i18n]");
    if (titleEl) document.title = t(titleEl.getAttribute("data-i18n"));
    scope.querySelectorAll("[data-i18n]").forEach((el) => {
      if (el.tagName === "TITLE") return;
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    scope.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
    });
    scope.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria")));
    });
    scope.querySelectorAll(".lang-switch [data-lang]").forEach((btn) => {
      const active = btn.getAttribute("data-lang") === lang;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setLang(next) {
    if (!LANGS.includes(next) || next === lang) return;
    lang = next;
    try {
      localStorage.setItem(KEY, lang);
    } catch {
      /* ignore */
    }
    apply();
    document.dispatchEvent(new CustomEvent("lt-i18n", { detail: { lang } }));
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const headers = new Headers((init && init.headers) || {});
    if (!headers.has("Accept-Language")) {
      headers.set("Accept-Language", lang === "zh" ? "zh-CN,zh;q=0.9" : "en;q=0.9");
    }
    return nativeFetch(input, Object.assign({}, init, { headers }));
  };

  document.addEventListener("click", (event) => {
    const btn = event.target.closest(".lang-switch [data-lang]");
    if (!btn) return;
    setLang(btn.getAttribute("data-lang"));
  });

  window.t = t;
  window.ltI18n = {
    t,
    apply,
    setLang,
    get lang() { return lang; },
  };

  apply();
})();
