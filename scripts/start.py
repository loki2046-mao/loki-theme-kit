#!/usr/bin/env python3
"""交互向导：不想记参数就回答几个问题，剩下的事脚本做完。

    python3 scripts/start.py          # 问答式
    python3 scripts/start.py --yes    # 全用默认值（一行接入 + 推荐 10 套）

默认走「一行接入」：产出一个文件，你只要在页面里加一行 <script>，就完事了。
想要主题精确作用到卡片/侧栏/气泡这些具体元素上，再选「深度接入」。
"""
import argparse
import pathlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent

GL = {"care": "护眼阅读", "art": "艺术风格", "retro": "复古屏幕", "calm": "安静工作", "": "未分组"}


def ask(prompt, default=""):
    try:
        ans = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return ans or default


def yes(prompt, default=True):
    d = "Y/n" if default else "y/N"
    a = ask(f"{prompt} [{d}] ").lower()
    if not a:
        return default
    return a.startswith("y") or a in ("是", "要", "好")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="全部用默认值，不提问")
    args = ap.parse_args()

    index = json.loads((SKILL / "sets" / "index.json").read_text(encoding="utf-8"))
    interactive = not args.yes and sys.stdin.isatty()

    print("=" * 68)
    print("  Loki 外观套组工坊 —— 给你的 App 换上一套好看的外观")
    print("=" * 68)
    print(f"  {len(index)} 套现成主题。一行接入，不用写代码。")
    print()

    if interactive:
        print("第 0 步（可选）：先看看长什么样。")
        print(f"  浏览器打开：{SKILL}/previews/dropin/index.html")
        print("  那是接入包的示例页，右下角能切全部套组，不会改你任何东西。")
        ask("  看完了按回车继续…")

    # ---- 接入方式 ----
    mode = "dropin"
    if interactive:
        print("\n第 1 步：用哪种接入方式？")
        print("  1) 一行接入（推荐）——生成一个文件，在你页面里加一行，就完事了")
        print("     主题会自动作用到页面底色、文字、标题、链接、按钮、输入框。")
        print("  2) 深度接入——每套 CSS 分开给你 + 切换器组件 + 参考宿主")
        print("     主题能精确作用到卡片、侧栏、气泡这些具体元素（要给元素贴类名）。")
        print("     适合正式项目；第一次用可以先选 1 看看效果。")
        mode = ask("  输入 1 / 2 后回车：", "1")
        mode = "deep" if mode.strip() == "2" else "dropin"

    # ---- 挑套组 ----
    choice = "1"
    only = ""
    if interactive:
        print("\n第 2 步：要装哪几套？")
        print("  1) 作者推荐的 10 套（领地不重叠，先看这些就够了）  ← 默认")
        print("  2) 全部 %d 套（文件更大一点）" % len(index))
        print("  3) 我自己挑")
        choice = ask("  输入 1 / 2 / 3 后回车：", "1")

    if choice.strip() == "3" and interactive:
        print()
        for i, r in enumerate(index, 1):
            star = "★" if r.get("recommended") else " "
            print(f"  {i:>2}. {star} {r['label']:<10} {r['id']:<18} {GL.get(r['group'], '')}")
        sel = ask("\n  输入编号（可多个，用空格或逗号隔开，例如 1 3 5）：")
        picked = []
        for tok in sel.replace("，", ",").replace(",", " ").split():
            if tok.isdigit() and 1 <= int(tok) <= len(index):
                picked.append(index[int(tok) - 1]["id"])
            elif any(r["id"] == tok for r in index):
                picked.append(tok)
        if picked:
            only = ",".join(picked)
            print(f"  已选 {len(picked)} 套：" + "、".join(picked))
        else:
            print("  没认出编号，改用推荐的 10 套。")
            choice = "1"

    # ---- 装到哪 ----
    out = "./loki-themes"
    prefix = "loki-"
    if interactive:
        print("\n第 3 步：放到哪儿？（回车用默认，可以填绝对路径）")
        out = ask("  目录 [./loki-themes]：", "./loki-themes")
        if mode == "deep":
            print("\n第 4 步：主题里的类名前缀。默认 loki-（作者标记）。")
            print("  想让它完全像你自己的项目，就填你自己的，比如 th- 。")
            prefix = ask("  前缀 [loki-]：", "loki-")

    # ---- 干活 ----
    if mode == "dropin":
        cmd = [sys.executable, str(HERE / "bundle.py"), "--out", out]
    else:
        cmd = [sys.executable, str(HERE / "install.py"), "--out", out, "--prefix", prefix,
               "--with-switcher", "--demo", "--force"]
    if choice.strip() == "2":
        cmd.append("--all")
    elif only:
        cmd += ["--only", only]
    elif mode == "dropin":
        cmd.append("--recommended")
    else:
        cmd.append("--recommended")

    print("\n" + "-" * 68)
    print("正在生成…（不动你现有任何文件，只往目标目录里写新文件）")
    rc = subprocess.call(cmd)
    if rc != 0:
        print("生成失败，把上面的报错发给我。", file=sys.stderr)
        return rc
    print("-" * 68)

    if mode == "dropin":
        print("\n完成。你只需要做一件事——在你页面的 <head> 里加这一行：\n")
        print(f'    <script src="{out.rstrip("/")}/loki-themes.js"></script>')
        print("\n就这样。页面立刻有外观主题，右下角会出现一个「外观」按钮，")
        print(f"{'全部' if choice.strip() == '2' else (str(len(only.split(','))) + ' 套' if only else '10 套')}主题可以随便切，你的选择会被记住。")
        print("\n  现在就看效果：浏览器打开 " + out.rstrip("/") + "/index.html")
        print("  不想要了：删掉那一行 script，一切都回原样。")
        print("\n  想更精确（让主题作用到卡片/侧栏/气泡上）：再跑一次向导选「深度接入」，")
        print("  或者在你的元素上加 class=\"loki-surface\" 这类契约类名，接入包已经认识它们。")
    else:
        default_theme = "loki-ease"
        try:
            installed = json.loads((Path(out) / "themes.json").read_text(encoding="utf-8"))
            if installed:
                default_theme = installed[0]["id"]
        except Exception:
            pass
        print("\n完成。深度接入还需要三件事（脚本不替你做，因为只有你知道自己项目长什么样）：\n")
        print("  ① 在全局 CSS 里加一行：")
        print(f'       @import "{out.rstrip("/")}/index.css";')
        print("  ② 在页面根元素 <html> 上加属性：")
        print(f'       <html data-theme="{default_theme}">')
        print("  ③ 给要装饰的元素贴类名（清单见生成目录里的 README.md）")
        print(f"\n  现在就看效果：浏览器打开 {out.rstrip('/')}/demo.html")
        print(f"  切换器组件：{out.rstrip('/')}/theme-switcher.js / .tsx / .css")

    # 装完把「还能要什么」直接弹给用户看，别让他去翻 README
    try:
        page = pathlib.Path(out) / "给你的用户.html"
        subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("welcome.py")),
                        "--out", str(page)], capture_output=True, text=True)
        if page.exists():
            subprocess.Popen(["open", str(page)])
            print(f"\n  装完说明已经打开给你了：{page}")
    except Exception:
        pass

    print("\n  —— 由 Loki 制作 · 任何人可自由使用和改造。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
