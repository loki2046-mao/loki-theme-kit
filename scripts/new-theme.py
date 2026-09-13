#!/usr/bin/env python3
"""起一套新主题的脚手架：把「从零做一套」拆成有顺序的六步，前四步自动。

用法：
    python3 scripts/new-theme.py --id my-forest --label "我的森林" --group art
    python3 scripts/new-theme.py --id my-forest --label "我的森林" --base loki-moss
    python3 scripts/new-theme.py --id my-forest --palette 参考图.png     # 顺带量色

它做什么：
  1) 建 sets/<id>/，从 --base（默认 loki-ease）复制一份令牌骨架；
  2) 把 --id/--label 写进选择器与 meta.json；
  3) 给出这套的「结构件清单」空表——这是关键：只换令牌 = 只换色，不算一套主题；
  4) --palette 给了图就顺手跑 palette.py，把建议色填进令牌。

做完脚手架后，人要做的是：
  A. 选来源板（一张你喜欢的图 / 一个真实场景）→ 用 palette.py 量色
  B. 定「结构件」：从 references/design-language.md 挑 2–4 个装置（撕口/准星/贴纸/编号/轨道…）
     写进 theme.css —— 目标是 ≥ 6 条规则、≥ 12 行
  C. 跑 python3 scripts/check.py --only <id>，六道门全过才算做完
  D. 在真实宿主里过一眼（导航有没有被挤出去、按钮文字还看得清吗）
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SETS = SKILL / "sets"

STRUCTURE_CHECKLIST = """九类结构装置（挑 2–4 个，凑够 ≥6 条规则 / ≥12 行）：

  [ ] 卡片形状      直角 / 大圆角 / 贴纸圆边 / 模切刀线
  [ ] 边框与投影    粗墨线 / 硬投影 / 发丝线 / 双层描边
  [ ] 角标与编号    左上编号芯片 / 四角准星 / 右下定位块
  [ ] 分组标识      彩色分组标签 / 前缀符号（01/02、>、//、|--）
  [ ] 激活态形态    实心块 / 左侧粗条 / 下划线 / 胶囊填充
  [ ] 内容区装饰    顶部色带 / 均衡器条 / 会话竖线 / 界格线
  [ ] 侧栏专属      侧栏底色与主区分开 / 深色侧栏 / 浅色侧栏
  [ ] 字体与字距    标题字体 / 等宽大写 / 字距拉宽 / 首字下沉
  [ ] 底纹与材质    纸纹 / 点阵 / 网格 / 扫描线（护眼组禁用）
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--group", default="art", help="care / art / retro / calm")
    ap.add_argument("--base", default="loki-ease")
    ap.add_argument("--palette", default="", help="参考图路径，顺带量色")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    dest = SETS / args.id
    base = SETS / args.base
    if not base.exists():
        print(f"基准套组不存在：{base}", file=sys.stderr)
        return 2
    if dest.exists() and not args.force:
        print(f"{dest} 已存在（要覆盖加 --force）", file=sys.stderr)
        return 2

    dest.mkdir(parents=True, exist_ok=True)
    css = (base / "theme.css").read_text(encoding="utf-8")
    css = re.sub(r'data-theme="[^"]+"', f'data-theme="{args.id}"', css)
    header = (f"/* {args.label or args.id}（{args.id}）—— 脚手架生成，基准 {args.base}。\n"
              f"   下一步：① 选定来源板量色 ② 写 2–4 个结构装置（见下）③ 跑 scripts/check.py\n"
              f"{STRUCTURE_CHECKLIST}*/\n")
    (dest / "theme.css").write_text(header + css, encoding="utf-8")

    meta = json.loads((base / "meta.json").read_text(encoding="utf-8"))
    meta.update({"id": args.id, "label": args.label or args.id, "group": args.group,
                 "derived_from": args.base, "status": "scaffold"})
    (dest / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"脚手架已建：{dest}/theme.css + meta.json（基准 {args.base}）")

    if args.palette:
        print(f"\n== 量色：{args.palette} ==")
        subprocess.run([sys.executable, str(HERE / "palette.py"), args.palette])

    print("\n下一步（顺序别换）：")
    print(f"  1) python3 scripts/check.py --only {args.id}   ← 现在多半过不了 G4（结构件不足）")
    print(f"  2) 在 {dest}/theme.css 里加 2–4 个结构装置")
    print(f"  3) 再跑 check.py 到六道门全过")
    print(f"  4) python3 scripts/gallery.py  → 在画廊里看这套的色卡，装进宿主看真实效果")
    return 0


if __name__ == "__main__":
    sys.exit(main())
