#!/usr/bin/env python3
"""外观档案：把「这个宿主现在长什么样」存下来，重启 / 升级之后一句话拿回来。

为什么需要它：改不了源码的宿主（打包好的桌面 App）只能**运行时注入** —— 重启就没了。
源码型宿主虽然写在代码里，但项目一升级、依赖一重装，也可能被冲掉。

所以这里把「这次装了什么」存成一份**档案**：主题清单 + 注入载荷 + 这个宿主的角色对照表。
之后不管是重启、升级、还是换了台机器，**用户只需要对 Agent 说一句话**
（"把外观恢复回来"），Agent 跑一条 restore 即可 —— 不需要用户开终端粘任何东西。

    python3 scripts/profile.py save    --name cola --port 9333 --adapter cola
    python3 scripts/profile.py restore --name cola          # ← Agent 只需要跑这一条
    python3 scripts/profile.py list
    python3 scripts/profile.py sets    --name cola --only loki-ease,loki-pop   # 只要这几套
    python3 scripts/profile.py drop    --name cola

档案位置：~/.loki-theme-kit/profiles/<名字>/
    profile.json          这次装了什么（宿主类型、主题清单、适配器、入口）
    payload/*.css|*.js    当时注入的完整载荷（原样拿回来，不重算）
    binding.json          这个宿主的角色对照表快照（结构件那一层）
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
HOME = pathlib.Path.home() / ".loki-theme-kit" / "profiles"

PORT_HINTS = [9333, 9222, 9223, 9229, 9224]


# ---------- 小工具 ----------

def hr(t=""):
    print("\n" + (f"▌{t}" if t else "") + ("\n" + "─" * 66 if t else ""))


def port_alive(port, timeout=1.0):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def page_url(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as r:
            for t in json.load(r):
                if t.get("type") == "page":
                    return t.get("url") or ""
    except Exception:
        pass
    return ""


def find_port(stored=None):
    """先试存档里的端口，再扫几个常见端口。"""
    if stored and port_alive(stored):
        return stored, ""
    for p in PORT_HINTS:
        if p != stored and port_alive(p):
            return p, f"存档里记的是 {stored}，但它在 {p} 上 —— 用它"
    return None, ""


def app_from_url(url):
    m = re.search(r"file://(/Applications/[^/]+\.app)", url or "")
    return m.group(1) if m else ""


def run(cmd, quiet=False):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    if not quiet and r.stdout.strip():
        print(r.stdout.rstrip())
    if r.returncode != 0 and r.stderr.strip():
        print(r.stderr.rstrip(), file=sys.stderr)
    return r


def _adapter_attr(adapter):
    """主题名写在哪个属性上：适配器说了算（Cola 是 data-cola-skin），否则 data-theme。"""
    if adapter:
        f = ROOT / "adapters" / adapter / "adapter.json"
        if f.exists():
            spec = json.loads(f.read_text(encoding="utf-8"))
            return (spec.get("install") or {}).get("attr") or "data-theme"
    return "data-theme"


def _adapter_storage_key(adapter):
    if adapter:
        f = ROOT / "adapters" / adapter / "adapter.json"
        if f.exists():
            spec = json.loads(f.read_text(encoding="utf-8"))
            return (spec.get("install") or {}).get("storageKey") or ""
    return ""


PLIST = pathlib.Path.home() / "Library" / "LaunchAgents" / "com.loki.theme-kit.restore.plist"
AGENT = "com.loki.theme-kit.restore"


def cmd_autostart(args):
    """开机自动恢复：装 / 卸 / 看状态。"""
    if args.status:
        hr("开机自动恢复状态")
        r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        line = [l for l in r.stdout.splitlines() if AGENT in l]
        print(f"  LaunchAgent：{'已加载　' + line[0].strip() if line else '未加载'}")
        print(f"  配置：{'在　' + str(PLIST) if PLIST.exists() else '不在'}")
        log = pathlib.Path("/tmp/loki-theme-kit-daemon.log")
        if log.exists():
            print("\n  最近日志：")
            for l in log.read_text(encoding="utf-8", errors="ignore").splitlines()[-6:]:
                print("    " + l)
        return 0

    if args.off:
        hr("关掉开机自动恢复")
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{AGENT}"], capture_output=True)
        subprocess.run(["launchctl", "unload", "-w", str(PLIST)], capture_output=True)
        if PLIST.exists():
            trash = pathlib.Path.home() / ".Trash" / f"loki-theme-kit-restore-{time.strftime('%Y%m%d-%H%M%S')}.plist"
            shutil.move(str(PLIST), str(trash))
            print(f"  配置已移到废纸篓（可恢复）：{trash}")
        print("  守护进程已停。已经注入的外观会留到宿主下次重启为止。")
        return 0

    # 装
    py = sys.executable
    if not str(py).startswith("/opt/homebrew"):
        cand = pathlib.Path("/opt/homebrew/bin/python3")
        if cand.exists():
            py = cand
    script = HERE / "daemon.py"
    argv = [str(py), str(script), "--interval", "5"]
    if args.takeover:
        argv.append("--takeover")
    body = "\n".join(f"    <string>{a}</string>" for a in argv)
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{AGENT}</string>
    <key>ProgramArguments</key>
    <array>
{body}
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>ProcessType</key><string>Background</string>
    <key>StandardOutPath</key><string>/tmp/loki-theme-kit-daemon.log</string>
    <key>StandardErrorPath</key><string>/tmp/loki-theme-kit-daemon.err</string>
</dict>
</plist>
"""
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    if PLIST.exists():
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{AGENT}"], capture_output=True)
        subprocess.run(["launchctl", "unload", "-w", str(PLIST)], capture_output=True)
    PLIST.write_text(plist, encoding="utf-8")

    hr("装开机自动恢复")
    r = subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(PLIST)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        r2 = subprocess.run(["launchctl", "load", "-w", str(PLIST)], capture_output=True, text=True)
        if r2.returncode != 0:
            print("  ✗ 加载失败：" + (r.stderr or r2.stderr).strip()[:200], file=sys.stderr)
            return 3
    time.sleep(2)
    lst = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    ok = AGENT in lst
    print(f"  配置：{PLIST}")
    print(f"  加载：{'✓ 已常驻' if ok else '✗ 没起来，看看 /tmp/loki-theme-kit-daemon.err'}")
    print(f"  守护：{py} daemon.py（每 {argv[3]} 秒一轮）"
          + ("　含接管宿主" if args.takeover else "　不接管宿主（只在宿主带调试端口时注入）"))
    log = pathlib.Path("/tmp/loki-theme-kit-daemon.log")
    if log.exists():
        tail = [l for l in log.read_text(encoding="utf-8", errors="ignore").splitlines()[-3:]]
        for l in tail:
            print("    " + l)
    print("\n  以后：打开宿主就有外观，不用叫 Agent。")
    print("  关掉：profile.py autostart --off　｜　看状态：profile.py autostart --status")
    return 0


def profile_dir(name):
    return HOME / name


def load_profile(name):
    p = profile_dir(name) / "profile.json"
    if not p.exists():
        print(f"没有这个档案：{name}（在 {HOME} 里找找）", file=sys.stderr)
        sys.exit(2)
    return json.loads(p.read_text(encoding="utf-8"))


def save_profile(name, data):
    d = profile_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "profile.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------- 打包 ----------

def build_payload(name, sets="all", adapter="cola", out=None):
    d = out or (profile_dir(name) / "payload")
    d.mkdir(parents=True, exist_ok=True)
    cmd = ["bundle.py", "--out", str(d), "--name", "loki-themes", "--quiet"]
    if sets == "all":
        cmd.append("--all")
    elif sets == "recommended":
        cmd.append("--recommended")
    else:
        cmd += ["--only", sets]
    if adapter:
        cmd += ["--adapter", adapter]
    r = run([str(HERE / cmd[0])] + cmd[1:], quiet=True)
    if r.returncode != 0:
        print("打包失败：\n" + (r.stdout + r.stderr)[-800:], file=sys.stderr)
        sys.exit(1)
    css, js = d / "loki-themes.css", d / "loki-themes.js"
    if not css.exists():
        print("打包产物不完整", file=sys.stderr)
        sys.exit(1)
    return d


def render_roles(name):
    """按最新对照表渲染挂钩器（宿主升级后 refresh 的成果能跟着回来）。"""
    b = ROOT / "adapters" / name / "binding.json"
    if not b.exists():
        b = None
    import importlib.util
    spec = importlib.util.spec_from_file_location("adapt", HERE / "adapt.py")
    A = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(A)
    host = name if b else None
    if not host:
        return None
    binding = A.load_binding(host)
    d = profile_dir(name) / "payload"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "loki-roles.js"
    p.write_text(A.render_js(binding), encoding="utf-8")
    shutil.copy(b, profile_dir(name) / "binding.json")
    return p


# ---------- 子命令 ----------

def cmd_save(args):
    name = args.name
    d = profile_dir(name)
    port = args.port
    if port and not port_alive(port):
        print(f"⚠ {port} 上没有活着的宿主，先存清单不存端口")
        port = None
    url = page_url(port) if port else ""
    app = args.app or app_from_url(url)

    payload = build_payload(name, args.sets, args.adapter)
    binding = render_roles(name) if args.adapter else None
    if binding is None:
        # 没有适配器的宿主：挂钩器就是空的，写个空壳免得 restore 时找不到文件
        (payload / "loki-roles.js").write_text("/* 这个宿主没有结构件适配（只搬颜色） */\n", encoding="utf-8")

    sets = sorted(p.name for p in (ROOT / "sets").iterdir() if p.is_dir())
    data = {
        "name": name,
        "kind": "inject" if args.adapter else "source",
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
        "updated_at": time.strftime("%Y-%m-%d %H:%M"),
        "sets_mode": args.sets,
        "sets_count": len([x for x in (args.sets.split(",") if args.sets not in ("all", "recommended", "") else sets)]),
        "adapter": args.adapter or "",
        "attr": _adapter_attr(args.adapter),
        "storageKey": _adapter_storage_key(args.adapter),
        "port": port,
        "app_path": app,
        "page_url": url,
        "project": args.project or "",
        "binding": f"adapters/{name}/binding.json" if (ROOT / "adapters" / name / "binding.json").exists() else "",
        "note": "改不了源码的宿主：重启会掉，restore 一句话拿回来" if args.adapter else "源码型宿主：写在项目里，一般不会掉",
    }
    save_profile(name, data)

    hr("档案已存")
    print(f"  名字：{name}　类型：{'运行时注入' if args.adapter else '源码接入'}")
    print(f"  主题：{args.sets}（{data['sets_count']} 套）" + (f"　适配器：{args.adapter}" if args.adapter else ""))
    print(f"  载荷：{payload}（{sum(f.stat().st_size for f in payload.iterdir() if f.suffix in ('.css', '.js'))//1024} KB）")
    print(f"  位置：{profile_dir(name)}")
    # 网页版提示页：装完弹给用户看的那一份
    page = payload / "给你的用户.html"
    run([str(HERE / "welcome.py"), "--out", str(page), "--sets", str(data["sets_count"])], quiet=True)
    if data["kind"] == "inject":
        print(f"  入口：{'端口 ' + str(port) if port else '（宿主当前没跑，端口未知）'}"
              + (f"　App：{app}" if app else ""))
        print("\n  重启 / 升级之后要拿回来：对 Agent 说「把外观恢复回来」即可（Agent 跑 restore）。")
    if not args.no_open and page.exists():
        subprocess.Popen(["open", str(page)])
        print(f"\n  已经用浏览器打开这一页给用户看了：{page}")
    return 0


def cmd_restore(args):
    data = load_profile(args.name)
    name = args.name
    hr(f"恢复外观档案：{name}")

    if data["kind"] == "source":
        proj = data.get("project")
        if not proj or not pathlib.Path(proj).exists():
            print(f"✗ 项目路径不在：{proj}　（档案里记的，可能被移走了）", file=sys.stderr)
            return 3
        r = run([str(HERE / "auto.py"), "--project", proj, "--sets", data.get("sets_mode", "all")])
        print("\n✓ 已按档案重新接入项目（已经接过就不会重复插，幂等）")
        return 0

    # 注入型宿主
    port, note = find_port(args.port or data.get("port"))
    if note:
        print(f"  {note}")
    if not port:
        print("✗ 宿主现在没开调试端口，注入不进去。\n")
        app = data.get("app_path") or f"/Applications/{name}.app"
        print("  让 Agent 这样重开宿主（用户不用管）：")
        print(f'    osascript -e \'quit app "{pathlib.Path(app).stem}"\' ; sleep 2 ; \\')
        print(f'    open -a "{app}" --args --remote-debugging-port={data.get("port") or 9333} --remote-allow-origins=*')
        print("\n  重开之后再跑一次 restore 就好。")
        return 3

    payload = profile_dir(name) / "payload"
    themes_js, roles_js = payload / "loki-themes.js", payload / "loki-roles.js"
    css = payload / "loki-themes.css"
    if not themes_js.exists():
        print("✗ 档案里的载荷不见了，重存一次：profile.py save ...", file=sys.stderr)
        return 3

    import importlib.util
    spec = importlib.util.spec_from_file_location("adapt", HERE / "adapt.py")
    A = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(A)

    # 先把自己上一轮塞进去的东西清掉：切换器里的条目、样式表、挂钩器与钩子类名。
    # 不然改小了清单再注入，旧的条目还挂在宿主面板里（重复项）。
    A.cdp(port, """(function () {
      document.querySelectorAll('[data-loki-theme-id]').forEach(function (e) { e.remove(); });
      var s = document.getElementById('loki-theme-kit-styles'); if (s) s.remove();
      if (window.__LOKI_ROLE_OBSERVER__) { window.__LOKI_ROLE_OBSERVER__.disconnect(); window.__LOKI_ROLE_OBSERVER__ = null; }
      window.__LOKI_ROLES__ = null;
      document.querySelectorAll('[data-loki-role]').forEach(function (el) {
        el.classList.remove('loki-' + el.getAttribute('data-loki-role'));
        el.removeAttribute('data-loki-role');
      });
      return 1;
    })()""")

    # 注入两份：主题包（把套组注册进宿主自己的外观面板）+ 结构件挂钩器。
    # 主题包是自包含的（自带样式与切换器），所以不用再单独注 CSS。
    run([str(HERE / "inject-cdp.py"), "--port", str(port),
         "--js", str(themes_js), "--style-id", "loki-theme-kit-styles"], quiet=True)
    run([str(HERE / "inject-cdp.py"), "--port", str(port), "--js", str(roles_js)], quiet=True)

    # 宿主升级过就自愈：失效的角色现场重认，然后拿新挂钩器再注一次
    spec_check = run([str(HERE / "adapt.py"), "--host", name, "--port", str(port),
                      "--check", "--keep"], quiet=True)
    if spec_check.returncode != 0:
        print("\n  宿主结构变了 —— 自动重认一遍（用户不用管）")
        run([str(HERE / "adapt.py"), "--host", name, "--port", str(port), "--refresh", "--apply"],
            quiet=True)
        render_roles(name)
        run([str(HERE / "inject-cdp.py"), "--port", str(port), "--css", str(css), "--js", str(js)])

    # 回读：说清楚现在到底装上没有
    got = A.cdp(port, "({样式: !!document.getElementById('loki-theme-kit-styles'),"
                      "钩子元素: document.querySelectorAll('[data-loki-role]').length,"
                      "套组条目: document.querySelectorAll('[data-loki-theme-id]').length,"
                      "皮肤: document.documentElement.getAttribute('data-cola-skin'),"
                      "存储: localStorage.getItem('cola-skin-selected')})")
    hr("回读")
    print(f"  样式表：{'在' if got.get('样式') else '不在'}　"
          f"面板里的套组：{got.get('套组条目')} 套　结构件挂钩：{got.get('钩子元素')} 个元素\n"
          f"  当前外观：{got.get('皮肤')}（记忆：{got.get('存储')}）")
    doc = payload / "给你的用户.md"
    if doc.exists():
        print(f"\n  交给用户看的那一页：{doc}")
    print("\n✓ 恢复了。" + ("　（点宿主自己的外观切换器就能换，选择会被记住）" if got.get("皮肤") else ""))
    return 0


def cmd_sets(args):
    data = load_profile(args.name)
    data["sets_mode"] = args.only
    data["updated_at"] = time.strftime("%Y-%m-%d %H:%M")
    save_profile(args.name, data)
    build_payload(args.name, args.only, data.get("adapter") or "")
    render_roles(args.name)
    print(f"✓ 清单已改成：{args.only}")
    print("  现在重新装上：profile.py restore --name " + args.name)
    return 0


def cmd_list(args):
    if not HOME.exists():
        print("还没有任何档案。")
        return 0
    rows = list(HOME.iterdir())
    if not rows:
        print("还没有任何档案。")
        return 0
    print(f"{'名字':<16}{'类型':<10}{'主题':<28}{'端口':<8}{'更新时间'}")
    print("─" * 74)
    for d in sorted(rows):
        f = d / "profile.json"
        if not f.exists():
            continue
        p = json.loads(f.read_text(encoding="utf-8"))
        print(f"{p['name']:<16}{'注入' if p['kind'] == 'inject' else '源码':<10}"
              f"{str(p.get('sets_mode'))[:26]:<28}{str(p.get('port') or '-'):<8}{p.get('updated_at')}")
    return 0


def cmd_drop(args):
    d = profile_dir(args.name)
    if not d.exists():
        print("没有这个档案。")
        return 0
    trash = pathlib.Path.home() / ".Trash" / f"loki-profile-{args.name}-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.move(str(d), str(trash))
    print(f"档案已移到废纸篓（可恢复）：{trash}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("save", help="把这次装了什么存成档案")
    s.add_argument("--name", required=True)
    s.add_argument("--port", type=int)
    s.add_argument("--adapter", default="cola")
    s.add_argument("--sets", default="all", help="all / recommended / 逗号分隔")
    s.add_argument("--app", help="宿主 App 路径（不给就从页面 URL 里认）")
    s.add_argument("--project", help="源码型宿主的项目路径")
    s.add_argument("--no-open", action="store_true", help="存完不自动弹提示页")
    s.set_defaults(fn=cmd_save)

    r = sub.add_parser("restore", help="拿回来（重启 / 升级之后跑这条）")
    r.add_argument("--name", required=True)
    r.add_argument("--port", type=int)
    r.set_defaults(fn=cmd_restore)

    st = sub.add_parser("sets", help="只要哪几套主题")
    st.add_argument("--name", required=True)
    st.add_argument("--only", required=True)
    st.set_defaults(fn=cmd_sets)

    l = sub.add_parser("list", help="有哪些档案")
    l.set_defaults(fn=cmd_list)

    a = sub.add_parser("autostart", help="开机自动恢复（装/卸/看）")
    a.add_argument("--on", action="store_true", help="装上（默认动作）")
    a.add_argument("--off", action="store_true", help="卸掉")
    a.add_argument("--status", action="store_true", help="看现在什么状态")
    a.add_argument("--interval", type=float, default=5.0)
    a.add_argument("--takeover", action="store_true",
                   help="宿主没带调试端口时，退出并用端口重启宿主（碰用户 App，要明确同意）")
    a.set_defaults(fn=cmd_autostart)

    d = sub.add_parser("drop", help="不要这个档案了")
    d.add_argument("--name", required=True)
    d.set_defaults(fn=cmd_drop)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
