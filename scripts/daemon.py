#!/usr/bin/env python3
"""外观守护：让「打开宿主就是你的外观」，不用每次叫 Agent。

背景：改不了源码的宿主（打包好的桌面 App）只能运行时注入，**一重启就掉**。
`profile.py restore` 能拿回来，但那要用户想起来跟 Agent 说一句。这个守护进程
把这一步也省了：

    宿主起来了 → 端口在 → 页面里没有我们的标记 → 自动把那套外观注入回去。

由 LaunchAgent 常驻（`profile.py autostart --on`），退出登录也停机。

三条纪律：
  1. **只注入，不接管宿主**。宿主没带调试端口时默认什么都不做（要它去重启宿主，
     得显式开 `--takeover`，那是碰用户 App 的行为，必须先得到同意）。
  2. **不抢别人家的皮肤系统**。我们的载荷自己会读宿主的存储键：用户选的要是宿主自带
     的皮肤，我们只把自己注册进面板，不去改他选的那套。宿主自己的守护进程看到
     页面上已经打了标记也会自动让位。
  3. **幂等**。已经在位就什么都不做；清单变了才重注一次（接入包里有代际接管，
     重注不会留下旧一代的残留）。

    python3 scripts/daemon.py --once            # 跑一轮就退出（自检用）
    python3 scripts/daemon.py                   # 常驻（默认 5 秒一轮）
    python3 scripts/daemon.py --log -           # 日志打到标准输出
"""
import argparse
import fcntl
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path.home() / ".loki-theme-kit"
PROFILES = HOME / "profiles"
PORT_HINTS = [9333, 9222, 9223, 9229, 9224]
TAKEOVER_WINDOW = 40        # 无端口实例启动后多少秒内允许接管（只在使用 --takeover 时）
TAKEOVER_COOLDOWN = 120
_last_takeover = 0.0

DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def log(msg, path):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if path and path != "-":
        try:
            p = pathlib.Path(path)
            if p.exists() and p.stat().st_size > 1_000_000:
                p.replace(p.with_suffix(".log.1"))
            with p.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def port_ready(port, timeout=1.5):
    try:
        with DIRECT.open(f"http://127.0.0.1:{port}/json", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def find_port(stored):
    if stored and port_ready(stored):
        return stored
    for p in PORT_HINTS:
        if p != stored and port_ready(p):
            return p
    return None


def eval_js(port, expr, timeout=10):
    try:
        import websocket
    except ImportError:
        return None
    try:
        with DIRECT.open(f"http://127.0.0.1:{port}/json", timeout=4) as r:
            targets = json.load(r)
        pages = [t for t in targets if t.get("type") == "page"]
        if not pages:
            return None
        ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=timeout)
        try:
            ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                "params": {"expression": expr, "returnByValue": True,
                                           "awaitPromise": True}}))
            while True:
                m = json.loads(ws.recv())
                if m.get("id") == 1:
                    return m.get("result", {}).get("result", {}).get("value")
        finally:
            ws.close()
    except Exception:
        return None


def inject_file(port, path, style_id=None):
    if not path.exists():
        return False
    # 用当前解释器，不要写 "python3" —— LaunchAgent 里的 PATH 很干净，
    # `python3` 可能解析不到（尤其是 websocket 装在家目录那套 Python 上的时候）
    cmd = [sys.executable, str(HERE / "inject-cdp.py"), "--port", str(port), "--js", str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def profiles(only=None):
    if not PROFILES.exists():
        return []
    out = []
    for d in sorted(PROFILES.iterdir()):
        f = d / "profile.json"
        if not f.exists():
            continue
        p = json.loads(f.read_text(encoding="utf-8"))
        if p.get("kind") != "inject":
            continue
        if only and p["name"] not in only:
            continue
        p["_dir"] = d
        out.append(p)
    return out


def payload_sets(prof):
    """载荷里到底带了几套 —— 用来判断「档案改过没有」。"""
    js = prof["_dir"] / "payload" / "loki-themes.js"
    if not js.exists():
        return None
    text = js.read_text(encoding="utf-8", errors="ignore")
    if "data-loki-theme-id" not in text:
        return None
    # 生成的包里主题表是 JSON：{"id": "loki-ease", ...}。
    # 注意键是**带引号**的，写成 id:\s*" 会一个都匹配不到（真踩过，白等了一轮）。
    ids = re.findall(r'"id":\s*"([a-z0-9-]+)"', text)
    return sorted(set(ids)) or None


def check_and_inject(prof, do_takeover, logpath, dry=False):
    name = prof["name"]
    port = find_port(prof.get("port"))
    if not port:
        if do_takeover:
            return maybe_takeover(prof, logpath)
        return "port-down"
    attr = prof.get("attr") or "data-cola-skin"
    storage_key = prof.get("storageKey") or "cola-skin-selected"
    state = eval_js(port, """(function () {
      var stored = null; try { stored = localStorage.getItem(%s); } catch (e) {}
      return {
        ready: document.readyState === 'complete',
        marker: !!document.getElementById('loki-theme-kit-styles'),
        gen: (window.__LOKI_THEME_KIT__ && window.__LOKI_THEME_KIT__.gen) || 0,
        sets: (window.__LOKI_THEME_KIT__ && window.__LOKI_THEME_KIT__.sets) || null,
        stored: stored,
        hostSkin: !!document.getElementById('cola-skin-inject'),
        current: document.documentElement.getAttribute(%s)
      };
    })()""" % (json.dumps(storage_key), json.dumps(attr)))
    if not state or not state.get("ready"):
        return "not-ready"

    want = payload_sets(prof)
    # 让位握手：用户现在选的是**宿主自带**的皮肤，而宿主那套样式还没进页面 ——
    # 先等宿主自己的守护进程把它注进去（它看到 html 上没有皮肤属性才会动手；
    # 我们要是抢先把标记打上，它就不管了，用户会看到一套没有样式的皮肤）。
    if want and state.get("stored") and state["stored"] not in want and not state.get("hostSkin"):
        return "yield-to-host"
    if state.get("marker") and state.get("sets") and (want is None or sorted(state["sets"]) == want):
        return "ok"
    if dry:
        return "would-inject"

    reason = "页面里没有我们的外观" if not state.get("marker") else "档案的清单变了"
    time.sleep(1.0)          # 等宿主渲染稳定（刚起来时 DOM 还在变）
    inject_file(port, prof["_dir"] / "payload" / "loki-themes.js")
    inject_file(port, prof["_dir"] / "payload" / "loki-roles.js")
    # 用户现在选的那套被从清单里剪掉了（比如把 35 套剪成 3 套，而那 3 套里没有它）：
    # 不处理的话界面会**掉样式**（那套的 CSS 已经不在包里了）。落到清单里的第一套。
    cur = state.get("current")
    if want and cur and cur not in want and cur in (state.get("sets") or []):
        fallback = want[0]
        eval_js(port, "(function(){try{localStorage.setItem(%s, %s);}catch(e){}"
                      "document.documentElement.setAttribute(%s, %s);return 1;})()"
                % (json.dumps(storage_key), json.dumps(fallback), json.dumps(attr), json.dumps(fallback)))
        log(f"{name}：当前选的 {cur} 已经不在清单里了 → 换成清单里的第一套 {fallback}（否则界面会掉样式）", logpath)

    back = eval_js(port, "({m: !!document.getElementById('loki-theme-kit-styles'),"
                         "n: document.querySelectorAll('[data-loki-theme-id]').length,"
                         "h: document.querySelectorAll('[data-loki-role]').length,"
                         "c: document.documentElement.getAttribute(%s)})" % json.dumps(attr))
    log(f"{name}：{reason} → 已注入（样式 {back.get('m') if back else '?'}　"
        f"面板 {back.get('n') if back else '?'} 套　结构件挂钩 {back.get('h') if back else '?'} 个　"
        f"当前 {back.get('c') if back else '?'}）", logpath)
    return "injected"


def maybe_takeover(prof, logpath):
    """宿主没带调试端口 → 退出并用端口重启它。**默认不开**，碰用户 App 要有明确同意。"""
    global _last_takeover
    if time.monotonic() - _last_takeover < TAKEOVER_COOLDOWN:
        return "takeover-cooling"
    app = prof.get("app_path")
    if not app or not pathlib.Path(app).exists():
        return "no-app"
    stem = pathlib.Path(app).stem
    r = subprocess.run(["pgrep", "-x", stem], capture_output=True, text=True)
    pids = [p for p in r.stdout.split() if p]
    if not pids:
        return "port-down"
    for pid in pids:
        cmd = subprocess.run(["ps", "-p", pid, "-o", "command="], capture_output=True, text=True).stdout
        if "--remote-debugging-port" in cmd:
            return "waiting-port"
        et = subprocess.run(["ps", "-p", pid, "-o", "etime="], capture_output=True, text=True).stdout.strip()
        secs = 0
        try:
            parts = et.split(":")
            secs = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except Exception:
            secs = 0
        if secs and secs > TAKEOVER_WINDOW:
            return "plain-host-old"
        _last_takeover = time.monotonic()
        log(f"{prof['name']}：宿主没带调试端口，按 --takeover 重启它（{stem}）", logpath)
        subprocess.run(["osascript", "-e", f'tell application "{stem}" to quit'], timeout=15)
        time.sleep(3)
        subprocess.Popen([app + "/Contents/MacOS/" + stem, "--remote-debugging-port=" + str(prof.get("port") or 9333),
                          "--remote-allow-origins=*"])
        return "takeover-done"
    return "port-down"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--once", action="store_true", help="跑一轮就退出（自检）")
    ap.add_argument("--dry-run", action="store_true", help="只看要不要注入，不动手")
    ap.add_argument("--profile", action="append", help="只守这个档案（可重复）")
    ap.add_argument("--takeover", action="store_true",
                    help="宿主没带调试端口时退出并用端口重启它（碰用户 App，默认关）")
    ap.add_argument("--log", default=str(HOME / "daemon.log"))
    args = ap.parse_args()

    HOME.mkdir(parents=True, exist_ok=True)
    lock_path = HOME / "daemon.pid"
    lock = lock_path.open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("已经有一个守护进程在跑了（同一把锁）", file=sys.stderr)
        return 1
    lock.write(str(os.getpid()))
    lock.flush()

    log(f"外观守护启动：{len(profiles(args.profile))} 个档案｜{args.interval}s 一轮"
        f"｜接管 {'开' if args.takeover else '关'}", args.log)
    idle = 0
    while True:
        ps = profiles(args.profile)
        if not ps:
            log("没有注入型档案可守（先在 profile.py save 存一个）", args.log)
        for prof in ps:
            try:
                r = check_and_inject(prof, args.takeover, args.log, args.dry_run)
            except Exception as e:
                log(f"{prof['name']}：出错 {e}", args.log)
                r = "error"
            if r not in ("ok", "port-down", "not-ready", "waiting-port", "yield-to-host", "plain-host-old"):
                idle = 0
            else:
                idle += 1
        if args.once:
            return 0
        if idle and idle % 720 == 0:      # 每小时留一条心跳，方便看它还活着
            log(f"心跳：一切都在位（第 {idle} 次巡检）", args.log)
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
