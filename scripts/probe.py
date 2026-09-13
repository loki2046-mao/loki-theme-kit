#!/usr/bin/env python3
"""宿主界面盘点 + 结构件角色草案。

套组的**颜色**靠令牌就能搬过去；**结构件**（纸面、贴纸圆边、撕口、计数器编号、
扫描线、四角准星……）挂在 `.loki-*` 这些语义钩子上。普通宿主的 DOM 里没有这些
钩子，所以要先认出来「宿主里哪个元素扮演哪个角色」。

这个脚本只做两件事：
  1. 把宿主的界面抓回来（`collect-dom.js`，走 CDP 或读已有 dump）；
  2. 按几何 / 重复度 / 配色 / 输入类型，把候选角色排个序，写成草案，并打印一张
     人（或 Agent）能直接看的对照表。

它**不猜死**：每个角色给多个候选 + 证据，最终由 `adapters/<宿主>/binding.json`
定稿。定稿之后 `adapt.py` 负责挂钩子、验证、跟着宿主升级。

    python3 scripts/probe.py --port 9333                 # 连正在跑的宿主
    python3 scripts/probe.py --from-dump /tmp/dom.json   # 离线分析
    python3 scripts/probe.py --port 9333 --dump /tmp/dom.json
"""
import argparse
import importlib.util
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent

# 套组里实际用到的契约钩子（grep sets/*/theme.css 得出的全集），附一句人话解释
HOOKS = {
    "loki-page": "页面根容器",
    "loki-sidebar": "最外层左侧栏",
    "loki-sidebar-head": "侧栏顶部品牌区",
    "loki-nav-group": "侧栏里的一组",
    "loki-nav-group-label": "侧栏分组小标题",
    "loki-nav-group-dot": "分组小标题前的圆点",
    "loki-nav-item": "侧栏一个可点条目",
    "loki-nav-item-active": "侧栏当前选中的那个条目",
    "loki-nav-icon": "侧栏条目里的小图标",
    "loki-brand-mark": "品牌图标位",
    "loki-brand-name": "品牌名",
    "loki-brand-sub": "品牌副标题",
    "loki-chat-sidebar": "会话列表那一栏",
    "loki-conversation-item": "一条会话",
    "loki-conversation-item-active": "当前那条会话",
    "loki-surface": "一层表面（卡片）",
    "loki-surface-strong": "强调表面（主面板）",
    "loki-paper": "内容纸面（正文所在的那张纸）",
    "loki-chat-canvas": "主区画布（消息流外面那层）",
    "loki-chat-stream": "消息流滚动区",
    "loki-bubble-user": "用户消息",
    "loki-bubble-assistant": "助手消息块",
    "loki-composer": "输入区容器",
    "loki-composer-meta": "输入区下方的小字",
    "loki-input": "文本输入框",
    "loki-button-primary": "主按钮",
    "loki-button-secondary": "次要按钮",
    "loki-workbench": "工作台区",
    "loki-workbench-toolbar": "工作台工具条",
    "loki-context-panel": "右侧上下文/依据面板",
    "loki-empty-hero": "空状态大图区",
    "loki-header-sticker": "主区顶部的标题贴纸位",
    "loki-sticker": "贴纸装饰位",
    "loki-sticker-title": "贴纸标题",
    "loki-code-block": "代码块",
    "loki-table": "表格",
    "loki-avatar": "头像",
    "loki-drawer": "抽屉 / 弹层",
    "loki-mascot-frame": "IP 形象的外框（不含形象本身）",
}


# ---------- 小工具 ----------

CLEANUP = """(function () {
  if (window.__LOKI_ROLE_OBSERVER__) { window.__LOKI_ROLE_OBSERVER__.disconnect(); window.__LOKI_ROLE_OBSERVER__ = null; }
  document.querySelectorAll('[data-loki-role]').forEach(function (el) {
    var r = el.getAttribute('data-loki-role');
    el.classList.remove('loki-' + r);
    el.removeAttribute('data-loki-role');
  });
  return 1;
})()"""


def load_collector():
    return (HERE / "collect-dom.js").read_text(encoding="utf-8")


def run_cdp(port, expr, want_url=None):
    spec = importlib.util.spec_from_file_location("inject_cdp", HERE / "inject-cdp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ws, send, page = mod.connect(port, want_url)
    try:
        return mod.evaluate(send, expr), page.get("url", "")
    finally:
        ws.close()


def sanitize(doc, prefix="loki-"):
    """把我们自己挂上去的钩子类名从盘点结果里滤掉。

    为什么必要：挂钩器一旦装在宿主里，它会一直补挂（MutationObserver），
    盘点时必然拍到自己加的类名 —— 候选里就全是回音（`div.coding-cola-agent-session-item.loki-nav-item`）。
    这些类名不是宿主的东西，不该参与判断，所以直接在分析阶段滤掉。"""
    pat = re.compile(r"\." + re.escape(prefix) + r"[a-z0-9-]+")
    for e in doc.get("elements", []):
        parts = [c for c in (e.get("cls") or "").split() if not c.startswith(prefix)]
        e["cls"] = " ".join(parts)
        e["sig"] = e["tag"] + "|" + "|".join(sorted(parts))
        if ">" not in e.get("sel", ""):
            e["sel"] = pat.sub("", e["sel"]) or e["path"]
    return doc


def px(v, default=0.0):
    m = re.match(r"^(-?[\d.]+)", str(v or ""))
    return float(m.group(1)) if m else default


def rgb(c):
    m = re.findall(r"[\d.]+", str(c or ""))
    if len(m) < 3:
        return None
    return tuple(int(float(x)) for x in m[:3])


def alpha(c):
    m = re.findall(r"[\d.]+", str(c or ""))
    return float(m[3]) if len(m) > 3 else 1.0


def lum(c):
    v = rgb(c)
    if v is None:
        return None
    out = []
    for x in v:
        s = x / 255.0
        out.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    la, lb = lum(a), lum(b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def opaque(c):
    return rgb(c) is not None and alpha(c) > 0.7 and rgb(c) != (0, 0, 0)


def area(e):
    return e["r"][2] * e["r"][3]


def parent_path(e):
    parts = e["path"].split(">")
    return ">".join(parts[:-1])


def short(e, n=22):
    t = (e.get("txt") or "").strip()
    return t[:n] + ("…" if len(t) > n else "")


def sig_of_group(items):
    return items[0]["sig"][:40]


# ---------- 盘点 ----------

def groups_by_parent_sig(el):
    g = {}
    for e in el:
        g.setdefault((parent_path(e), e["sig"]), []).append(e)
    return g


def find_repeats(el, min_count=3, hmax=160):
    out = []
    for (ppath, sig), items in groups_by_parent_sig(el).items():
        if len(items) < min_count:
            continue
        h = max(i["r"][3] for i in items)
        if h > hmax or h < 10:
            continue
        items = sorted(items, key=lambda x: x["r"][1])
        out.append({"count": len(items), "h": h, "path": items[0]["path"], "sel": items[0]["sel"],
                    "parent": ppath, "sig": sig, "samples": [short(i) for i in items[:4]],
                    "bg": items[0]["bg"], "x": items[0]["r"][0], "w": items[0]["r"][2],
                    "items": items})
    return sorted(out, key=lambda d: -d["count"])


def find_columns(doc, el):
    """纵向的整列。**不要用 DOM 深度做过滤** —— 真实应用里侧栏常常在十几层里面，
    设个 `d<=9` 会把侧栏筛掉，只剩整个应用根（然后被拿去做候选）。
    改成用几何：够高、够宽，但又不是整页本身。"""
    vp = doc["viewport"]
    page = vp[0] * vp[1]
    cols = [e for e in el
            if e["r"][3] >= vp[1] * 0.5 and e["r"][2] >= 140
            and e["r"][2] * e["r"][3] < page * 0.9]
    cols.sort(key=lambda e: (e["r"][0], -area(e)))
    return cols


def find_scrolls(doc, el):
    vp = doc["viewport"]
    out = [e for e in el
           if (e["se"] or e["ovf"] in ("auto", "scroll"))
           and area(e) >= vp[0] * vp[1] * 0.08]
    out.sort(key=lambda e: -area(e))
    return out


def find_buttons(el):
    out = [e for e in el
           if e["tag"] in ("button",) or e["role"] == "button"
           or (e["cur"] == "pointer" and e["r"][3] <= 64 and e["r"][2] <= 320 and e["own"] > 0)]
    return out


def find_inputs(el):
    return [e for e in el if e["tag"] in ("input", "textarea") or e["role"] == "textbox"
            or e.get("cls", "").find("prose") >= 0]


def find_surfaces(doc, el):
    vp = doc["viewport"]
    out = [e for e in el
           if opaque(e["bg"]) and rgb(e["bg"]) != rgb(e["pbg"])
           and (px(e["rad"]) > 0 or e["sh"])
           and area(e) >= vp[0] * vp[1] * 0.008]
    out.sort(key=lambda e: -area(e))
    return out


def text_scale(el):
    hist = {}
    for e in el:
        if e["own"] < 2:
            continue
        k = e["fs"]
        hist.setdefault(k, []).append(e)
    return sorted(((float(k.rstrip("px") or 0), len(v)) for k, v in hist.items()), reverse=True)


# ---------- 草案 ----------

def propose(doc, el):
    vp = doc["viewport"]
    vh = vp[1]
    props = {}

    def put(hook, selector, why, extra=None):
        if hook in props:
            return
        d = {"hook": hook, "selector": selector, "why": why}
        if extra:
            d.update(extra)
        props[hook] = d

    cols = find_columns(doc, el)
    scrolls = find_scrolls(doc, el)
    repeats = find_repeats(el)
    buttons = find_buttons(el)
    inputs = find_inputs(el)
    surfaces = find_surfaces(doc, el)

    # 最左边的整列 → 侧栏
    # 最左边的整列 → 侧栏。同一组里取**最外层**（高度接近的候选中取深度最小的），
    # 否则会挑到侧栏里面那层列表容器，挂上去的就不是「侧栏」本身。
    def outermost(cands):
        hmax = max(c["r"][3] for c in cands)
        near = [c for c in cands if c["r"][3] >= hmax * 0.98]
        return min(near, key=lambda c: c["d"])

    if cols:
        left = [c for c in cols if c["r"][0] <= vp[0] * 0.04]
        if left:
            side = outermost(left)
            put("loki-sidebar", side["sel"], f"贴着左边缘、高度占满的整列（最外层 {side['r'][2]:.0f}×{side['r'][3]:.0f}）")
        right = [c for c in cols if c["r"][0] + c["r"][2] >= vp[0] * 0.97 and c is not (left[0] if left else None)]
        if len(cols) >= 3 and right:
            panel = outermost(right)
            put("loki-context-panel", panel["sel"], f"最右边那一列（最外层 {panel['r'][2]:.0f}×{panel['r'][3]:.0f}）")

    # 侧栏里的重复行 → 导航项
    side_repeats = [r for r in repeats if r["x"] < vp[0] * 0.35 and 16 <= r["h"] <= 56]
    if side_repeats:
        best = max(side_repeats, key=lambda r: r["count"])
        put("loki-nav-item", best["sel"], f"侧栏里重复出现 {best['count']} 次、高 {best['h']:.0f}px 的行",
            {"count": best["count"], "samples": best["samples"]})
        # 组小标题：侧栏里那些不重复、不可点、字号更小的短文本
        labels = [e for e in el if e["r"][0] < vp[0] * 0.35 and e["own"] > 1 and e["own"] < 14
                  and e["cur"] != "pointer" and px(e["fs"]) <= 12 and e["r"][3] <= 26 and e["r"][1] > 0]
        if labels:
            put("loki-nav-group-label", labels[0]["sel"], "侧栏里的短小标签（多半是分组名）")

    # 最大的滚动区 → 消息流
    if scrolls:
        put("loki-chat-stream", scrolls[0]["sel"], "面积最大的可滚动区",
            {"w": scrolls[0]["r"][2], "h": scrolls[0]["r"][3], "kids": scrolls[0]["kids"]})

    # 消息流里的重复块 → 气泡
    stream = scrolls[0] if scrolls else None
    if stream:
        inside = [r for r in repeats if r["x"] >= vp[0] * 0.1 and r["w"] >= vp[0] * 0.3]
        if inside:
            b = max(inside, key=lambda r: r["count"])
            put("loki-bubble-assistant", b["sel"], f"主区里重复 {b['count']} 次的宽块",
                {"count": b["count"], "samples": b["samples"]})

    # 输入
    if inputs:
        i = max(inputs, key=lambda e: area(e))
        put("loki-input", i["sel"], f"<{i['tag']}> 输入框",
            {"w": i["r"][2], "h": i["r"][3]})

    # 按钮：按底色分成主/次
    if buttons:
        page_bg = None
        for e in el:
            if e["path"] == "html>body" or (e["r"][0] <= 1 and e["r"][1] <= 1 and area(e) > vp[0] * vh * 0.9):
                page_bg = e["bg"]
                break
        page_bg = page_bg or (el[0]["pbg"] if el else "rgb(255,255,255)")
        strong = [b for b in buttons if opaque(b["bg"]) and (contrast(b["bg"], page_bg) or 1) > 1.6]
        weak = [b for b in buttons if b not in strong]
        if strong:
            s = max(strong, key=lambda e: e["r"][2] * e["r"][3])
            put("loki-button-primary", s["sel"], f"底色明显区别于页面背景的按钮（对页面对比 {contrast(s['bg'], page_bg)}:1）",
                {"count": len(strong)})
        if weak:
            w = max(weak, key=lambda e: e["r"][2] * e["r"][3])
            put("loki-button-secondary", w["sel"], "底色接近背景 / 只有描边的按钮",
                {"count": len(weak)})

    # 代码块
    pres = [e for e in el if e["tag"] == "pre"]
    if pres:
        put("loki-code-block", "pre", "已经是 <pre>，直接可用")

    # 表格
    if any(e["tag"] == "table" for e in el):
        put("loki-table", "table", "<table> 已是语义元素")

    # 表面
    if surfaces:
        s = surfaces[0]
        put("loki-surface-strong", s["sel"], f"面积最大的独立表面（{s['r'][2]:.0f}×{s['r'][3]:.0f}，圆角 {s['rad']}）")
    return props


# ---------- 输出 ----------

def hr(t=""):
    print("\n" + ("─" * 68 if not t else f"\n▌{t}\n" + "─" * 68))


def report(doc, el, props):
    vp = doc["viewport"]
    print(f"宿主：{doc['title'] or '(无标题)'}")
    print(f"      {doc['url']}")
    print(f"      视口 {vp[0]}×{vp[1]}  元素总数 {doc['total']}（抓到 {len(el)}，丢弃 {doc['dropped']}）")
    print(f"      html class={doc['htmlCls']!r} 属性 {doc['htmlAttrs']}")

    hr("整列（候选：侧栏 / 画布 / 右栏）")
    for c in find_columns(doc, el)[:8]:
        print(f"  {c['r'][2]:>5.0f}×{c['r'][3]:<5.0f} @x={c['r'][0]:<5.0f} bg={c['bg']:<22} kids={c['kids']:<3} {c['path']}")

    hr("可滚动区（候选：消息流 / 工作台）")
    for c in find_scrolls(doc, el)[:8]:
        print(f"  {c['r'][2]:>5.0f}×{c['r'][3]:<5.0f} @y={c['r'][1]:<5.0f} ovf={c['ovf']:<7} se={c['se']} kids={c['kids']:<3} {c['path']}")

    hr("重复出现的行（候选：导航项 / 会话项 / 消息）")
    for r in find_repeats(el)[:12]:
        print(f"  ×{r['count']:<3} h={r['h']:<4.0f} x={r['x']:<5.0f} w={r['w']:<5.0f} {r['path']}")
        print(f"       样本：{r['samples']}")

    hr("按钮 / 输入 / 代码块")
    bs = find_buttons(el)
    print(f"  按钮候选 {len(bs)} 个：")
    for b in bs[:10]:
        print(f"    {b['r'][2]:>4.0f}×{b['r'][3]:<4.0f} bg={b['bg']:<22} rad={b['rad']:<6} 「{short(b, 14)}」 {b['path']}")
    for i in find_inputs(el)[:6]:
        print(f"  输入：<{i['tag']}> {i['r'][2]:.0f}×{i['r'][3]:.0f} place={i.get('aria')!r} {i['path']}")
    for p in [e for e in el if e["tag"] == "pre"][:4]:
        print(f"  代码块：{p['r'][2]:.0f}×{p['r'][3]:.0f} {p['path']}")

    hr("字号分布（看清文字层级）")
    for fs, n in text_scale(el)[:10]:
        print(f"  {fs:>5.1f}px  ×{n}")

    hr("草案：角色 → 候选选择器")
    if not props:
        print("  没认出任何角色 —— 这个宿主的 DOM 可能太扁平，需要手写 binding.json")
    for hook in HOOKS:
        if hook not in props:
            continue
        p = props[hook]
        print(f"  {hook:<28} {p['selector']}")
        print(f"      └ {p['why']}" + (f"　(payload={ {k: v for k, v in p.items() if k not in ('hook', 'selector', 'why')} })" if len(p) > 3 else ""))
    missing = [h for h in HOOKS if h not in props]
    print(f"\n  认出 {len(props)} / {len(HOOKS)} 个钩子位置；没认出的：")
    print("    " + ", ".join(missing))
    print("\n  ⚠ 这是**草案**，不是定稿。请人工核一遍上面每条：认错了要改，认不出的可以手写。")
    print("    定稿写进 adapters/<宿主>/binding.json，然后 `adapt.py --check` 会逐条实测。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, help="正在跑的宿主调试端口（CDP）")
    ap.add_argument("--url-match", help="只在 URL 含该串的页面上跑")
    ap.add_argument("--from-dump", help="离线分析已有的 dump JSON")
    ap.add_argument("--dump", help="把抓到的原始盘点写到这个文件")
    ap.add_argument("--json", action="store_true", help="只输出 JSON 草案")
    args = ap.parse_args()

    if args.from_dump:
        doc = json.loads(pathlib.Path(args.from_dump).read_text(encoding="utf-8"))
    elif args.port:
        # 盘点前先把**我们自己挂的钩子摘掉**，否则会把 `loki-nav-group` 这类自己加的类名
        # 当成宿主自己的类，候选里就全是回音（真踩过）。
        run_cdp(args.port, CLEANUP, args.url_match)
        try:
            doc, _ = run_cdp(args.port, load_collector(), args.url_match)
        except Exception as e:
            print(f"抓盘点失败：{e}", file=sys.stderr)
            return 2
    else:
        print("要么给 --port，要么给 --from-dump", file=sys.stderr)
        return 2

    if isinstance(doc, str):
        print("页面返回了字符串而不是对象，检查 collect-dom.js 是不是 IIFE", file=sys.stderr)
        return 2
    doc = sanitize(doc)
    el = doc.get("elements", [])
    props = propose(doc, el)

    if args.dump:
        pathlib.Path(args.dump).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        print(f"原始盘点已写入 {args.dump}（{len(el)} 条）")

    if args.json:
        print(json.dumps(props, ensure_ascii=False, indent=2))
    else:
        report(doc, el, props)
    return 0


if __name__ == "__main__":
    sys.exit(main())
