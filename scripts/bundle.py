#!/usr/bin/env python3
"""打一个「单文件接入包」：一行 <script>，装完就有全部套组 + 悬浮切换器。

    python3 scripts/bundle.py --recommended --out ./my-site/themes
    python3 scripts/bundle.py --all --out ./my-site/themes
    python3 scripts/bundle.py --only loki-desk,loki-ease --out ./my-site/themes

产出（都在 --out 目录里）：
    loki-themes.js    一行就能用：<script src="loki-themes.js"></script>
    loki-themes.css   同一份样式，喜欢 <link> 的用这个（那样要自己写切换器）
    index.html        一个最小示例页，浏览器打开就能看效果
    README.md         怎么用、参数、边界、怎么改
    给你的用户.md/.html  装完要交给用户看的那一页（想要什么就说哪句话）

和 install.py 的区别：
    install.py  = 深度接入：把每套 CSS 分开给你，你自己 @import、自己接切换器、
                  自己给元素贴契约类名 —— 适合正式项目，控制力最强。
    bundle.py   = 一行接入：脚本自己注入样式、自己上主题、自带悬浮切换器 ——
                  适合"我现在就想看看它长什么样"或者轻量项目。
"""
import argparse
import pathlib
import re
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SETS = SKILL / "sets"
TEMPLATES = SKILL / "templates"

GROUP_LABELS = {"care": "护眼阅读", "art": "艺术风格", "retro": "复古屏幕",
                "calm": "安静工作", "": "未分组"}


def minify(css: str) -> str:
    """去掉注释、压缩空白。保守做法：只清注释 + 折叠空白 + 收紧 { } ; 周围的空格，
    避免动 url()/data-URI 里的内容。35 套原样约 360KB，压完约 150KB。"""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};])\s*", r"\1", css)
    return css.strip()


SKILL = pathlib.Path(__file__).resolve().parent.parent


def _user_facing_block(count=None):
    """从 references/after-install.md 里抽「给用户的那段话」（单一来源）。

    文档里按 35 套写的，这里按实际套数改掉 —— 生成物上的数字必须跟真的一致，
    不然用户数一数发现对不上，后面说什么都不信了。"""
    f = SKILL / "references" / "after-install.md"
    if not f.exists():
        return "（references/after-install.md 不在了）"
    text = f.read_text(encoding="utf-8")
    m = re.search(r"<!-- USER-FACING-START -->(.*?)<!-- USER-FACING-END -->", text, re.S)
    body = (m.group(1).strip() if m else text.strip())
    if count:
        body = (body.replace("现在有 35 套外观主题", f"现在有 {count} 套外观主题")
                    .replace("30 多套随便切", f"{count} 套随便切")
                    .replace("35 套全是纯 CSS", f"{count} 套全是纯 CSS"))
    return body + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./loki-themes")
    ap.add_argument("--only", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--recommended", action="store_true")
    ap.add_argument("--theme", default="", help="首次打开用哪套（默认推荐里的第一套）")
    ap.add_argument("--name", default="loki-themes", help="产物文件名（不含扩展名）")
    ap.add_argument("--keep-comments", action="store_true", help="不压缩，保留注释（体积大约 2 倍）")
    ap.add_argument("--no-switcher", action="store_true", help="不内置悬浮切换器（只上主题）")
    ap.add_argument("--adapter", default="", help="宿主适配器（adapters/<名字>/adapter.json），如 cola")
    ap.add_argument("--quiet", action="store_true", help="只报错不打进度（给 profile.py 这类调用方用）")
    args = ap.parse_args()

    index = json.loads((SETS / "index.json").read_text(encoding="utf-8"))
    info = {r["id"]: r for r in index}

    if args.all:
        chosen = [r["id"] for r in index]
    elif args.only:
        chosen = [x.strip() for x in args.only.split(",") if x.strip()]
    else:
        chosen = [r["id"] for r in index if r.get("recommended")] or [r["id"] for r in index]
    unknown = [c for c in chosen if c not in info]
    if unknown:
        print(f"不认识的套组：{'、'.join(unknown)}", file=sys.stderr)
        return 2

    # 三层：通用元素 → 契约钩子的基础长相 → 各套主题（主题只负责覆盖，不负责排版）
    skip_generic = False
    if args.adapter:
        _sp = SKILL / "adapters" / args.adapter / "adapter.json"
        if _sp.exists():
            skip_generic = bool(json.loads(_sp.read_text(encoding="utf-8")).get("skip_generic_layer"))
    parts = []
    if not skip_generic:
        # 通用元素层给「没有设计系统的普通页面」用；宿主自带设计系统时会打架，按适配器开关跳过
        parts.append((TEMPLATES / "dropin-base.css").read_text(encoding="utf-8"))
    parts += [(TEMPLATES / "hooks-base.css").read_text(encoding="utf-8"),
              (TEMPLATES / "dropin-ui.css").read_text(encoding="utf-8")]
    also = []
    if args.adapter:
        _spec_path = SKILL / "adapters" / args.adapter / "adapter.json"
        if _spec_path.exists():
            also = json.loads(_spec_path.read_text(encoding="utf-8")).get("also_match_selectors", [])
    for cid in chosen:
        css_text = (SETS / cid / "theme.css").read_text(encoding="utf-8")
        if also:
            # 套组的令牌定义在 :root[data-theme="x"] 上；宿主用的是别的属性（Cola: data-cola-skin），
            # 不改写的话套组令牌根本不会被定义，适配层读到的是空值。
            extra = ", ".join(sel.replace("__ID__", cid) for sel in also)
            css_text = css_text.replace(f':root[data-theme="{cid}"]', f':root[data-theme="{cid}"], {extra}')
        parts.append(f"/* ==== {info[cid].get('label', cid)}（{cid}）==== */\n" + css_text)
    # ---- 宿主适配层：把我们的令牌接到宿主的令牌上（适配器见 adapters/） ----
    host_profile = None
    if args.adapter:
        adir = SKILL / "adapters" / args.adapter
        spec = json.loads((adir / "adapter.json").read_text(encoding="utf-8"))
        imp = " !important" if spec.get("important") else ""
        blocks = []
        for cid in chosen:
            sels = ", ".join(sel.replace("__ID__", cid) for sel in spec.get("extra_selectors", []))
            decls = []
            for target, source in spec.get("token_map", {}).items():
                val = f"var({source})" if source.startswith("--") else source
                decls.append(f"  {target}: {val}{imp};")
            blocks.append(f"{sels} {{\n" + "\n".join(decls) + "\n}")
        extra = (adir / "extra.css")
        parts.append(f"/* ==== 宿主适配层：{spec.get('label', args.adapter)} ==== */\n"
                     + "\n".join(blocks) + ("\n" + extra.read_text(encoding="utf-8") if extra.exists() else ""))
        # 深色/浅色：宿主大多需要同步自己的 class（Cola 用 .dark / .light）
        def lum(hexv):
            h = (hexv or "").strip().lstrip("#")
            if len(h) == 3: h = "".join(c * 2 for c in h)
            if len(h) != 6: return None
            try: r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
            except ValueError: return None
            f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
        dark = []
        for cid in chosen:
            # 令牌块可能有多段（后面的覆盖前面的），取最后一个才算数
            found = re.findall(r'--bg-canvas\s*:\s*([^;]+);', (SETS / cid / "theme.css").read_text(encoding="utf-8"))
            L = lum(found[-1]) if found else None
            if L is not None and L < 0.3:
                dark.append(cid)
        inst = spec.get("install", {})
        host_profile = {"label": spec.get("label", args.adapter), "darkThemes": dark,
                        "attr": inst.get("attr", ""), "storageKey": inst.get("storageKey", ""),
                        "switcher": inst.get("switcher") or None,
                        "yieldAttr": inst.get("yield_attr", ""), "schemeClass": bool(dark),
                        "origModeAttr": inst.get("orig_mode_attr", "")}

    # 适配层拼好之后才压缩成最终 CSS
    raw_css = "\n".join(parts)
    css = raw_css if args.keep_comments else minify(raw_css)

    themes = [{"id": cid, "label": info[cid].get("label", cid), "group": info[cid].get("group", ""),
               "accent": info[cid].get("accent", ""), "surface": info[cid].get("surface", "")}
              for cid in chosen]
    default = args.theme or next((t["id"] for t in themes if info[t["id"]].get("recommended")), themes[0]["id"])

    js = (TEMPLATES / "dropin.js.tmpl").read_text(encoding="utf-8")
    js = (js.replace("__CSS__", json.dumps(css, ensure_ascii=False))
            .replace("__THEMES__", json.dumps(themes, ensure_ascii=False))
            .replace("__GROUP_LABELS__", json.dumps(GROUP_LABELS, ensure_ascii=False))
            .replace("__DEFAULT__", json.dumps(default, ensure_ascii=False)))

    js = js.replace("__HOST__", json.dumps(host_profile, ensure_ascii=False) if host_profile else "null")

    if args.no_switcher:
        js = js.replace("  var root = document.documentElement;",
                        '  opt.switcher = "off";   // 生成时指定：不带悬浮切换器\n  var root = document.documentElement;', 1)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.name}.js").write_text(js, encoding="utf-8")
    (out / f"{args.name}.css").write_text(
        f"/* Loki 外观套组工坊 —— {len(chosen)} 套主题\n"
        f"   用 <link> 引这个的话，主题切换要你自己写：改 <html data-theme=\"…\">。 */\n" + css,
        encoding="utf-8")
    (out / "index.html").write_text(f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>接入包示例</title>
<script src="./{args.name}.js"></script>
</head>
<body>
<h1>接入包示例页</h1>
<p>这一页除了下面那几行，没有任何样式和脚本。它的外观全部来自 <code>{args.name}.js</code>。</p>
<p>右下角点「外观」，可以切 {len(chosen)} 套主题。你的选择会被记住。</p>
<p><a href="#">这是一个链接</a> · <button>一个按钮</button> <button data-variant="secondary">次按钮</button></p>
<p><input placeholder="一个输入框"></p>
<blockquote>把 <code>&lt;script src="{args.name}.js"&gt;&lt;/script&gt;</code> 加进你自己的页面，就完成了。</blockquote>
</body>
</html>
""", encoding="utf-8")

    # ---- 生成给用户的两份说明 ----
    # 内容来自 references/after-install.md 的 USER-FACING 区块 —— 单一来源，
    # 改那份文档，生成物跟着变（不然两处迟早说不一样的话）。
    welcome = _user_facing_block(len(chosen))
    (out / "给你的用户.md").write_text(welcome, encoding="utf-8")
    # 同一份内容的网页版：装完要**自动弹出来**给用户看的，就是这一页
    import welcome as _welcome
    (out / "给你的用户.html").write_text(_welcome.render(len(chosen)), encoding="utf-8")

    (out / "README.md").write_text(f"""# {len(chosen)} 套外观主题（单文件接入包）

> 来自 **Loki 外观套组工坊（loki-theme-kit）** —— 作者 Loki · 可自由使用与改造。

## 怎么用：一行

把这一行加进你页面的 `<head>`：

```html
<script src="./{args.name}.js"></script>
```

完。你的页面立刻有外观主题，右下角会出现一个「外观」按钮，点开可以切
{len(chosen)} 套，选择会被记住（换浏览器/清缓存才会重置）。

## 可选的参数（都写在那个 script 标签上）

```html
<!-- 首次打开用某套；之后以用户的选择为准 -->
<script src="./{args.name}.js" data-theme="{default}"></script>

<!-- 不显示悬浮按钮，只上主题（那就要自己切 data-theme） -->
<script src="./{args.name}.js" data-switcher="off"></script>

<!-- 自动给常见元素贴契约类名（默认关；开了效果更足，但会往你的 DOM 加 class） -->
<script src="./{args.name}.js" data-autotag="on"></script>
```

## 它做了什么 / 没做什么

**做**：注入一份样式表（页面底色／文字／标题字体／链接／按钮／输入框／选中色／滚动条，
以及你选的每一套主题）；把主题名设到 `<html>`（或宿主约定的属性上）；放一个切换入口；
记住选择。

**没做**：不改你的布局（不动 margin/padding/宽高），不碰你的品牌形象和头像，
不删改你的任何文件。**不想要了就删掉那一行**——一切都回原样。

## 这个项目里怎么改

- 换/加/减套组：改 `sets/` 后用 `scripts/bundle.py` 重新打包（`--only a,b,c` 只打这几套）
- 想让卡片、侧栏、气泡这些**具体部件**也跟着变：那要给它挂契约钩子 + 逐条实测，
  见 `references/host-binding.md`（一句话：把宿主的元素认领成 `.loki-*` 钩子）
- 想让这套外观**重启/升级之后还在**、或者**换台机器也在**：见 `references/after-install.md`

## 包含的套组

{chr(10).join(f"- {t['label']}（{t['id']}）" for t in themes)}
""", encoding="utf-8")

    layers = ("" if skip_generic else "通用元素基础层 + ") + "契约钩子基础层 + 你选的每一套主题"
    if host_profile:
        layers += f" + 宿主适配层（{host_profile['label']}，{len(host_profile['darkThemes'])} 套深色）"
    if args.quiet:
        return 0
    print(f"  分层：{layers}")
    js_kb = (out / f"{args.name}.js").stat().st_size // 1024
    css_kb = (out / f"{args.name}.css").stat().st_size // 1024
    print(f"接入包已生成：{out}/")
    print(f"  {args.name}.js    {js_kb} KB（单文件，含 {len(chosen)} 套主题 + 悬浮切换器）")
    print(f"  {args.name}.css   {css_kb} KB（只要样式的话）")
    print("  index.html      浏览器打开就能看效果")
    print("  README.md       怎么用 + 怎么改 + 边界")
    print("  给你的用户.md/.html  装完要交给用户看的那一页（能力清单：想要什么就说哪句话）\n"
          "                     装完自动弹出来的就是这个 .html（auto.py 会打开它）")
    print(f"\n用法就一行：<script src=\"./{args.name}.js\"></script>")
    print(f"默认套组：{default}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

    raw_css = "\n".join(parts)
    css = raw_css if args.keep_comments else minify(raw_css)

    themes = [{"id": cid, "label": info[cid].get("label", cid), "group": info[cid].get("group", ""),
               "accent": info[cid].get("accent", ""), "surface": info[cid].get("surface", "")}
              for cid in chosen]
