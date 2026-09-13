#!/usr/bin/env python3
"""从一张参考图里量出主色，并给出「该怎么映射成主题令牌」的建议。

用法：
    python3 scripts/palette.py 参考图.png
    python3 scripts/palette.py 参考图.png --colors 6 --json

为什么要有它：做外观最难的一步不是写 CSS，是「我这张很喜欢，到底该取哪几个色」。
肉眼取色会漏掉面积最大的那个底——而底决定了这套主题是舒服还是刺眼。

输出：
  - 按面积排序的主色表（含占比、亮度、饱和度）
  - 建议映射：canvas / surface / text / muted / accent / accent-ink
  - 直接可粘的 CSS 片段（--bg-canvas: … 一行行）
  - 一句风险提示：建议的正文对比度是多少，够不够 7:1
"""
import argparse
import json
import re
import sys
from pathlib import Path


def lum(rgb):
    f = lambda c: (c / 255) / 12.92 if (c / 255) <= 0.03928 else (((c / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def hex_of(rgb):
    return "#%02x%02x%02x" % rgb


def sat(rgb):
    mx, mn = max(rgb), min(rgb)
    return 0 if mx == 0 else (mx - mn) / mx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--colors", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("需要 Pillow：pip install pillow", file=sys.stderr)
        return 2

    im = Image.open(args.image).convert("RGB")
    im.thumbnail((900, 900))
    q = im.quantize(colors=args.colors, method=Image.MEDIANCUT)
    palette = q.getpalette()
    counts = sorted(q.getcolors(), key=lambda x: -x[0])
    total = sum(c for c, _ in counts)

    rows = []
    for count, idx in counts:
        rgb = tuple(palette[idx * 3:idx * 3 + 3])
        rows.append({"hex": hex_of(rgb), "pct": round(count / total * 100, 1),
                     "lum": round(lum(rgb), 3), "sat": round(sat(rgb), 2), "rgb": rgb})

    by_area = list(rows)

    def mix(a, b, t):
        return tuple(round(x + (y - x) * t) for x, y in zip(a, b))

    def darken(rgb, target_lum):
        """朝黑色收缩到目标亮度（保住色相，只压明度）。"""
        lo, hi = 0.0, 1.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if lum(mix(rgb, (0, 0, 0), mid)) > target_lum:
                lo = mid
            else:
                hi = mid
        return mix(rgb, (0, 0, 0), hi)

    def toward(rgb, other, want_ratio, floor=0.0):
        """把 rgb 往 other 混到「对比度 ≥ want_ratio」为止。"""
        lo, hi = floor, 1.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if ratio(mix(rgb, other, mid), other) < want_ratio:
                lo = mid
            else:
                hi = mid
        return mix(rgb, other, hi)

    lightest = max(rows, key=lambda r: r["lum"])
    darkest = min(rows, key=lambda r: r["lum"])
    lights = [r for r in rows if r["lum"] > 0.6]
    canvas = max(lights, key=lambda r: r["pct"]) if lights else lightest
    surface = lightest
    if surface["lum"] < canvas["lum"]:
        surface = canvas  # 面不能比底还暗，否则卡片"陷进去"

    # 正文：原图最暗的那个往往不够黑。判据不是"亮度多少"，而是"压在上面够不够 7:1"，
    # 所以按对比度压深，压到刚好有余量为止。
    fixes = []
    text_rgb = darkest["rgb"]
    if ratio(text_rgb, surface["rgb"]) < 7.0:
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if ratio(mix(text_rgb, (0, 0, 0), mid), surface["rgb"]) < 7.2:
                lo = mid
            else:
                hi = mid
        text_rgb = mix(text_rgb, (0, 0, 0), hi)
        fixes.append(f"原图最暗色 {darkest['hex']} 压正文只有 {ratio(darkest['rgb'], surface['rgb']):.1f}:1，"
                     f"已按比例压深到 {hex_of(text_rgb)}（色相不变，只压明度）")

    # 辅助小字：从底往正文方向调，达到 4.8:1（留一点余量），但不得比正文还深
    muted_rgb = toward(canvas["rgb"], text_rgb, 4.8)
    if ratio(muted_rgb, canvas["rgb"]) >= ratio(text_rgb, canvas["rgb"]) - 0.05:
        fixes.append("原图里没有可用的中间调，辅助色只能贴着正文调出来——"
                     "建议自己手调一档更淡、但辅助/底仍 ≥ 4.5 的灰")

    # 强调：要饱和度够、亮度居中（能压得住浅色字）；没有就从最饱和的那个调出来
    candidates = [r for r in rows if 0.18 <= r["lum"] <= 0.72]
    vivid = max(candidates, key=lambda r: r["sat"]) if candidates else max(rows, key=lambda r: r["sat"])
    accent_rgb = vivid["rgb"]
    if vivid["lum"] > 0.72:
        accent_rgb = darken(accent_rgb, 0.55)
        fixes.append(f"原图最饱和色 {vivid['hex']} 太亮（压不住字），已压到 {hex_of(accent_rgb)}")
    elif vivid["lum"] < 0.18:
        fixes.append(f"原图最饱和色 {vivid['hex']} 偏暗，建议作为 -deep 档，另挑一个亮一档的做强调色")

    # 强调上的字：白字和近黑字哪边够 4.5 就用哪边
    ink_white = (255, 254, 250)
    ink_dark = (20, 20, 20)
    rw, rd = ratio(ink_white, accent_rgb), ratio(ink_dark, accent_rgb)
    ink_rgb = ink_white if rw >= rd else ink_dark
    if max(rw, rd) < 4.5:
        accent_rgb = darken(accent_rgb, 0.35)
        rw, rd = ratio(ink_white, accent_rgb), ratio(ink_dark, accent_rgb)
        ink_rgb = ink_white if rw >= rd else ink_dark
        fixes.append(f"强调色两边字都压不住，已再压深到 {hex_of(accent_rgb)}")

    suggestion = {
        "--bg-canvas": hex_of(canvas["rgb"]),
        "--bg-surface": hex_of(surface["rgb"]),
        "--text-primary": hex_of(text_rgb),
        "--text-muted": hex_of(muted_rgb),
        "--accent-copper": hex_of(accent_rgb),
        "--accent-ink": hex_of(ink_rgb),
    }
    suggestion = {k: v for k, v in suggestion.items()}
    body_ratio = ratio(hex_to_rgb(suggestion["--text-primary"]), hex_to_rgb(suggestion["--bg-surface"]))
    muted_ratio = ratio(hex_to_rgb(suggestion["--text-muted"]), hex_to_rgb(suggestion["--bg-canvas"]))
    ink_ratio = ratio(hex_to_rgb(suggestion["--accent-ink"]), hex_to_rgb(suggestion["--accent-copper"]))

    if args.json:
        print(json.dumps({"image": args.image, "colors": by_area, "suggested": suggestion,
                          "adjustments": fixes,
                          "contrast": {"text_on_surface": round(body_ratio, 2),
                                       "muted_on_canvas": round(muted_ratio, 2),
                                       "ink_on_accent": round(ink_ratio, 2)}},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"参考图：{args.image}")
    print(f"{'色值':<10}{'占比':>7}{'相对亮度':>10}{'饱和':>7}")
    for r in by_area:
        print(f"{r['hex']:<10}{r['pct']:>6.1f}%{r['lum']:>10.3f}{r['sat']:>7.2f}")
    if fixes:
        print("\n自动修补（这几步不是取色，是补条件——色相从原图来，明度按可读性压）：")
        for f in fixes:
            print("  · " + f)
    print("\n建议映射（面积优先，不是肉眼优先）：")
    for k, v in suggestion.items():
        print(f"  {k:<18}{v}")
    print("\n直接粘进 theme.css：")
    print('  :root[data-theme="你的主题名"] {')
    for k, v in suggestion.items():
        print(f"    {k}: {v};")
    print("  }")
    print(f"\n风险提示：正文/面 {body_ratio:.2f}（要 ≥ 7）、辅助/底 {muted_ratio:.2f}（要 ≥ 4.5）、"
          f"强调上文字 {ink_ratio:.2f}（要 ≥ 4.5）")
    weak = [n for n, v, need in (("正文", body_ratio, 7), ("辅助", muted_ratio, 4.5), ("强调上文字", ink_ratio, 4.5)) if v < need]
    if weak:
        print(f"  ⚠ {'、'.join(weak)}还不达标——别硬上，往 text-primary 更深 / muted 更深的方向调。")
    else:
        print("  ✓ 三档都达标。")
    return 0


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


if __name__ == "__main__":
    sys.exit(main())
