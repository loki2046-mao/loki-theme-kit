#!/usr/bin/env python3
"""把套组的**结构件**接进宿主：认领角色 → 挂契约钩子 → 实测验证 → 跟着宿主升级。

套组分两层：
  · 颜色/圆角/字体/状态色 → 靠**令牌**搬过去，任何宿主都能过；
  · 结构件（纸面纹理、贴纸圆边、撕口、计数器编号、扫描线、四角准星、气泡尾巴……）
    → 挂在 `.loki-*` 这些语义钩子上，普通宿主没有这些钩子，所以**会全部落空**。

这个脚本补的就是这一环。不去改 35 套主题、也不去改宿主源码，而是给宿主的真实元素
**加上**那批钩子类名 —— 于是 35 套结构层原封不动生效。每个宿主只需要一份角色对照表
（`adapters/<宿主>/binding.json`），由 `probe.py` 出草案、你来定稿。

    python3 scripts/adapt.py --host cola --port 9333 --check     # 逐条实测：哪些角色真的匹配上了
    python3 scripts/adapt.py --host cola --port 9333 --verify    # 挂上钩子后：结构件到了多少、有没有改坏布局
    python3 scripts/adapt.py --host cola --port 9333 --render --out /tmp/cola   # 生成能注入的 roles.js
    python3 scripts/adapt.py --host cola --port 9333 --install --css <套组 css>
    python3 scripts/adapt.py --host cola --port 9333 --refresh   # 宿主升级后：一条命令重认并重验

为什么要有 --refresh：宿主一升级，DOM 一改，选择器就可能失效，结构件会**悄悄**落空。
所以挂钩器匹配不到时会往控制台喊；`--check` / `--verify` 也把「匹配到几个」算成硬数字。
"--refresh" 会重新盘点、把失效的角色就地重认、写回对照表，再跑一遍验证。
"""
import argparse
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
ADAPTERS = ROOT / "adapters"
SETS = ROOT / "sets"

# 这些属性一变，说明结构件**改动了宿主的排版** —— 要盯，可能是好事也可能是闯祸
LAYOUT_KEYS = ["display", "position", "w", "h", "mt", "mb", "ml", "mr", "pt", "pb", "pl", "pr",
               "ovx", "ovy", "dir", "gap", "maxW", "whiteSpace", "fs", "lh", "ls"]
# 这些是「帅的东西」：纹理 / 圆角 / 投影 / 裁切 / 前后缀装饰
DECOR_KEYS = ["bi", "btw", "bts", "btc", "rad", "sh", "cp", "tf", "fil", "tt", "ff", "c1", "c2", "b1", "a1"]


# ---------- CDP ----------

def cdp(port, expr, url_match=None):
    spec = importlib.util.spec_from_file_location("inject_cdp", HERE / "inject-cdp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ws, send, _ = mod.connect(port, url_match)
    try:
        return mod.evaluate(send, expr)
    finally:
        ws.close()


def inject_expr(binding, watch=False):
    roles = binding.get("roles", {})
    cfg = json.dumps({"roles": roles, "prefix": binding.get("prefix", "loki-"), "watch": watch},
                     ensure_ascii=False)
    tagger = (ROOT / "templates" / "tagger.js").read_text(encoding="utf-8")
    return f"window.__LOKI_ROLES__ = {cfg};\n{tagger}\n;window.__LOKI_ROLE_REPORT__"


CLEANUP = """
(function () {
  var n = 0;
  document.querySelectorAll('[data-loki-role]').forEach(function (el) {
    var r = el.getAttribute('data-loki-role');
    el.classList.remove('loki-' + r);
    el.removeAttribute('data-loki-role');
    n++;
  });
  return n;
})()
"""

MEASURE = r"""
(function () {
  function snap(el) {
    var cs = getComputedStyle(el), b = getComputedStyle(el, '::before'), a = getComputedStyle(el, '::after');
    return {
      display: cs.display, position: cs.position, w: cs.width, h: cs.height,
      mt: cs.marginTop, mb: cs.marginBottom, ml: cs.marginLeft, mr: cs.marginRight,
      pt: cs.paddingTop, pb: cs.paddingBottom, pl: cs.paddingLeft, pr: cs.paddingRight,
      ovx: cs.overflowX, ovy: cs.overflowY, dir: cs.flexDirection, gap: cs.gap,
      maxW: cs.maxWidth, whiteSpace: cs.whiteSpace, fs: cs.fontSize, lh: cs.lineHeight, ls: cs.letterSpacing,
      bi: cs.backgroundImage, btw: cs.borderTopWidth, bts: cs.borderTopStyle, btc: cs.borderTopColor,
      rad: cs.borderTopLeftRadius, sh: cs.boxShadow, cp: cs.clipPath, tf: cs.transform,
      fil: cs.filter, tt: cs.textTransform, ff: cs.fontFamily,
      c1: b.content, b1: b.backgroundImage, c2: a.content, a1: a.backgroundImage
    };
  }
  var LAYOUT = __LAYOUT__, DECOR = __DECOR__;
  var rec = [].slice.call(document.querySelectorAll('[data-loki-role]')).map(function (el) {
    return { role: el.getAttribute('data-loki-role'), el: el };
  });
  // 全局：整页元素的几何快照。只带钩子的元素会被量到，**钩子影响的子孙**也会现形
  // （比如 `.loki-chat-stream > div { max-width: 38rem }` 改的是子元素，不在挂着钩子的那层）。
  var all = [].slice.call(document.querySelectorAll('body *')).slice(0, 2500);
  function geo(el) {
    var r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return [Math.round(r.width), Math.round(r.height), r.top, cs.display, cs.visibility];
  }
  var allA = all.map(geo), withHook = rec.map(function (r) { return snap(r.el); });
  rec.forEach(function (r) { r.el.classList.remove('loki-' + r.role); });
  document.body.offsetHeight;
  var without = rec.map(function (r) { return snap(r.el); });
  var allB = all.map(geo);
  rec.forEach(function (r) { r.el.classList.add('loki-' + r.role); });
  document.body.offsetHeight;
  var gSize = 0, gHidden = 0, gMoved = 0;
  for (var i = 0; i < all.length; i++) {
    var x = allA[i], y = allB[i];
    if (y[3] === 'none' && x[3] !== 'none') { gHidden++; continue; }
    if (Math.abs(x[0] - y[0]) > Math.max(6, x[0] * 0.2) || Math.abs(x[1] - y[1]) > Math.max(6, x[1] * 0.2)) gSize++;
    else if (Math.abs(x[2] - y[2]) > 6) gMoved++;
  }

  var byRole = {}, layoutHits = 0, decorHits = 0, sizeBig = 0, hidden = 0;
  rec.forEach(function (r, i) {
    var a = without[i], b = withHook[i];
    var dl = LAYOUT.filter(function (k) { return a[k] !== b[k]; });
    var dd = DECOR.filter(function (k) { return a[k] !== b[k]; });
    var g = byRole[r.role] || (byRole[r.role] = { n: 0, layout: 0, decor: 0, keys: {}, pairs: [] });
    g.n++;
    dl.forEach(function (k) {
      g.layout++; g.keys[k] = (g.keys[k] || 0) + 1;
      if (g.pairs.length < 8) g.pairs.push('[' + r.role + '] ' + k + ': ' + a[k] + ' → ' + b[k]);
    });
    dd.forEach(function (k) { g.decor++; g.keys[k] = (g.keys[k] || 0) + 1; });
    layoutHits += dl.length; decorHits += dd.length;
    var wA = parseFloat(a.w), wB = parseFloat(b.w), hA = parseFloat(a.h), hB = parseFloat(b.h);
    if (Math.abs(wA - wB) > Math.max(4, wA * 0.2) || Math.abs(hA - hB) > Math.max(4, hA * 0.2)) sizeBig++;
    if (b.display === 'none' && a.display !== 'none') hidden++;
  });
  return { roles: byRole, layoutHits: layoutHits, decorHits: decorHits, sizeBig: sizeBig,
           hidden: hidden, tagged: rec.length, docH: document.documentElement.scrollHeight,
           global: { total: all.length, sizeBig: gSize, hidden: gHidden, moved: gMoved } };
})()
"""


# ---------- 读写 ----------

def binding_path(host):
    return ADAPTERS / host / "binding.json"


def load_binding(host):
    p = binding_path(host)
    if not p.exists():
        print(f"没有 {p}。先用 probe.py 出草案：python3 scripts/probe.py --port <端口>", file=sys.stderr)
        sys.exit(2)
    return json.loads(p.read_text(encoding="utf-8"))


def save_binding(host, b):
    p = binding_path(host)
    if p.exists():
        bak = p.with_suffix(".json.bak")
        bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text(json.dumps(b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_js(binding):
    roles = binding.get("roles", {})
    cfg = json.dumps({"roles": roles, "prefix": binding.get("prefix", "loki-"), "watch": True},
                     ensure_ascii=False)
    tagger = (ROOT / "templates" / "tagger.js").read_text(encoding="utf-8")
    head = ("/* 由 loki-theme-kit / adapt.py 生成 —— 结构件挂钩器 + 这份宿主角色对照表。\n"
            f" * 宿主：{binding.get('host')}　盘点日期：{binding.get('probed_at')}\n"
            " * 重新生成：python3 scripts/adapt.py --host <宿主> --port <端口> --refresh\n */\n")
    return head + "window.__LOKI_ROLES__ = " + cfg + ";\n" + tagger


def set_hooks(set_dir):
    css = (set_dir / "theme.css").read_text(encoding="utf-8")
    return set(re.findall(r"\.loki-([a-z0-9-]+)", css))


# ---------- 子命令 ----------

def cmd_check(host, port, url_match, keep=False):
    b = load_binding(host)
    report = cdp(port, inject_expr(b, watch=False), url_match)
    if not isinstance(report, dict):
        print("没拿到报告，检查宿主是否在跑 / 端口是否正确", file=sys.stderr)
        return 2
    roles = b.get("roles", {})
    dead = [k for k in roles if report.get(k, 0) <= 0]
    broken = [k for k in dead if report.get(k) == -1]
    print(f"宿主 {host}：绑定 {len(roles)} 个角色，匹配到元素共 {report.get('__total', 0)} 个\n")
    for k in roles:
        n = report.get(k, 0)
        mark = "✓" if n > 0 else "✗"
        print(f"  {mark} {k:<24} ×{n:<5} {roles[k] if isinstance(roles[k], str) else roles[k].get('selector')}")
    if dead:
        print(f"\n⚠ {len(dead)} 个角色此刻一个元素都没匹配到：{', '.join(dead)}")
        print("  两个原因会长成这样：① 宿主升级改了 DOM（真失效）；"
              "② 那块界面现在根本没出现在屏幕上（比如发送按钮只在会话里才有）。")
        print("  判据：**少量**为 0 多半是 ②，**大面积**为 0 才是 ①（见下面的结论）。")
    else:
        print("\n✓ 全部角色都匹配到了")
    # 报警门槛：只有「大面积失效」或「选择器本身写错了」才值得把 --refresh 叫起来。
    # 单个角色为 0 多半只是那块 UI 当前不在屏幕上 —— 一惊一乍地自动重认反而会改错东西。
    loud = bool(broken) or len(dead) > max(1, len(roles) // 3)
    if dead:
        if loud:
            print(f"\n✗ 判定：宿主结构变了 —— 跑 `adapt.py --host {host} --port {port} --refresh --apply` 重认")
        else:
            print(f"\n✓ 判定：只是当前界面没露出这些部件，不用动对照表（要确认就把对应面板点开再跑一次）")
    if not keep:
        cdp(port, CLEANUP, url_match)
    return 1 if loud else 0


def cmd_verify(host, port, url_match, keep=False):
    b = load_binding(host)
    cdp(port, CLEANUP, url_match)
    report = cdp(port, inject_expr(b, watch=False), url_match)
    js = MEASURE.replace("__LAYOUT__", json.dumps(LAYOUT_KEYS)).replace("__DECOR__", json.dumps(DECOR_KEYS))
    m = cdp(port, js, url_match)

    print(f"宿主 {host}｜挂上钩子的元素 {m['tagged']} 个\n")
    print("▌角色 → 结构件命中情况（「装饰」= 纹理/圆角/投影/裁切/前后缀；「排版」= 尺寸/内外边距/溢出/字号）")
    print("─" * 78)
    rows = sorted(m["roles"].items(), key=lambda kv: -(kv[1]["decor"] + kv[1]["layout"]))
    for role, g in rows:
        top = sorted(g["keys"].items(), key=lambda kv: -kv[1])[:4]
        tops = " ".join(f"{k}×{v}" for k, v in top)
        override = [k for k in g["keys"] if k in OVERRIDE_KEYS]
        flag = (" ⚠接管了 " + ",".join(override)) if override else (" ·改尺寸/内边距" if g["layout"] else "")
        print(f"  {role:<24} ×{g['n']:<4} 装饰 {g['decor']:<4}排版 {g['layout']:<4}{flag}  {tops}")
    print("─" * 78)
    print(f"  装饰变化 {m['decorHits']} 处｜排版变化 {m['layoutHits']} 处"
          f"｜尺寸变化 >20% 的元素 {m['sizeBig']} 个｜被隐藏的元素 {m['hidden']} 个")

    # 「改尺寸/内边距」是结构件的正常后果（加了边框、行高就变），不算围祸；
    # 真正要盯的是「直接接管宿主排版机制」的那几个属性。
    risky = [r for r, g in m["roles"].items() if any(k in g["keys"] for k in OVERRIDE_KEYS)]
    if risky:
        print(f"\n⚠ 这些角色直接接管了宿主的排版机制（display/position/溢出），装主题前先看一眼：{', '.join(sorted(risky))}")
    if m["hidden"] > 0:
        print(f"\n✗ 有 {m['hidden']} 个元素被结构件隐藏了 —— 这是闯祸，去查对应的钩子")
    else:
        print("\n✓ 没有被结构件隐藏的元素；其余「排版变化」都是加边框/行高带出来的正常后果")

    # 结构件覆盖率：每套主题用了哪些钩子，真正挂上的有几个
    matched = {k for k, v in report.items() if isinstance(v, int) and v > 0}
    print("\n▌结构件覆盖率（该套主题用到的钩子里，真正挂到宿主元素上的比例）")
    print("─" * 78)
    sets = sorted(d for d in SETS.iterdir() if d.is_dir() and (d / "theme.css").exists())
    all_hooks = set()
    worst = []
    for d in sets:
        hooks = set_hooks(d)
        all_hooks |= hooks
        hit = hooks & matched
        pct = 100.0 * len(hit) / len(hooks) if hooks else 100.0
        worst.append((pct, d.name, len(hooks), len(hit), sorted(hooks - hit)))
    for pct, name, tot, hit, miss in sorted(worst)[:8]:
        print(f"  {name:<22} {hit:>3}/{tot:<3} {pct:5.1f}%   缺：{', '.join(miss[:6])}{'…' if len(miss) > 6 else ''}")
    avg = sum(w[0] for w in worst) / len(worst)
    print(f"  —— 35 套平均结构件覆盖率：{avg:.1f}%")
    unbound = sorted(all_hooks - matched)
    print(f"\n  这个宿主上完全没挂上的钩子（结构件会落空，按需补 binding）：{', '.join(unbound)}")
    if not keep:
        cdp(port, CLEANUP, url_match)
    return 0


def cmd_render(host, out):
    b = load_binding(host)
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    p = out / "loki-roles.js"
    p.write_text(render_js(b), encoding="utf-8")
    print(f"已生成 {p}（{p.stat().st_size} 字节，含 {len(b.get('roles', {}))} 个角色）")
    print("用法：和套组 css 一起注入，顺序随意（挂钩器会让 MutationObserver 持续补挂）")
    return 0


def cmd_install(host, port, css, url_match):
    b = load_binding(host)
    out = pathlib.Path("/tmp/loki-adapt"); out.mkdir(parents=True, exist_ok=True)
    js = out / "loki-roles.js"
    js.write_text(render_js(b), encoding="utf-8")
    cmd = [sys.executable, str(HERE / "inject-cdp.py"), "--port", str(port), "--js", str(js)]
    if css:
        cmd += ["--css", css]
    if url_match:
        cmd += ["--url-match", url_match]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        return r.returncode
    print()
    return cmd_check(host, port, url_match, keep=True)


# 这几个属性被改，是「直接接管了宿主自己的排版机制」—— 要单独拎出来看
OVERRIDE_KEYS = ("display", "position", "ovx", "ovy", "whiteSpace")
# 这几个变了只能说明「尺寸跟着字号/内边距变了」，是结构件的正常后果，不算闯祸
CONSEQUENCE_KEYS = ("w", "h", "mt", "mb", "ml", "mr", "pt", "pb", "pl", "pr",
                    "gap", "maxW", "fs", "lh", "ls")


def cmd_triage(host, port, url_match, themes, apply=False):
    """逐钩子隔离测试：这个钩子自己会不会把宿主的排版弄坏。

    为什么要隔离：一起挂上时，父层钩子的字号/宽度会传给子层，量出来的“锅”会算到错的
    钩子头上。所以每个角色单独挂一次，看它对**整页几何**的影响 —— 连子孙一起看，
    因为有些规则改的就是子元素（`.loki-chat-stream > div { max-width: … }`）。"""
    b = load_binding(host)
    roles = b.get("roles", {})
    js = MEASURE.replace("__LAYOUT__", json.dumps(LAYOUT_KEYS)).replace("__DECOR__", json.dumps(DECOR_KEYS))
    agg = {}
    for tid in themes:
        print(f"  采样主题 {tid} …", flush=True)
        cdp(port, f"document.documentElement.setAttribute('data-cola-skin', {json.dumps(tid)}); 1", url_match)
        for role, spec in roles.items():
            cdp(port, CLEANUP, url_match)
            cdp(port, inject_expr({"roles": {role: spec}, "prefix": b.get("prefix", "loki-")}, watch=False), url_match)
            m = cdp(port, js, url_match)
            g = m.get("global", {})
            r0 = m.get("roles", {}).get(role, {})
            a = agg.setdefault(role, {"decor": 0, "layout": 0, "sizeBig": 0, "moved": 0, "hidden": 0,
                                      "total": 0, "keys": {}, "pairs": [], "worst_ratio": 0.0, "themes": []})
            ratio = g.get("sizeBig", 0) / max(1, g.get("total", 1))
            a["decor"] += r0.get("decor", 0)
            a["layout"] += r0.get("layout", 0)
            a["sizeBig"] += g.get("sizeBig", 0)
            a["moved"] += g.get("moved", 0)
            a["hidden"] += g.get("hidden", 0)
            a["total"] += g.get("total", 0)
            a["worst_ratio"] = max(a["worst_ratio"], ratio)
            for k, v in r0.get("keys", {}).items():
                a["keys"][k] = a["keys"].get(k, 0) + v
            for p in r0.get("pairs", []):
                if len(a["pairs"]) < 8 and p not in a["pairs"]:
                    a["pairs"].append(p)
            if ratio > 0.30:
                a["themes"].append(tid)
    cdp(port, CLEANUP, url_match)

    print(f"\n▌钩子隔离测试（采样 {len(themes)} 套主题：{', '.join(themes)}）")
    print("  判定：✗ 自动撤下 = 藏了元素 / 把溢出改成 hidden / 整页 >60% 元素尺寸大变；"
          "⚠ 要人看一眼 = 接管了 display/position/溢出，或整页 >10% 元素尺寸变化；✓ = 基本只动装饰")
    print("─" * 96)
    print(f"  {'钩子':<20}{'装饰':>6}{'排版':>6}{'尺寸大变':>9}{'位移':>7}{'隐藏':>6}{'最差比例':>9}  判定")
    verdicts = {}
    for role, a in sorted(agg.items(), key=lambda kv: kv[1]["worst_ratio"], reverse=True):
        override = [k for k in a["keys"] if k in OVERRIDE_KEYS and a["keys"][k] > 0]
        clipped = any(p.split('→')[-1].strip() in ('hidden', 'clip') for p in a["pairs"] if p.split(':')[-1].strip().split('→')[0].strip() in ('ovx', 'ovy'))
        if a["hidden"]:
            v, why = "✗ 撤下", "藏了元素"
        elif clipped:
            v, why = "✗ 撤下", "溢出被改成 hidden（会裁掉内容）"
        elif a["worst_ratio"] > 0.60:
            v, why = "✗ 撤下", "整页 >60% 元素尺寸大变"
        elif override or a["worst_ratio"] > 0.10:
            v, why = "⚠ 看着办", ("接管了 " + ",".join(override) if override else "") + \
                (f"整页 {a['worst_ratio']*100:.0f}% 元素尺寸变化" if a["worst_ratio"] > 0.10 else "")
        else:
            v, why = "✓ 保留", ""
        verdicts[role] = (v, why)
        print(f"  {role:<20}{a['decor']:>6}{a['layout']:>6}{a['sizeBig']:>9}{a['moved']:>7}"
              f"{a['hidden']:>6}{a['worst_ratio']*100:>8.1f}%  {v} {why}")
        if v.startswith("⚠") and a["pairs"]:
            for p in a["pairs"][:3]:
                print(f"        · {p}")

    drop = [r for r, (v, _) in verdicts.items() if v.startswith("✗")]
    warn = [r for r, (v, _) in verdicts.items() if v.startswith("⚠")]
    keep = [r for r, (v, _) in verdicts.items() if v.startswith("✓")]
    print(f"\n  保留 {len(keep)}｜看着办 {len(warn)}｜撤下 {len(drop)}")
    if warn:
        print(f"  ⚠ 要人看一眼的：{', '.join(warn)}")
    if apply and drop:
        withdrawn = b.setdefault("withdrawn", {})
        for r in drop:
            withdrawn[r] = {"selector": b["roles"][r], "reason": verdicts[r][1],
                            "triage": "adapt.py --triage", "at": __import__("time").strftime("%Y-%m-%d")}
            del b["roles"][r]
        save_binding(host, b)
        print(f"\n  已把 {len(drop)} 个钩子从 roles 移到 withdrawn 写回 {binding_path(host)}（旧的存成 .json.bak）")
        print("  它们不再被挂上 → 那些装饰位在这个宿主上是空的（其它 34 套不受影响）")
    elif drop:
        print(f"\n  发现 {len(drop)} 个该撤下的钩子，但没写盘（加 --apply 才改 binding.json）")
    return 0


STAMP_JS = """
(function () {
  var out = {};
  var roles = __ROLES__;
  for (var role in roles) {
    var spec = roles[role], sel = typeof spec === 'string' ? spec : spec.selector;
    var n = 0, r0 = null;
    try {
      var nodes = document.querySelectorAll(sel);
      for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        if (typeof spec !== 'string') {
          if (spec.within && !el.closest(spec.within)) continue;
          if (spec.has && !el.querySelector(spec.has)) continue;
          if (spec.not && el.closest(spec.not)) continue;
        }
        if (!r0) { var r = el.getBoundingClientRect(); r0 = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; }
        n++;
      }
    } catch (e) { n = -1; }
    out[role] = { n: n, rect: r0 };
  }
  return out;
})()
"""


def measure_role(port, sel, url_match=None):
    """现场量一个选择器：匹配几个、第一个元素的位置尺寸。"""
    js = f"""(function () {{
      try {{
        var nodes = document.querySelectorAll({json.dumps(sel)});
        if (!nodes.length) return {{ n: 0, rect: null }};
        var r = nodes[0].getBoundingClientRect();
        return {{ n: nodes.length, rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] }};
      }} catch (e) {{ return {{ n: -1, rect: null }}; }}
    }})()"""
    return cdp(port, js, url_match)


def same_shape(ev, got):
    """新候选跟当初记下的位置/尺寸像不像 —— 「匹配得上」不等于「还是那个东西」。"""
    if not ev or not got or got.get("n", 0) <= 0:
        return False, "新候选匹配 0 个"
    en, gn = ev.get("n", 0), got["n"]
    # 数量**只查变宽、不查变少**：列表/消息流是懒渲染的，滚一下数量就会变，
    # 比少了会误杀（实测：表格从 10 个变 2 个，其实选择器一点没错）。
    # 但数量暴涨说明新选择器比原来宽得多，那就不是同一个东西了。
    if gn > max(en * 3, en + 5):
        return False, f"匹配数量暴涨（当初 {en} 个，现在 {gn} 个 —— 新选择器比原来宽）"
    er, gr = ev.get("rect"), got.get("rect")
    if er and gr:
        # 横向位置要比（左边缘一挪，多半就不是原来那个东西了）
        if abs(er[0] - gr[0]) > 60:
            return False, f"横向位置对不上（当初 x={er[0]}，现在 x={gr[0]}）"
        # 尺寸要比
        for i in (2, 3):
            a, b = er[i], gr[i]
            if a > 40 and abs(a - b) > max(24, a * 0.35):
                return False, f"尺寸对不上（当初 {a}px，现在 {b}px）"
        # **纵向位置不比**：元素可能在滚动容器里，视口 y 会随滚动位置变 —— 比它会误杀
        # （实测：表格在消息流里滚了 101px 就被判「不是原来那个」，其实一模一样）。
    return True, ""


def cmd_stamp(host, port, url_match):
    """把每个角色现在的「匹配几个、在什么位置」记进 binding.json。

    为什么记：宿主升级后 `--refresh` 要靠它判断新候选**还是不是原来那个东西**。
    只判断「新选择器匹配上了」不够 —— 比如侧栏的备用候选是 `body>div:nth-of-type(1)`，
    它当然能匹配到元素（整个应用根），但那是错的。"""
    b = load_binding(host)
    got = cdp(port, STAMP_JS.replace("__ROLES__", json.dumps(b.get("roles", {}), ensure_ascii=False)), url_match)
    ev = b.setdefault("evidence", {})
    for role, d in (got or {}).items():
        ev[role] = d
    b["probed_at"] = __import__("time").strftime("%Y-%m-%d")
    save_binding(host, b)
    bad = [r for r, d in (got or {}).items() if d.get("n", 0) <= 0]
    print(f"已把 {len(got or {})} 个角色的现场证据记进 {binding_path(host)}" +
          (f"；其中 {len(bad)} 个当前匹配 0 个：{', '.join(bad)}" if bad else "；全部匹配正常"))
    return 0


def cmd_refresh(host, port, url_match, apply=False):
    b = load_binding(host)
    roles = b.get("roles", {})
    print(f"① 重认：先看现在还有哪些角色是活的")
    report = cdp(port, inject_expr(b, watch=False), url_match)
    cdp(port, CLEANUP, url_match)
    dead = [k for k in roles if report.get(k, 0) <= 0]
    print(f"   {len(roles) - len(dead)}/{len(roles)} 个角色活着" + (f"，失效 {len(dead)} 个：{', '.join(dead)}" if dead else ""))
    if not dead:
        print("\n③ 没有失效，什么都不用改。")
        return 0

    print("\n② 重新盘点宿主，给失效的角色找新位置")
    r = subprocess.run([sys.executable, str(HERE / "probe.py"), "--port", str(port), "--json"]
                       + (["--url-match", url_match] if url_match else []),
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("   盘点失败：" + (r.stderr or "").strip()[:200], file=sys.stderr)
        return 2
    props = json.loads(r.stdout)
    ev = b.get("evidence", {})
    fixed, manual = {}, []
    for role in dead:
        cand = props.get("loki-" + role)
        if not cand:
            manual.append((role, "盘点也没认出这个位置"))
            continue
        sel = cand["selector"]
        got = measure_role(port, sel, url_match)
        ok, why = same_shape(ev.get(role), got)
        if ok:
            fixed[role] = sel
            print(f"   {role:<24} → {sel}   （实测 ×{got['n']}，位置尺寸跟当初对得上）")
        else:
            manual.append((role, f"新候选 {sel} 被否了：{why}"))

    print()
    if fixed and apply:
        roles.update(fixed)
        b["roles"] = roles
        b["probed_at"] = __import__("time").strftime("%Y-%m-%d")
        b.setdefault("refresh_log", []).append(
            {"at": b["probed_at"], "auto_fixed": fixed, "needs_human": [m[0] for m in manual]})
        save_binding(host, b)
        print(f"③ 已把 {len(fixed)} 个角色写回 {binding_path(host)}（旧的存成 .json.bak）")
    elif fixed:
        print(f"③ 找到 {len(fixed)} 个可自动修的角色，但**没有写盘**（加 --apply 才写）：")
        for k, v in fixed.items():
            print(f"     {k:<24} → {v}")
    if manual:
        print(f"\n⚠ {len(manual)} 个角色要人工看一眼：")
        for k, why in manual:
            print(f"     {k:<24} {why}")
    if fixed or manual:
        print("\n④ 改完再跑一遍验证：python3 scripts/adapt.py --host %s --port %d --verify" % (host, port))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="宿主名（对应 adapters/<宿主>/binding.json）")
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--url-match")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--stamp", action="store_true", help="把角色当前的匹配数/位置尺寸记进 binding.json（refresh 要用）")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--triage", action="store_true", help="逐钩子隔离测试：它会不会弄坏宿主排版")
    ap.add_argument("--themes", help="triage 采样哪几套主题，逗号分隔")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--apply", action="store_true", help="refresh 时把结果写回 binding.json")
    ap.add_argument("--keep", action="store_true", help="验证完不要把钩子摘掉")
    ap.add_argument("--css", help="install / verify 用的套组 CSS")
    ap.add_argument("--out", default="/tmp/loki-adapt", help="render 的输出目录")
    args = ap.parse_args()

    if args.refresh:
        return cmd_refresh(args.host, args.port, args.url_match, args.apply)
    if args.install:
        return cmd_install(args.host, args.port, args.css, args.url_match)
    if args.triage:
        themes = (args.themes.split(",") if args.themes
                  else ["loki-ease", "loki-terminal", "loki-pop", "urban-collage"])
        return cmd_triage(args.host, args.port, args.url_match, themes, args.apply)
    if args.verify:
        return cmd_verify(args.host, args.port, args.url_match, args.keep)
    if args.render:
        return cmd_render(args.host, args.out)
    if args.check:
        return cmd_check(args.host, args.port, args.url_match, args.keep)
    if args.stamp:
        return cmd_stamp(args.host, args.port, args.url_match)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
