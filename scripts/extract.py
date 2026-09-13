#!/usr/bin/env python3
"""从一份「按主题 id 混在一起」的宿主 CSS 里，抽出每套主题的套组文件。

用法：
    python3 scripts/extract.py --css <宿主.css> --switcher <切换器.tsx> --out sets/
    python3 scripts/extract.py --css app/globals.css --switcher app/components/ThemeSwitcher.tsx

产出：
    <out>/<id>/theme.css   该套主题真正需要的 CSS（令牌块 + 该套专属规则）
    <out>/<id>/meta.json   身份卡（名字/分组/主色/结构件配方线索/装饰槽位）
    <out>/index.json       全部套组的索引（画廊与安装器读它）

分类规则：
    :root[data-theme="X"] { --a: ... }         → 令牌块
    :root[data-theme="X"] .sel { ... }         → 该套专属规则（选择器列表里其它主题摘掉）
    :root[data-theme] .sel { ... }             → 共享基线，不属于任何单套，不进套组
    其它                                        → 宿主自己的样式，不碰

装饰槽位：规则里指向宿主私有素材的 url("/...")，会被改写成 var(--deco-x)，
默认 none，原路径记进 meta.json。这样套组本身零资产依赖，别人的 App 不会
因为缺图而破版；想挂自己装饰的人覆盖 --deco-x 就行。
"""
import argparse
import json
import re
from pathlib import Path

DEFAULT_CSS = "app/globals.css"
DEFAULT_SWITCHER = "app/components/ThemeSwitcher.tsx"


# ---------------------------------------------------------------- CSS 扫描

def parse(text, at=None):
    """扫一遍 CSS，返回 (selector, body_text, at_wrapper)；支持 @media 嵌套。

    扫描时跳过注释与字符串本体（只影响扫描位置；body 走原文切片，内容不丢）。
    选择器前挂着的解释性注释会被摘掉——那是原作者的文档，不参与分类。
    """
    out = []
    at = at or []
    i, n = 0, len(text)
    sel_start = 0
    body_start = None
    depth = 0
    while i < n:
        c = text[i]
        if c == "/" and text[i + 1:i + 2] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "\"'":
            q = c
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    break
                j += 1
            i = j + 1
            continue
        if c == "{":
            if depth == 0:
                sel = re.sub(r"/\*.*?\*/", "", text[sel_start:i], flags=re.S).strip()
                body_start = i + 1
            depth += 1
            i += 1
            continue
        if c == "}":
            depth -= 1
            if depth == 0:
                body = text[body_start:i]
                if sel.startswith("@"):
                    out.extend(parse(body, at + [sel]))
                else:
                    out.append((sel, body, at[-1] if at else None))
                i += 1
                sel_start = i
                continue
            i += 1
            continue
        i += 1
    return out


def split_selector_list(sel: str):
    parts, cur, depth, quote = [], "", 0, None
    for ch in sel:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            cur += ch
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def theme_of(sel: str):
    m = re.match(r'^:root\[data-theme="([^"]+)"\](.*)$', sel.strip())
    return (m.group(1), m.group(2)) if m else (None, None)


# ---------------------------------------------------------------- 装饰槽位

SLOT_LETTERS = "abcdefgh"


def to_slots(body: str, taken: dict):
    """把宿主私有素材的 url("/...") 换成 var(--deco-x)，返回 (新 body, 本次用到的槽位)。"""
    found = []

    def repl(m):
        path = m.group(1)
        key = (path,)
        if key not in taken:
            letter = SLOT_LETTERS[len(taken)] if len(taken) < len(SLOT_LETTERS) else "z"
            taken[key] = letter
        return f"var(--deco-{taken[key]})"

    new_body = re.sub(r'url\("(/[^"]+)"\)', repl, body)
    found = [p for (p,) in taken]
    return new_body, found


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--css", default=DEFAULT_CSS)
    ap.add_argument("--switcher", default=DEFAULT_SWITCHER)
    ap.add_argument("--out", default="sets")
    ap.add_argument("--only", default="", help="只抽这些 id（逗号分隔）")
    args = ap.parse_args()

    css_path = Path(args.css)
    rules = parse(css_path.read_text(encoding="utf-8"))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    ids = []
    sw_meta = {}
    sw = Path(args.switcher)
    if sw.exists():
        sw_text = sw.read_text(encoding="utf-8")
        ids = re.findall(r'id:\s*"([^"]+)"', sw_text)
        # 顺带把名字/分组/主色读出来（切换器里有就带，没有就留空）
        for m in re.finditer(
            r'\{[^{}]*?id:\s*"([^"]+)",\s*label:\s*"([^"]+)",\s*accent:\s*"([^"]+)",'
            r'\s*surface:\s*"([^"]+)"(?:,\s*group:\s*"([^"]+)")?', sw_text, re.S):
            sw_meta[m.group(1)] = {"label": m.group(2), "accent": m.group(3),
                                   "surface": m.group(4), "group": m.group(5) or ""}
    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        ids = [i for i in ids if i in want]
    if not ids:
        # 没有切换器就退回「CSS 里出现过的所有 data-theme」
        seen = []
        for sel, _, _ in rules:
            for s in split_selector_list(sel):
                t = theme_of(s)[0]
                if t and t not in seen:
                    seen.append(t)
        ids = seen

    index = []
    for tid in ids:
        tokens, own = [], []
        taken: dict = {}
        for sel, body, at in rules:
            sels = split_selector_list(sel)
            hits = [s for s in sels if theme_of(s)[0] == tid]
            if not hits:
                continue
            bare = len(sels) == 1 and theme_of(sels[0])[1].strip() == ""
            if bare:
                tokens.append((sel, body, at))
            else:
                own.append((", ".join(hits), body, at))

        token_body = "".join(b for _, b, _ in tokens)
        token_props = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", token_body))

        # 专属规则里的装饰素材 → 槽位变量
        own_slotted = []
        for sel, body, at in own:
            new_body, _ = to_slots(body, taken)
            own_slotted.append((sel, new_body, at))
        slots = sorted(f"--deco-{v}" for v in taken.values())  # 只留槽位名，不留原作者素材路径

        slot_decls = ""
        for var, path in sorted(slots.items()):
            # 注意：不把原素材路径写进产物——套组发出去不该带任何人的私有素材线索。
            slot_decls += (
                "  /* 装饰槽位：原来这里挂着一件小道具（位置与尺寸已定，图片不随包分发）。\n"
                f"     想挂自己的图就覆盖它，例如 {var}: url(\"/your/icon.png\"); */\n"
                f"  {var}: none;\n"
            )

        d = out_dir / tid
        d.mkdir(parents=True, exist_ok=True)

        def render(entries):
            chunks = []
            for sel, body, at in entries:
                block = f"{sel} {{{body}}}"
                if at:
                    block = f"{at} {{\n{block}\n}}"
                chunks.append(block)
            return "\n".join(chunks)

        (d / "theme.css").write_text(
            f"/* {tid} —— 由 scripts/extract.py 从 {css_path} 抽出，未人工整理。\n"
            f"   契约见 references/host-contract.md；选择器前缀可按宿主改写。 */\n"
            f':root[data-theme="{tid}"] {{\n'
            f"{token_body}"
            f"{slot_decls}}}\n\n"
            f"{render(own_slotted)}\n",
            encoding="utf-8",
        )

        sw_i = sw_meta.get(tid, {})
        hooks = sorted({
            cls for sel, _, _ in own_slotted
            for cls in re.findall(r'\.([a-z][a-z0-9-]*)', sel)
        })
        meta = {
            "id": tid,
            "label": sw_i.get("label", tid),
            "group": sw_i.get("group", ""),
            "accent": sw_i.get("accent", ""),
            "surface": sw_i.get("surface", ""),
            "tokens": len(token_props),
            "token_names": sorted(token_props),
            "rules": len(own_slotted),
            "rule_lines": sum(len([l for l in b.split("\n") if l.strip()]) for _, b, _ in own_slotted),
            "host_hooks": hooks,
            "deco_slots": slots,
            "deco_note": "槽位只定义位置与尺寸，图片由使用者自己提供" if slots else "",
        }
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index.append({"id": tid, "label": meta["label"], "group": meta["group"],
                      "accent": meta["accent"], "surface": meta["surface"],
                      "tokens": meta["tokens"], "rules": meta["rules"],
                      "rule_lines": meta["rule_lines"], "host_hooks": hooks,
                      "deco_slots": sorted(slots)})

    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"抽出 {len(index)} 套 → {out_dir}/")
    print(f"{'id':<18}{'令牌':>5}{'规则':>5}{'规则行':>7}  装饰槽位")
    for r in index:
        print(f"{r['id']:<18}{r['tokens']:>5}{r['rules']:>5}{r['rule_lines']:>7}  {'、'.join(r['deco_slots']) or '—'}")


if __name__ == "__main__":
    main()
