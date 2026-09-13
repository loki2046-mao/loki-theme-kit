#!/usr/bin/env python3
"""无人值守接入：给一个项目目录，自动把外观套组接上去，不需要人回答任何问题。

给 Agent 用的主入口。人也可以用，但它假设"你只想让它装好"。

    python3 scripts/auto.py --project /path/to/app
    python3 scripts/auto.py --project ./my-site --sets all
    python3 scripts/auto.py --project ./my-site --dry-run      # 只看它会改什么，不动文件

它会：
  1. 打一个自包含接入包（默认 35 套全带）到项目的 public/ 或项目根；
  2. 认出宿主类型（Next App Router / Vite / 纯 HTML / 静态目录），找到要接线的那一个文件；
  3. 把 <script src="…loki-themes.js"></script> 插到正确位置（幂等：已经接过就不重复插）；
  4. 改任何文件之前先留一份 .loki-bak 备份；
  5. 回读验证：包在不在、里面有几套、script 标签是不是真的进了文件。

退出码 0 = 接好了；1 = 有需要人看一眼的地方（打印出来）。
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
MARKER = "loki-themes.js"


def find_entry_candidates(project: Path):
    """返回 [(文件, 宿主类型, 插入锚点)]，按可靠性排序。"""
    out = []
    for layout in ["app/layout.tsx", "src/app/layout.tsx", "app/layout.jsx", "src/app/layout.jsx",
                   "app/layout.js", "src/app/layout.js"]:
        p = project / layout
        if p.exists():
            out.append((p, "next-app-router", "body"))
    for html in ["index.html", "public/index.html", "src/index.html", "app/index.html"]:
        p = project / html
        if p.exists():
            out.append((p, "html-head", "head"))
    # 兜底：项目根下任意一个含 <head> 的 html（挑层级最浅的）
    if not out:
        cands = sorted(project.glob("*.html")) or sorted(project.glob("**/*.html"))[:3]
        for p in cands:
            if "<head" in p.read_text(encoding="utf-8", errors="ignore"):
                out.append((p, "html-head", "head"))
    return out


def build_bundle(project: Path, sets_arg: str, dry: bool, no_switcher: bool = False) -> tuple:
    """选一个合适的落点并生成接入包。返回 (目标目录, URL 前缀, 日志行)。"""
    public = None
    for cand in ["public", "static", "assets"]:
        if (project / cand).is_dir():
            public = project / cand
            break
    if public is not None:
        dest = public / "loki-themes"
        url = "/loki-themes/"
    else:
        dest = project / "loki-themes"
        url = "./loki-themes/"
    if dry:
        return dest, url, f"[dry-run] 会把接入包写到 {dest}/loki-themes.js（URL 前缀 {url}）"
    cmd = [sys.executable, str(HERE / "bundle.py"), "--out", str(dest)]
    if sets_arg == "all":
        cmd.append("--all")
    elif sets_arg == "recommended":
        cmd.append("--recommended")
    else:
        cmd += ["--only", sets_arg]
    if no_switcher:
        cmd.append("--no-switcher")
    rc = subprocess.run(cmd, capture_output=True, text=True)
    if rc.returncode != 0:
        raise RuntimeError(rc.stderr or rc.stdout)
    return dest, url, rc.stdout.strip().splitlines()[0]


def inject(path: Path, url: str, anchor: str, dry: bool):
    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        return "already", src, src
    tag = f'<script src="{url}{MARKER}"></script>'
    if anchor == "body":
        m = re.search(r"<body[^>]*>", src)
        if not m:
            return "no-anchor", src, src
        new = src[:m.end()] + "\n        {/* Loki 外观套组：一行接入，见 loki-theme-kit */}\n        " + tag + src[m.end():]
    else:
        m = re.search(r"</head>", src, re.I)
        if not m:
            return "no-anchor", src, src
        new = src[:m.start()] + f"\n  {tag}\n" + src[m.start():]
    if dry:
        return "would", src, new
    bak = path.with_suffix(path.suffix + f".loki-bak-{int(time.time())}")
    shutil.copy2(path, bak)
    path.write_text(new, encoding="utf-8")
    return "done", src, new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="目标项目目录")
    ap.add_argument("--sets", default="all", help="all（默认）/ recommended / 逗号分隔的套组 id")
    ap.add_argument("--no-switcher", action="store_true", help="不要悬浮切换器（只上主题）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-open", action="store_true",
                    help="装完不自动弹提示页（默认会弹，让用户一次看到「还能要什么」）")
    args = ap.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"❌ 项目目录不存在：{project}", file=sys.stderr)
        return 1

    print(f"== 目标项目：{project}")
    dest, url, log = build_bundle(project, args.sets, args.dry_run, args.no_switcher)
    print(f"== 接入包：{log}")

    bundle = dest / f"{MARKER}"
    count = None
    if bundle.exists():
        text = bundle.read_text(encoding="utf-8")
        count = len(re.findall(r'"id":\s*"', text))
        size_kb = bundle.stat().st_size // 1024
        print(f"   文件 {bundle}")
        print(f"   体积 {size_kb} KB ｜ 内含套组 {count} 套 ｜ 悬浮切换器 {'无（--no-switcher）' if args.no_switcher else '有'}")

    cands = find_entry_candidates(project)
    if not cands:
        print("⚠ 没找到可以接线的入口文件（没有 app/layout.tsx，也没有含 <head> 的 html）。")
        print(f"   请手工在你页面的 <head> 里加：<script src=\"{url}{MARKER}\"></script>")
        return 1

    entry, kind, anchor = cands[0]
    status, before, after = inject(entry, url, anchor, args.dry_run)
    label = {"next-app-router": "Next.js App Router", "html-head": "HTML 页面"}[kind]
    print(f"== 宿主类型：{label}（锚点 {anchor}）→ {entry.relative_to(project)}")
    if status == "already":
        print("   已经接过了，跳过（幂等）")
    elif status == "no-anchor":
        print(f"⚠ 这个文件里找不到 {anchor} 锚点，没有改它。")
        print(f"   请手工加：<script src=\"{url}{MARKER}\"></script>")
        return 1
    elif status == "would":
        print("   [dry-run] 会插入：")
        for line in after.splitlines():
            if MARKER in line:
                print("     " + line.strip())
    else:
        print("   已插入 script 标签（原文件备份在同目录 .loki-bak-*）")

    # ---- 回读验证 ----
    print("\n== 回读验证 ==")
    ok = True
    if args.dry_run:
        print("   （dry-run：没有生成文件，跳过回读）")
    elif count is None:
        print("   ✗ 接入包没生成成功"); ok = False
    else:
        print(f"   {'✓' if count >= 1 else '✗'} 接入包含 {count} 套主题")
    if not args.dry_run:
        now = entry.read_text(encoding="utf-8")
        print(f"   {'✓' if MARKER in now else '✗'} script 标签在 {entry.relative_to(project)} 里")
        print(f"   {'✓' if bundle.exists() else '✗'} 接入包在 {bundle.relative_to(project)}")
        ok = ok and MARKER in now and bundle.exists()
    print()
    if args.dry_run:
        print("（dry-run：一个文件都没改）")
    elif ok:
        print("接好了。启动你的项目就能看到：页面右下角会出现「外观」按钮，")
        print(f"{count if count else '全部'} 套主题可以随便切，选择被记住。")
        # 交付这一环不要漏：用户装完必须知道「还想要什么该说什么」，
        # 否则他只会看到换了颜色，以为这个 Skill 就这样。
        user_doc = bundle.parent / "给你的用户.md"
        switch = "右下角会有「外观」按钮" if not args.no_switcher else "主题已经在页面上了"
        print()
        print("== 现在把这一段交给用户（照抄，数字按实际改） ==")
        print(f"""
   已经接好了：启动你的项目，{switch}，{count if count else '全部'} 套可以随便切，选择会被记住。

   先说清楚一件事：**这一步只换了配色和基本字体圆角**。侧栏、卡片、气泡、代码块这些
   UI 部件要不要也跟着变成这套主题的样子，是另一层，得针对你的界面单独适配一遍。
   想要就跟我说一句「**连 UI 部件也一起变**」。

   另外三件事也随时跟我说就行：只想留几套 →「我只要这几套」；
   重启/升级后外观掉了 →「把外观恢复回来」；不想每次都叫我 →「我要开机自动恢复」。
""")
        print(f"（完整的能力清单在 {user_doc}，可以直接发给用户）")
        # 装完**直接弹给用户看**，别让他自己去翻文档。
        page = user_doc.with_suffix(".html")
        if not page.exists():
            subprocess.run([sys.executable, str(HERE / "welcome.py"), "--out", str(page),
                            "--sets", str(count or 0)], capture_output=True, text=True)
        if page.exists():
            if args.no_open:
                print(f"（没开浏览器；要看得话打开这个文件：{page}）")
            else:
                subprocess.Popen(["open", str(page)])
                print(f"\n已经用浏览器打开这一页给用户看了：{page}")
                print("（不想自动打开：下次加 --no-open）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
