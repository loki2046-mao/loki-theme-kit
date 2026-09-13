/* 主题切换器（原生 JS，无依赖，可直接抄）
 *
 * 设计要点（这几条都是踩过坑才加上的）：
 *  1. 主题名存在 <html data-theme="…">，CSS 用 :root[data-theme="x"] 选择器接管，不需要 class 列表；
 *  2. 读 localStorage 必须放在「挂载之后」，不要在模块顶层读——服务端渲染时读到 undefined，
 *     客户端首帧读到记忆值，两边 HTML 不一致，React 会报 hydration mismatch；
 *  3. 想彻底没有首帧闪白，在 <head> 里放一个内联脚本（见 templates/theme-switcher-flash-guard.html），
 *     在样式之前就把 data-theme 设好。
 */

export const STORAGE_KEY = "loki_theme";
export const FALLBACK = "loki-ease";   // 装完套组后，把这里改成你想默认的那套

/** 切主题：只改一个属性 + 记一笔 */
export function applyTheme(id, root = document.documentElement) {
  root.dataset.theme = id;
  try { localStorage.setItem(STORAGE_KEY, id); } catch { /* 隐私模式下写不进去，忽略 */ }
}

/** 恢复上次选择；没有记忆或记忆的主题已经不存在 → 用 fallback */
export function restoreTheme(availableIds, root = document.documentElement) {
  let saved = null;
  try { saved = localStorage.getItem(STORAGE_KEY); } catch { /* ignore */ }
  const id = availableIds.includes(saved) ? saved : FALLBACK;
  root.dataset.theme = id;
  return id;
}

/**
 * 造一个切换器元素，塞进 mount。
 * @param {{sets: Array<{id:string,label:string,group?:string,accent?:string,surface?:string}>, mount: HTMLElement, groups?: Record<string,string>}} opts
 */
export function createThemeSwitcher({ sets, mount, groups = {} }) {
  const box = document.createElement("details");
  box.className = "lk-theme-picker";
  const current = document.documentElement.dataset.theme || FALLBACK;
  const cur = sets.find((s) => s.id === current);

  box.innerHTML = `
    <summary class="lk-theme-summary">
      <span class="lk-theme-dot" style="background:${(cur && cur.accent) || "#888"}"></span>
      <span>外观</span>
      <span class="lk-theme-current">${(cur && cur.label) || current}</span>
    </summary>
    <div class="lk-theme-panel" role="listbox"></div>`;
  const panel = box.querySelector(".lk-theme-panel");

  const byGroup = {};
  for (const s of sets) (byGroup[s.group || ""] ||= []).push(s);

  for (const [g, list] of Object.entries(byGroup)) {
    if (g && groups[g]) {
      const h = document.createElement("div");
      h.className = "lk-theme-group";
      h.textContent = groups[g];
      panel.appendChild(h);
    }
    for (const s of list) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "lk-theme-item";
      b.dataset.themeId = s.id;
      b.setAttribute("role", "option");
      b.setAttribute("aria-selected", String(s.id === current));
      b.innerHTML = `<span class="lk-theme-swatch" style="background:${s.surface || "#fff"}">
                       <i style="background:${s.accent || "#888"}"></i></span>
                     <span class="lk-theme-label">${s.label || s.id}</span>`;
      b.onclick = () => {
        applyTheme(s.id);
        panel.querySelectorAll(".lk-theme-item").forEach((x) =>
          x.setAttribute("aria-selected", String(x.dataset.themeId === s.id)));
        box.querySelector(".lk-theme-current").textContent = s.label || s.id;
        const dot = box.querySelector(".lk-theme-dot");
        if (dot) dot.style.background = s.accent || "#888";
      };
      panel.appendChild(b);
    }
  }
  mount.appendChild(box);
  return box;
}
