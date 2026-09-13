#!/usr/bin/env python3
"""把选中的套组装进宿主的 App，并可选生成「能直接抄」的切换器与一个可打开的演示页。

用法：
    python3 scripts/install.py --list
    python3 scripts/install.py --recommended --out ./my-themes      # 装推荐的那 10 套
    python3 scripts/install.py --all --out ./my-themes
    python3 scripts/install.py --only loki-ease,loki-pop --out ./my-themes
    python3 scripts/install.py --recommended --out ./my-themes --prefix th- --with-switcher --demo

产出（都在 --out 目录里，绝不碰宿主已有文件）：
    <id>.css            每套主题的 CSS
    index.css           @import 汇总，宿主只引这一个
    themes.js/.json     套组清单（id/名字/分组/主色），给切换器吃
    README.md           宿主接上要做的三件事 + 钩子清单
    --with-switcher     切换器组件（原生 JS / React TSX / CSS / 防闪白片段）
    --demo              参考宿主外壳 + demo.html（浏览器直接打开就能看效果）

安全检查：目标目录已有同名文件默认拒绝覆盖（--force 才覆盖）；只写自己的输出目录。
"""
import argparse
import pathlib
import subprocess
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
DEFAULT_SETS = SKILL / "sets"
TEMPLATES = SKILL / "templates"

GROUP_LABELS = {"care": "护眼阅读", "art": "艺术风格", "retro": "复古屏幕",
                "calm": "安静工作", "": "未分组"}
GROUP_ORDER = ["care", "art", "retro", "calm", ""]


def apply_prefix(css: str, prefix: str) -> str:
    """只改契约类名 .loki-xxx → .<prefix>xxx；data-theme 的 id 不动（那是套组名）。"""
    if not prefix or prefix == "loki-":
        return css
    return re.sub(r"\.loki-([a-z0-9-]+)", lambda m: f".{prefix}{m.group(1)}", css)


def write(path: Path, text: str, force: bool, report: dict):
    if path.exists() and not force:
        report["skipped"].append(path.name)
        return False
    path.write_text(text, encoding="utf-8")
    report["written"].append(path.name)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default=str(DEFAULT_SETS))
    ap.add_argument("--out", default="./loki-themes")
    ap.add_argument("--only", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--recommended", action="store_true", help="只装标了 recommended 的那几套")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--prefix", default="loki-", help="契约类名前缀，默认 loki-（如 th- → .th-surface）")
    ap.add_argument("--with-switcher", action="store_true")
    ap.add_argument("--demo", action="store_true", help="生成参考宿主 + demo.html")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    sets_dir = Path(args.sets)
    dirs = {d.name: d for d in sets_dir.iterdir() if d.is_dir()}
    index = json.loads((sets_dir / "index.json").read_text(encoding="utf-8")) if (sets_dir / "index.json").exists() else []
    info = {r["id"]: r for r in index}

    if args.list:
        for r in index:
            star = "★" if r.get("recommended") else " "
            print(f"{star} {r['id']:<18}{r.get('label', ''):<12}{GROUP_LABELS.get(r.get('group', ''), ''):<10}"
                  f"令牌 {r['tokens']:>3} · 规则 {r['rules']:>2} · {r['rule_lines']:>3} 行"
                  f"{'  [装饰槽位 ' + str(len(r['deco_slots'])) + ']' if r.get('deco_slots') else ''}")
        print("\n★ = 推荐（领地不重叠，先看这几套）；全部 35 套用 --all 装")
        return 0

    if args.all:
        chosen = list(dirs)
    elif args.recommended:
        chosen = [r["id"] for r in index if r.get("recommended")]
    else:
        chosen = [x.strip() for x in args.only.split(",") if x.strip()]
    if not chosen:
        print("没指定套组。用 --list 看清单，然后 --all / --recommended / --only a,b,c。", file=sys.stderr)
        return 2

    unknown = [c for c in chosen if c not in dirs]
    if unknown:
        print(f"不认识的套组：{'、'.join(unknown)}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {"written": [], "skipped": []}

    for cid in chosen:
        css = (dirs[cid] / "theme.css").read_text(encoding="utf-8")
        write(out / f"{cid}.css", apply_prefix(css, args.prefix), args.force, report)

    installed = [c for c in chosen if (out / f"{c}.css").exists()]
    by_group: dict = {}
    for cid in installed:
        g = info.get(cid, {}).get("group", "")
        by_group.setdefault(g, []).append(cid)

    lines = ["/* 外观套组入口 —— 由 loki-theme-kit/scripts/install.py 生成。",
             "   在你的全局 CSS 里 @import 这一个文件就够了。 */", ""]
    for g in GROUP_ORDER:
        if g not in by_group:
            continue
        lines.append(f"/* --- {GROUP_LABELS.get(g, g)} --- */")
        for cid in by_group[g]:
            lines.append(f'@import "./{cid}.css";')
        lines.append("")
    write(out / "index.css", "\n".join(lines), args.force, report)

    theme_list = [{
        "id": cid,
        "label": info.get(cid, {}).get("label", cid),
        "group": info.get(cid, {}).get("group", ""),
        "accent": info.get(cid, {}).get("accent", ""),
        "surface": info.get(cid, {}).get("surface", ""),
    } for cid in installed]
    write(out / "themes.json", json.dumps(theme_list, ensure_ascii=False, indent=2) + "\n", args.force, report)
    first = theme_list[0]["id"] if theme_list else "loki-ease"

    write(out / "themes.js",
          "// 套组清单：给切换器吃。装完新套组重跑一次 install.py 即可。\n"
          f"export const THEMES = {json.dumps(theme_list, ensure_ascii=False, indent=2)};\n\n"
          f"export const GROUP_LABELS = {json.dumps(GROUP_LABELS, ensure_ascii=False, indent=2)};\n",
          args.force, report)

    if args.with_switcher or args.demo:
        for name in ["theme-switcher.js", "theme-switcher.tsx", "theme-switcher.css",
                     "theme-switcher-flash-guard.html"]:
            write(out / name, (TEMPLATES / name).read_text(encoding="utf-8"), args.force, report)

    if args.demo:
        write(out / "host-base.css", (TEMPLATES / "host-base.css").read_text(encoding="utf-8"), args.force, report)
        switcher_js = (TEMPLATES / "theme-switcher.js").read_text(encoding="utf-8")
        switcher_js = re.sub(r"^export ", "", switcher_js, flags=re.M)
        demo = (TEMPLATES / "host-demo.html").read_text(encoding="utf-8")
        demo = (demo.replace("__THEMES__", json.dumps(theme_list, ensure_ascii=False))
                    .replace("__GROUP_LABELS__", json.dumps(GROUP_LABELS, ensure_ascii=False))
                    .replace("__SWITCHER_JS__", switcher_js)
                    .replace('data-theme="loki-ease"', f'data-theme="{first}"')
                    .replace('|| "loki-ease"', f'|| "{first}"'))
        write(out / "demo.html", demo, args.force, report)

    hooks = sorted({h for cid in installed for h in info.get(cid, {}).get("host_hooks", [])})
    deco = sorted({d for cid in installed for d in info.get(cid, {}).get("deco_slots", [])})
    readme = f"""# 已装套组：{len(installed)} 套（契约前缀 `{args.prefix}`）

> 来自 **Loki 外观套组工坊（loki-theme-kit）** —— 作者 Loki · 可自由使用与改造。

## 你需要做的三件事

1. 引样式（在你的全局 CSS 或入口里加一行）：

   ```css
   @import "./loki-themes/index.css";   /* 路径按你实际放置位置改 */
   ```

2. 在页面根元素上给主题名：`<html data-theme="{first}">`。切换就是改这个属性，
   存哪都行（localStorage / 用户设置 / Cookie）；可选主题的清单看 `themes.json`。

3. 给你 App 里的元素挂契约类名。本次装进来的套组会用到：

{chr(10).join(f"   - `.{args.prefix}{h}`" for h in hooks) if hooks else "   （本批套组只用令牌，不挑钩子）"}

完整契约表见 `references/host-contract.md`。**少挂哪几个，就少几处主题效果，不会报错。**

## 切换器（可以直接抄）

{"""已一并装进本目录：

- `theme-switcher.js`   原生 JS（造 DOM，无依赖）
- `theme-switcher.tsx`  React / Next.js 版
- `theme-switcher.css`  切换器样式（只用主题令牌，自己也会跟着变）
- `theme-switcher-flash-guard.html`  放在 `<head>` 最前面的防闪白片段

两个坑已经在文件注释里写明白了：localStorage 不能在 useState 初值里读（hydration
mismatch）；收起的面板要 `display:none`，否则它仍然占布局、会把侧栏挤出去。""" if args.with_switcher else "这次没生成。加 `--with-switcher` 会把切换器组件一起装进来。"}

## 演示页

{"""`demo.html` 是一个**参考宿主**：只用契约类名 + 令牌搭出侧栏/卡片/按钮/输入区，
浏览器直接打开就能切主题看效果（`host-base.css` 就是"宿主那一半"的最小实现，
可以照着搬进你自己的样式）。""" if args.demo else "这次没生成。加 `--demo` 会生成参考宿主 + demo.html。"}

## 关于图片和 IP

套组**零图片依赖**：{("这些槽位：" + "、".join(deco) + " 默认 `none`，想挂自己的装饰就覆盖它。") if deco else "本批套组没有任何图片引用。"}

```css
:root[data-theme="loki-8bit"] {{ --deco-a: url("/your/cloud.png"); }}
```

**套组不含任何人的 IP 形象。** 你自己的品牌头像放你自己的位置，别指望套组带它来。
"""
    write(out / "README.md", readme, args.force, report)

    print(f"装了 {len(installed)} 套 → {out}/")
    print(f"  写入 {len(report['written'])} 个文件" + (f"（跳过已存在 {len(report['skipped'])} 个，要覆盖加 --force）" if report["skipped"] else ""))
    if args.demo:
        print(f"  演示页：open {out}/demo.html")
    print("\n还需要你手动做的三件事（脚本不替你做）：")
    print("  1) 在全局 CSS 里 @import 生成的 index.css")
    print(f'  2) 在 <html> 上放 data-theme="{first}"')
    print("  3) 给页面元素挂契约类名（清单见生成的 README.md）")
    _show_welcome(out)
    return 0


def _show_welcome(out_dir):
    """深度接入也把"装完提示页"弹一次 —— 用户不该为了知道还能要什么去翻文档。"""
    page = pathlib.Path(out_dir) / "给你的用户.html"
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("welcome.py")),
                    "--out", str(page)], capture_output=True, text=True)
    if page.exists():
        subprocess.Popen(["open", str(page)])
        print(f"装完提示页（已打开）：{page}")


if __name__ == "__main__":
    sys.exit(main())
