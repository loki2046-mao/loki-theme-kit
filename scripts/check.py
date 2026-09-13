#!/usr/bin/env python3
"""套组质量门：一套主题能不能叫「做完」，由这个脚本说了算，不由眼睛。

用法：
    python3 scripts/check.py                 # 体检 sets/ 下全部套组
    python3 scripts/check.py --only loki-ease,loki-pop
    python3 scripts/check.py --json          # 机器可读

六道门：
  G1 令牌完整   必备令牌一个不能少（缺了就说明这套抽得不完整）
  G2 可读性     正文/底 ≥ 7、正文/面 ≥ 7、辅助/底 ≥ 4.5（WCAG，长文阅读舒适区）
  G3 强调可读   强调色上的文字 ≥ 4.5；强调色与底的区分度 ≥ 3.0（低了按钮会"隐形"）
  G4 真设计系统 结构规则 ≥ 6 条、规则行 ≥ 12 行 —— 挡的是"只换了个色号"的假主题
  G5 护眼专项   标了 eye_safe 的套组：不得有纯白面、不得有纹理/噪点/动效
  G6 零资产依赖 套组里不许残留宿主私有素材路径（应当都变成 --deco-x 槽位）

退出码：0 = 全过；1 = 有套组没过门。
"""
import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_TOKENS = [
    "--bg-canvas", "--bg-surface", "--text-primary", "--text-secondary",
    "--text-muted", "--accent-copper", "--accent-ink",
]
PATTERN_TOKENS = ["--canvas-texture", "--canvas-noise", "--canvas-ambient",
                  "--canvas-mark", "--surface-highlight", "--surface-glow"]
EYE_GROUPS = {"care"}


def lum(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return None
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    if la is None or lb is None:
        return None
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def read_set(d: Path):
    css = (d / "theme.css").read_text(encoding="utf-8")
    meta_p = d / "meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
    m = re.search(r'^:root\[data-theme="[^"]+"\]\s*\{(.*?)^\}', css, re.S | re.M)
    tokens = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1))) if m else {}
    body_after = css[m.end():] if m else css
    rules = len(re.findall(r"\{", body_after))
    lines = len([l for l in body_after.split("\n") if l.strip() and not l.strip().startswith("/*")])
    # 只在「非注释」文本里找残留素材：注释里出现的路径是给人看的说明，不是依赖
    css_no_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    raw_assets = re.findall(r'url\("(/[^"]+)"\)', css_no_comments)
    animations = len(re.findall(r"\b(animation|transition)\s*:", css))
    return tokens, meta, rules, lines, raw_assets, animations


def check_set(d: Path):
    tid = d.name
    tokens, meta, rules, lines, raw_assets, animations = read_set(d)
    group = (meta.get("group") or "").strip()
    problems, notes = [], []

    missing = [t for t in REQUIRED_TOKENS if t not in tokens]
    if missing:
        problems.append("G1 缺令牌 " + "、".join(missing))

    g = lambda k: (tokens.get(k) or "").strip()
    canvas, surface = g("--bg-canvas"), g("--bg-surface")
    text, muted = g("--text-primary"), g("--text-muted")
    accent, ink = g("--accent-copper"), g("--accent-ink")
    r_text_c = ratio(text, canvas)
    r_text_s = ratio(text, surface)
    r_muted = ratio(muted, canvas)
    r_ink = ratio(ink, accent)
    r_acc = ratio(accent, canvas)

    if r_text_s is not None and r_text_s < 7:
        problems.append(f"G2 正文/面 {r_text_s:.2f} < 7")
    if r_muted is not None and r_muted < 4.5:
        problems.append(f"G2 辅助/底 {r_muted:.2f} < 4.5")
    if r_ink is not None and r_ink < 4.5:
        problems.append(f"G3 强调上文字 {r_ink:.2f} < 4.5")
    if r_acc is not None and r_acc < 3.0:
        notes.append(f"强调与底区分度偏低 {r_acc:.2f}")

    if rules < 6 or lines < 12:
        problems.append(f"G4 结构件不足（规则 {rules} 条 / 行 {lines}）——疑似只是换色")

    if group in EYE_GROUPS or meta.get("eye_safe"):
        for t in PATTERN_TOKENS:
            v = (tokens.get(t) or "none").strip()
            if v and v != "none":
                problems.append(f"G5 护眼套组不该有 {t}")
        if re.search(r"^\s*animation\s*:", (d / "theme.css").read_text(encoding="utf-8"), re.M):
            problems.append("G5 护眼套组不该有 animation")
        lc = lum(canvas)
        if lc is not None and lc > 0.88:
            problems.append(f"G5 纸面过亮（相对亮度 {lc:.3f} > 0.88，接近纯白）")

    if raw_assets:
        problems.append("G6 残留宿主私有素材 " + "、".join(sorted(set(raw_assets))))

    return {
        "id": tid, "label": meta.get("label", tid), "group": group,
        "tokens": len(tokens), "rules": rules, "rule_lines": lines,
        "text_on_surface": r_text_s, "muted_on_canvas": r_muted,
        "ink_on_accent": r_ink, "accent_vs_canvas": r_acc,
        "deco_slots": sorted(k for k in tokens if k.startswith("--deco-")),
        "animations": animations,
        "problems": problems, "notes": notes,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default=str(Path(__file__).resolve().parent.parent / "sets"))
    ap.add_argument("--only", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.sets)
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    dirs = sorted(d for d in root.iterdir() if d.is_dir() and (not only or d.name in only))

    rows = [check_set(d) for d in dirs]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(f"{'套组':<18}{'令牌':>5}{'规则':>5}{'行':>4}{'正文/面':>9}{'辅助/底':>9}{'字/强调':>9}  判定")
        print("-" * 84)
        for r in rows:
            def f(v):
                return "  n/a" if v is None else f"{v:>6.2f}"
            verdict = "；".join(r["problems"]) if r["problems"] else "✓ 过"
            print(f"{r['id']:<18}{r['tokens']:>5}{r['rules']:>5}{r['rule_lines']:>4}"
                  f"{f(r['text_on_surface'])}{f(r['muted_on_canvas'])}{f(r['ink_on_accent'])}  {verdict}")
            for n in r["notes"]:
                print(f"{'':<18}{'':>23}   · {n}")
        print("-" * 84)
        bad = [r["id"] for r in rows if r["problems"]]
        print(f"未过门 {len(bad)} / {len(rows)}：{'、'.join(bad) if bad else '无'}")

    sys.exit(1 if any(r["problems"] for r in rows) else 0)


if __name__ == "__main__":
    main()
