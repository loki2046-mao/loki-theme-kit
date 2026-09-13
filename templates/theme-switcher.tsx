"use client";
/* 主题切换器（React / Next.js App Router 版，可直接抄）
 *
 * 这个文件里有两个坑是我真踩过的，别绕过去：
 *  1. localStorage 不能在 useState 初值里读。
 *     服务端渲染拿不到 localStorage → width/主题名两边不一致 → React 报
 *     "A tree hydrated but some attributes of the server rendered HTML didn't match"。
 *     正确做法：初值用「服务端也能算出来的同一个值」，挂载后在 useEffect 里回填记忆值。
 *  2. 首帧闪默认色：靠 <head> 里的内联脚本解决（见 theme-switcher-flash-guard.html），
 *     不要在 React 里抢这一帧——组件挂载时第一帧已经画完了。
 */
import { useEffect, useState } from "react";

export const STORAGE_KEY = "loki_theme";
export const FALLBACK = "loki-ease";

export type ThemeItem = {
  id: string;
  label: string;
  group?: string;
  accent?: string;
  surface?: string;
};

const GROUP_LABELS: Record<string, string> = {
  care: "护眼阅读",
  art: "艺术风格",
  retro: "复古屏幕",
  calm: "安静工作",
};

export function applyTheme(id: string) {
  document.documentElement.dataset.theme = id;
  try { localStorage.setItem(STORAGE_KEY, id); } catch {}
}

export default function ThemeSwitcher({ sets }: { sets: ThemeItem[] }) {
  // ① 初值 = 服务端也会得到的值（FALLBACK），保证首帧两端一致
  const [current, setCurrent] = useState<string>(FALLBACK);

  // ② 挂载后才读记忆值
  useEffect(() => {
    let saved: string | null = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch {}
    const id = saved && sets.some((s) => s.id === saved) ? saved : FALLBACK;
    setCurrent(id);
    document.documentElement.dataset.theme = id;
  }, [sets]);

  const cur = sets.find((s) => s.id === current);
  const groups: string[] = [];
  for (const s of sets) {
    const g = s.group ?? "";
    if (g && !groups.includes(g)) groups.push(g);
  }

  return (
    <details className="lk-theme-picker">
      <summary className="lk-theme-summary">
        <span className="lk-theme-dot" style={{ background: cur?.accent ?? "#888" }} />
        <span>外观</span>
        <span className="lk-theme-current">{cur?.label ?? current}</span>
      </summary>
      <div className="lk-theme-panel">
        {groups.map((g) => (
          <div key={g}>
            <div className="lk-theme-group">{GROUP_LABELS[g] ?? g}</div>
            {sets.filter((s) => s.group === g).map((s) => (
              <button
                key={s.id}
                type="button"
                className="lk-theme-item"
                aria-selected={s.id === current}
                onClick={() => { applyTheme(s.id); setCurrent(s.id); }}
              >
                <span className="lk-theme-swatch" style={{ background: s.surface ?? "#fff" }}>
                  <i style={{ background: s.accent ?? "#888" }} />
                </span>
                <span className="lk-theme-label">{s.label}</span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </details>
  );
}
