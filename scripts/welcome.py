#!/usr/bin/env python3
"""装完自动弹给用户看的那一页（自包含 HTML，零外链、零图片、零依赖）。

为什么要有它：用户装完只看到"颜色变了"，他不会去翻 README，更不会去看
`references/after-install.md`。所以**装完直接把这一页弹出来**，一次把话说全：
现在能用什么、还想要什么该说哪句话、重启升级会不会掉、想自己做怎么办、不想要了怎么办。

文字内容来自 `references/after-install.md` 里 USER-FACING 那一段（单一来源），
这里只负责渲染成一个能看的页面 —— 改文档，页面跟着变，不会两处说不一样的话。

    python3 scripts/welcome.py --out /tmp/给你的用户.html --sets 35
    python3 scripts/welcome.py --out … --sets 35 --open      # 顺手用浏览器打开
"""
import argparse
import html
import pathlib
import re
import sys
import webbrowser

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
SOURCE = SKILL / "references" / "after-install.md"


# ---------- 取内容 ----------

def user_facing_markdown(count=None):
    if not SOURCE.exists():
        return "# 外观已经装好了\n\n（references/after-install.md 不在了）\n"
    text = SOURCE.read_text(encoding="utf-8")
    m = re.search(r"<!-- USER-FACING-START -->(.*?)<!-- USER-FACING-END -->", text, re.S)
    body = (m.group(1).strip() if m else text.strip())
    if count:
        body = (body.replace("现在有 35 套外观主题", f"现在有 {count} 套外观主题")
                    .replace("30 多套随便切", f"{count} 套随便切")
                    .replace("35 套全是纯 CSS", f"{count} 套全是纯 CSS"))
    return body


# ---------- 极简 Markdown → HTML（只支持这一段用到的语法） ----------

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_to_html(md):
    out, i = [], 0
    lines = md.split("\n")
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 表格
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>")
            for r in body:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            lv = len(m.group(1))
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
            i += 1
            continue

        # 分隔线
        if re.match(r"^-{3,}$", stripped):
            out.append("<hr>")
            i += 1
            continue

        # 引用块
        if stripped.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append('<blockquote>' + "<br>".join(inline(b) for b in buf) + "</blockquote>")
            continue

        # 代码块
        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            continue

        # 列表
        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            ordered = bool(re.match(r"^\d+\.\s+", stripped))
            items = []
            while i < len(lines) and (re.match(r"^\s*[-*]\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i])):
                items.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", lines[i]).strip())
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>" for t in items) + f"</{tag}>")
            continue

        # 段落
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^\s*(#{1,4}\s|[-*]\s|\d+\.\s|>|\||```|-{3,}$)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append(f"<p>{inline(' '.join(buf))}</p>")
        else:
            i += 1
    return "\n".join(out)


# ---------- 页面 ----------

CSS = """
:root { --bg:#efe9dd; --paper:#f7f3e9; --ink:#3a352e; --muted:#6b6355; --line:#d8cfba; --accent:#8a5a2b; }
* { box-sizing:border-box; }
body { margin:0; padding:40px 20px 80px; background:var(--bg); color:var(--ink);
  font:16px/1.85 "Iowan Old Style","Songti SC","STSong",Georgia,"PingFang SC",serif; }
.wrap { max-width:820px; margin:0 auto; background:var(--paper); border:1px solid var(--line);
  border-radius:14px; padding:36px 44px 44px; box-shadow:0 1px 0 rgba(0,0,0,.04), 0 18px 40px -32px rgba(60,50,30,.5); }
h1 { font-size:26px; line-height:1.35; margin:0 0 6px; letter-spacing:.01em; }
h2 { font-size:19px; margin:34px 0 10px; padding-top:16px; border-top:1px solid var(--line); }
h3 { font-size:16px; margin:22px 0 8px; }
p, li { margin:9px 0; }
strong { color:#2b2620; }
code { background:#ece5d4; border:1px solid var(--line); border-radius:5px; padding:1px 5px;
  font:13px/1.6 "SF Mono",Menlo,Consolas,monospace; }
pre { background:#ece5d4; border:1px solid var(--line); border-radius:8px; padding:12px 14px; overflow-x:auto; }
pre code { background:none; border:0; padding:0; }
table { border-collapse:collapse; width:100%; margin:14px 0; font-size:14.5px; }
th, td { border:1px solid var(--line); padding:9px 11px; text-align:left; vertical-align:top; }
th { background:#e9e1ce; font-weight:600; }
blockquote { margin:14px 0; padding:12px 16px; background:#f1ead8; border-left:3px solid var(--accent);
  border-radius:0 8px 8px 0; }
hr { border:0; border-top:1px solid var(--line); margin:28px 0; }
a { color:var(--accent); }
.foot { margin-top:34px; padding-top:16px; border-top:1px solid var(--line); color:var(--muted);
  font-size:13px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#14120f; --paper:#1c1916; --ink:#e6ddca; --muted:#a19684; --line:#3a3429; --accent:#d0a267; }
  strong { color:#f2ead8; }
  code, pre { background:#241f19; }
  th { background:#241f19; }
  blockquote { background:#221d17; }
}
"""


def render(count=None, title=None):
    md = user_facing_markdown(count)
    body = md_to_html(md)
    head = title or (f"外观装好了{('：' + str(count) + ' 套') if count else ''}")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(head)}</title>
<style>{CSS}</style>
</head><body><div class="wrap">
{body}
<div class="foot"><span>Loki 外观套组工坊 · 作者 Loki</span><span>关掉这一页就行，它不影响任何东西</span></div>
</div></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="写到这个路径（.html）")
    ap.add_argument("--sets", type=int, help="实际装了几套（写进正文）")
    ap.add_argument("--open", action="store_true", help="写完用默认浏览器打开")
    ap.add_argument("--html", action="store_true", help="直接把 HTML 打到标准输出")
    args = ap.parse_args()

    page = render(args.sets)
    if args.html or not args.out:
        print(page)
        return 0
    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(page, encoding="utf-8")
    print(f"装完提示页：{p}")
    if args.open:
        webbrowser.open("file://" + str(p.resolve()))
        print("（已用浏览器打开）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
