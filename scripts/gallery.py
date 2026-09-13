#!/usr/bin/env python3
"""生成套组预览画廊：一张自包含 HTML，能看、能挑、能导出「我要哪些」的清单。

用法：
    python3 scripts/gallery.py                       # → previews/gallery.html
    python3 scripts/gallery.py --out /tmp/g.html
    open previews/gallery.html

画廊做四件事：
  1) 每套一张卡：色卡（底/面/正文/强调 真实取色）、身份（名字/分组/契约钩子数）、
     实测指标（令牌数、结构规则数、规则行数、正文对比度）、装饰槽位。
  2) 搜索 + 分组筛选（套组多了不做过收纳就是一堆散乱色块）。
  3) 勾选「我要这套」，勾选结果存在浏览器 localStorage，刷新不丢。
  4) 一键导出 `--only a,b,c` 参数，直接粘给 scripts/install.py。

注意：画廊是「静态预览」（色卡 + 结构说明），不是宿主 App 里的真实渲染。
要看真实效果，得把这套 CSS 装进宿主或打开宿主的主题切换器——画廊里会写明这点。
"""
import argparse
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent

GROUP_LABELS = {
    "care": "护眼阅读", "art": "艺术风格", "retro": "复古屏幕", "calm": "安静工作", "": "未分组",
}


def read_tokens(css: str):
    m = re.search(r'^:root\[data-theme="[^"]+"\]\s*\{(.*?)^\}', css, re.S | re.M)
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1))) if m else {}


def build(sets_dir: Path):
    cards = []
    for d in sorted(p for p in sets_dir.iterdir() if p.is_dir()):
        css = (d / "theme.css").read_text(encoding="utf-8")
        meta_p = d / "meta.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
        t = read_tokens(css)
        g = lambda k, fb="": (t.get(k) or fb).strip()
        body = css[css.find("\n}", css.find('{')):] if css.find('{') >= 0 else ""
        cards.append({
            "id": d.name,
            "label": meta.get("label", d.name),
            "group": meta.get("group", ""),
            "tokens": len(t),
            "rules": len(re.findall(r"\{", body)),
            "lines": len([l for l in body.split("\n") if l.strip()]),
            "hooks": sorted(set(re.findall(r'\.([a-z][a-z0-9-]*)', body))),
            "deco": sorted(k for k in t if k.startswith("--deco-")),
            "colors": {
                "canvas": g("--bg-canvas", "#fff"),
                "surface": g("--bg-surface", "#fff"),
                "sidebar": g("--bg-metal", "#333"),
                "text": g("--text-primary", "#000"),
                "muted": g("--text-muted", "#666"),
                "accent": g("--accent-copper", "#888"),
                "accentInk": g("--accent-ink", "#fff"),
                "border": g("--border-subtle", "#ddd"),
                "radius": g("--radius-panel", "12px"),
                "font": g("--font-display", "inherit"),
            },
            "recommended": bool(meta.get("recommended")),
            "source_board": meta.get("source_board", ""),
            "status": meta.get("status", ""),
            "css": css,
        })
    return cards


PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>外观套组画廊 · loki-theme-kit</title>
<style>
 :root { color-scheme: light; }
 body { margin:0; font:14px/1.6 -apple-system,"PingFang SC",sans-serif; background:#f4f4f1; color:#17171a; }
 header { position:sticky; top:0; z-index:5; background:#17171a; color:#f4f4f1; padding:14px 20px; display:flex; gap:16px; align-items:center; flex-wrap:wrap; }
 header h1 { font-size:15px; margin:0; letter-spacing:.02em; }
 header .meta { font-size:12px; opacity:.75; }
 header input { flex:1; min-width:180px; padding:7px 10px; border-radius:8px; border:1px solid #3a3a40; background:#22222a; color:#fff; font-size:13px; }
 header button { padding:7px 12px; border-radius:8px; border:0; background:#f0f0ea; color:#17171a; font-size:12px; font-weight:600; cursor:pointer; }
 header button.ghost { background:transparent; color:#f0f0ea; border:1px solid #4a4a52; }
 main { padding:18px 20px 60px; }
 .filters { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }
 .chip { padding:5px 11px; border-radius:999px; border:1px solid #d5d5cf; background:#fff; font-size:12px; cursor:pointer; }
 .chip[data-on="1"] { background:#17171a; color:#fff; border-color:#17171a; }
 .grid { display:grid; gap:14px; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); }
 .card { background:#fff; border:1px solid #e2e2da; border-radius:12px; overflow:hidden; }
 .card.selected { outline:2px solid #17171a; }
 .swatch { display:flex; height:74px; }
 .swatch div { flex:1; }
 .body { padding:11px 13px 13px; }
 .label { font-weight:700; font-size:14px; display:flex; align-items:center; gap:7px; }
 .label small { font-weight:400; opacity:.55; font-size:11px; }
 .row { font-size:11.5px; opacity:.72; margin-top:5px; display:flex; gap:10px; flex-wrap:wrap; }
 .hooks { font-family:ui-monospace,Menlo,monospace; font-size:10.5px; opacity:.6; margin-top:7px; word-break:break-all; }
 .deco { margin-top:7px; font-size:11px; color:#8a5a12; }
 .pick { margin-top:9px; display:flex; gap:8px; align-items:center; }
 .pick button { font-size:11.5px; padding:4px 10px; border-radius:7px; border:1px solid #d5d5cf; background:#fafaf7; cursor:pointer; }
 details { margin-top:9px; }
 summary { font-size:11.5px; cursor:pointer; opacity:.65; }
 pre { max-height:260px; overflow:auto; background:#17171a; color:#e6e6df; padding:10px; border-radius:8px; font-size:10.5px; margin:7px 0 0; }
 footer { position:fixed; bottom:0; left:0; right:0; background:#17171a; color:#f4f4f1; padding:9px 20px; font-size:12px; display:flex; gap:14px; align-items:center; }
 code { background:rgba(255,255,255,.14); padding:2px 6px; border-radius:5px; font-size:11.5px; }
</style></head><body>
<header>
  <h1>Loki 外观套组画廊</h1>
  <span class="meta">__COUNT__ 套（★ = 作者推荐，默认已勾选）· 勾选后导出清单给 install.py · 静态预览，真实渲染看 previews/demo/demo.html</span>
  <input id="q" placeholder="搜索：名字 / id / 分组 / 契约钩子…">
  <button id="copy">复制 --only 清单</button>
  <button class="ghost" id="clear">清空勾选</button>
</header>
<main>
  <div class="filters" id="filters"></div>
  <div class="grid" id="grid"></div>
</main>
<footer>
  <span style="opacity:.6">Loki 外观套组工坊 · 作者 Loki</span>
  <span id="status">已选 0 套</span>
  <code id="cmd">--only —</code>
</footer>
<script>
const SETS = __DATA__;
const KEY = "loki-theme-kit:selected";
// 第一次打开：默认勾上作者推荐的那几套（★），之后以你自己的选择为准
const stored = localStorage.getItem(KEY);
let selected = new Set(JSON.parse(stored !== null ? stored : JSON.stringify(SETS.filter(s => s.recommended).map(s => s.id))));
let groupsOn = new Set(Object.keys(SETS.reduce((a,s)=>{a[s.group||""]=1;return a;},{})));

const GL = __GROUPS__;
function draw() {
  const q = (document.getElementById("q").value || "").toLowerCase();
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  let shown = 0;
  for (const s of SETS) {
    if (!groupsOn.has(s.group || "")) continue;
    const hay = (s.id + " " + s.label + " " + (s.group||"") + " " + (GL[s.group||""]||"")
                 + " " + s.hooks.join(" ") + " " + s.source_board).toLowerCase();
    if (q && !hay.includes(q)) continue;
    shown++;
    const el = document.createElement("div");
    el.className = "card" + (selected.has(s.id) ? " selected" : "");
    const c = s.colors;
    el.innerHTML = `
      <div class="swatch">
        <div style="background:${c.canvas}"></div>
        <div style="background:${c.surface}"></div>
        <div style="background:${c.sidebar}"></div>
        <div style="background:${c.text}"></div>
        <div style="background:${c.accent}"></div>
        <div style="background:${c.border}"></div>
      </div>
      <div class="body">
        <div class="label">${s.recommended ? "★ " : ""}${s.label}<small>${s.id}</small></div>
        <div class="row"><span>${GL[s.group||""] || s.group || "未分组"}</span><span>令牌 ${s.tokens}</span><span>结构规则 ${s.rules}</span><span>${s.lines} 行</span></div>
        <div class="hooks">契约钩子：${s.hooks.join(" ") || "（无，纯令牌套组）"}</div>
        <div class="row" style="opacity:.55">来源：${s.source_board || "未注明"}</div>
        ${s.deco.length ? `<div class="deco">装饰槽位 ${s.deco.join(" ")}（默认 none，可挂你自己的图）</div>` : ""}
        <div class="pick"><button data-pick="${s.id}">${selected.has(s.id) ? "已选 ✓" : "选这套"}</button></div>
        <details><summary>看这套的 CSS（${s.lines} 行）</summary><pre>${s.css.replace(/[<>&]/g, m=>({"<":"&lt;",">":"&gt;","&":"&amp;"}[m]))}</pre></details>
      </div>`;
    grid.appendChild(el);
  }
  if (!shown) grid.innerHTML = '<div style="opacity:.6">没有匹配的套组。</div>';
  const list = [...selected];
  document.getElementById("status").textContent = `已选 ${list.length} 套（显示 ${shown} 套）`;
  document.getElementById("cmd").textContent = list.length ? "--only " + list.join(",") : "--only —";
}
const filters = document.getElementById("filters");
for (const g of Object.keys(GL)) {
  const b = document.createElement("div");
  b.className = "chip"; b.dataset.on = "1"; b.textContent = `${GL[g]}（${SETS.filter(s=>(s.group||"")===g).length}）`;
  b.onclick = () => { if (groupsOn.has(g)) groupsOn.delete(g); else groupsOn.add(g); b.dataset.on = groupsOn.has(g) ? "1" : "0"; draw(); };
  filters.appendChild(b);
}
document.addEventListener("click", e => {
  const id = e.target?.dataset?.pick;
  if (!id) return;
  if (selected.has(id)) selected.delete(id); else selected.add(id);
  localStorage.setItem(KEY, JSON.stringify([...selected]));
  draw();
});
document.getElementById("q").oninput = draw;
document.getElementById("clear").onclick = () => { selected.clear(); localStorage.setItem(KEY, "[]"); draw(); };
document.getElementById("copy").onclick = async () => {
  const t = document.getElementById("cmd").textContent;
  try { await navigator.clipboard.writeText(t); document.getElementById("status").textContent = "已复制：" + t; }
  catch { document.getElementById("status").textContent = "复制失败，手动选中：" + t; }
};
draw();
</script></body></html>
"""


# 在线版（docs/index.html）比本地画廊页多出来的那一行
DOC_META = ('  <span class="meta">MIT · '
            '<a href="https://github.com/loki2046-mao/loki-theme-kit" style="color:#f0f0ea">GitHub 仓库</a> · '
            '<a href="https://github.com/loki2046-mao/loki-theme-kit#readme" style="color:#f0f0ea">怎么接入</a></span>\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default=str(SKILL / "sets"))
    ap.add_argument("--out", default=str(SKILL / "previews" / "gallery.html"))
    ap.add_argument("--docs", default=str(SKILL / "docs" / "index.html"),
                    help="同时写一份在线版（GitHub Pages，带仓库链接）")
    ap.add_argument("--no-docs", action="store_true", help="不写在线版")
    args = ap.parse_args()

    cards = build(Path(args.sets))
    groups = {}
    for c in cards:
        groups[c["group"]] = GROUP_LABELS.get(c["group"], c["group"] or "未分组")
    page = (PAGE
            .replace("__DATA__", json.dumps(cards, ensure_ascii=False))
            .replace("__GROUPS__", json.dumps(groups, ensure_ascii=False))
            .replace("__COUNT__", str(len(cards))))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"画廊已生成：{out}（{len(cards)} 套，{out.stat().st_size // 1024} KB，单文件自包含）")

    # 在线版跟画廊页同一份数据，只多一行仓库链接 —— 免得两边各改一次、改着改着就不一样了
    if not args.no_docs:
        docout = Path(args.docs)
        docout.parent.mkdir(parents=True, exist_ok=True)
        docout.write_text(page.replace("</header>", DOC_META + "</header>", 1), encoding="utf-8")
        (docout.parent / ".nojekyll").write_text("", encoding="utf-8")
        print(f"在线版已生成：{docout}（+ .nojekyll）")


if __name__ == "__main__":
    main()
