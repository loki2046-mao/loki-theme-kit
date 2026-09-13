#!/usr/bin/env python3
"""CDP 注入器：给「已经在跑的 Electron / Chromium 宿主」接上外观套组。

为什么需要它：`auto.py` 是给能改源码的项目用的；但有些宿主（打包好的桌面 App）
源码你改不了，只能从外面注入。这类宿主的接法是：

    python3 scripts/inject-cdp.py --port 9333 --css out/loki-themes.css --js out/loki-themes.js
    python3 scripts/inject-cdp.py --port 9333 --eval "document.documentElement.dataset.theme"
    python3 scripts/inject-cdp.py --port 9333 --shot /tmp/cola.png

宿主必须先带调试端口启动（Electron 加 `--remote-debugging-port=9333 --remote-allow-origins=*`）。
它只做三件事：往页面塞一个 <style>、可选塞一段脚本、可选截图。不落盘、不改宿主安装包。
不想要了：重启宿主，或在页面里 `document.getElementById('loki-theme-kit-styles').remove()`。
"""
import argparse
import base64
import json
import sys
import time
import urllib.request

try:
    import websocket  # websocket-client
except ImportError:
    print("需要 websocket-client：pip install websocket-client", file=sys.stderr)
    sys.exit(2)


def connect(port, want_url=None):
    for _ in range(20):
        try:
            targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2))
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError(f"CDP 连不上：127.0.0.1:{port}（宿主没带 --remote-debugging-port 启动？）")
    pages = [t for t in targets if t.get("type") == "page"]
    if want_url:
        pages = [p for p in pages if want_url in (p.get("url") or "")] or pages
    if not pages:
        raise RuntimeError("没有可用的 page target")
    ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=60)
    state = {"id": 0}

    def send(method, params=None):
        state["id"] += 1
        ws.send(json.dumps({"id": state["id"], "method": method, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == state["id"]:
                return msg

    return ws, send, pages[0]


def evaluate(send, expr):
    r = send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
    res = r.get("result", {})
    if res.get("exceptionDetails"):
        return {"error": res["exceptionDetails"].get("text"), "detail": str(res["exceptionDetails"])[:300]}
    return res.get("result", {}).get("value")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--css", help="要注入的 CSS 文件")
    ap.add_argument("--js", help="要注入的 JS 文件（可选）")
    ap.add_argument("--eval", dest="expr", help="只跑一段表达式并打印结果")
    ap.add_argument("--shot", help="截图保存到该路径")
    ap.add_argument("--style-id", default="loki-theme-kit-styles")
    ap.add_argument("--keep-other-styles", action="store_true",
                    help="不清掉上一次注入的同 id style（默认先清再写，保证幂等）")
    args = ap.parse_args()

    ws, send, page = connect(args.port)
    print(f"连接：{page.get('title', '')} · {(page.get('url') or '')[:70]}")

    try:
        if args.expr:
            out = evaluate(send, args.expr)
            print(json.dumps(out, ensure_ascii=False, indent=2) if not isinstance(out, str) else out)
            return 0

        if args.css:
            css = open(args.css, encoding="utf-8").read()
            clear = "" if args.keep_other_styles else \
                f"document.getElementById({json.dumps(args.style_id)})?.remove();"
            expr = (clear + "(() => { const s = document.createElement('style'); s.id = "
                    + json.dumps(args.style_id) + "; s.textContent = " + json.dumps(css)
                    + "; document.head.appendChild(s); return 'css ' + s.textContent.length + ' chars'; })()")
            print("注入 CSS：", evaluate(send, expr))

        if args.js:
            js = open(args.js, encoding="utf-8").read()
            expr = ("(() => { try { " + js + " ; return 'js ok'; } catch (e) { return 'js err: ' + e.message; } })()")
            print("注入 JS：", evaluate(send, expr))

        time.sleep(1.5)
        if args.shot:
            shot = send("Page.captureScreenshot", {"format": "png"})
            open(args.shot, "wb").write(base64.b64decode(shot["result"]["data"]))
            print("截图：", args.shot)
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
