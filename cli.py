#!/usr/bin/env python3
"""
Server Monitor CLI — fully dynamic, portable across machines.
No hardcoded app names, IPs, users, or domains.
Config source: srv.py (monitor.conf.json + env vars).
"""

import getpass
import os
import re
import shutil
import socket
import subprocess
import sys

MONITOR_DIR = os.path.dirname(os.path.realpath(__file__))
if MONITOR_DIR not in sys.path:
    sys.path.insert(0, MONITOR_DIR)

try:
    import srv
except ImportError:
    srv = None

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"


def strip_ansi(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def box_line(content: str, width: int) -> str:
    vis = len(strip_ansi(content))
    pad = max(0, width - 4 - vis)
    return f"{BOLD}{CYAN}│{RESET}  {content}{' ' * pad}{BOLD}{CYAN}│{RESET}"


def get_conf():
    if srv and hasattr(srv, "get_config"):
        try:
            return srv.get_config()
        except Exception:
            pass
    return {"port": int(os.environ.get("MONITOR_PORT", os.environ.get("PORT", 8899))),
            "title": os.environ.get("MONITOR_TITLE", "server")}


def get_monitor_user():
    if os.environ.get("MONITOR_USER"):
        return os.environ["MONITOR_USER"]
    try:
        if srv and getattr(srv, "USER", None):
            return next(iter(srv.USER))
    except Exception:
        pass
    return "admin"


def get_network_ips():
    """Auto-detect LAN + Tailscale IPs. No hardcoded fallback."""
    lan = ""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("1.1.1.1", 80))
        lan = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            lan = socket.gethostbyname(socket.gethostname())
        except Exception:
            lan = "127.0.0.1"
    ts = ""
    try:
        r = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
        out = (r.stdout or "").strip().splitlines()
        if out and out[0].strip():
            ts = out[0].strip()
    except Exception:
        pass
    return lan, ts


def render_dashboard():
    if not srv:
        print(f"{RED}Error: Modul srv.py tidak ditemukan di {MONITOR_DIR}{RESET}")
        return 1

    conf = get_conf()
    port_self = int(conf.get("port", 8899))
    title = str(conf.get("title", "server"))
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = ""
    user = getpass.getuser()
    lan_ip, ts_ip = get_network_ips()
    primary_ip = ts_ip or lan_ip

    snap = srv.snapshot()
    pm2_by_name = {p["name"]: p for p in snap.get("pm2", [])}
    svc_by_port = {s["port"]: s for s in snap.get("services", [])}
    sites = snap.get("sites", {})

    term_w = shutil.get_terminal_size((80, 24)).columns
    w = max(76, min(term_w, 96))

    print(f"{BOLD}{CYAN}╭{'─' * (w - 2)}╮{RESET}")
    print(box_line(f"{BOLD}{title.upper()}{RESET} {DIM}• Server Monitor ({hostname}){RESET}", w))
    host_parts = []
    if ts_ip:
        host_parts.append(f"{GREEN}{ts_ip} (Tailscale){RESET}")
    if lan_ip:
        host_parts.append(f"{WHITE}{lan_ip} (LAN){RESET}")
    if host_parts:
        print(box_line(f"{DIM}Host:{RESET} " + f" {DIM}•{RESET} ".join(host_parts), w))
    sys_info = (f"Uptime: {snap['uptime']} │ CPU: {snap['cpu']}% │ "
                f"RAM: {snap['mem_used_gb']}/{snap['mem_total_gb']}GB ({snap['mem_pct']}%) │ "
                f"Disk: {snap['disk_pct']}%")
    print(box_line(f"{DIM}{sys_info}{RESET}", w))
    print(f"{BOLD}{CYAN}╰{'─' * (w - 2)}╯{RESET}")
    print()

    print(f"{BOLD}{WHITE}  DAFTAR APLIKASI & ALAMAT AKSES:{RESET}")
    print(f"  {DIM}{'─' * (w - 4)}{RESET}")

    registered_web = snap.get("web", [])
    registered_names = set()

    if not registered_web:
        print(f"  {DIM}(tidak ada aplikasi terdeteksi){RESET}\n")

    for item in registered_web:
        name = item.get("name", "?")
        registered_names.add(name)
        port = item.get("port")
        path = item.get("path", "/") or "/"
        clean_path = "" if path == "/" else path
        desc = item.get("desc", "")
        url_override = item.get("url")
        host = item.get("host", "")
        is_localhost = (host == "127.0.0.1")

        pm2_info = pm2_by_name.get(name)
        svc_info = svc_by_port.get(port) if port else None

        status_text, status_color, bullet = "OFFLINE", RED, "○"
        if url_override:
            if sites.get(name, False):
                status_text, status_color, bullet = "ONLINE", GREEN, "●"
        elif pm2_info:
            pm2_st = pm2_info.get("status")
            if pm2_st == "online" and (svc_info and svc_info.get("ok")):
                status_text, status_color, bullet = "ONLINE", GREEN, "●"
            elif pm2_st == "online":
                status_text, status_color, bullet = "STARTING", YELLOW, "◐"
            else:
                status_text = str(pm2_st).upper()
        elif svc_info and svc_info.get("ok"):
            status_text, status_color, bullet = "ONLINE", GREEN, "●"

        extra_parts = []
        if port:
            extra_parts.append(f"Port: {port}")
        if pm2_info:
            extra_parts.append(f"RAM: {pm2_info.get('mem', '-')}")
            extra_parts.append(f"CPU: {pm2_info.get('cpu', '-')}")
        elif desc:
            extra_parts.append(str(desc)[:60])
        extra_str = f"{DIM}(" + " │ ".join(extra_parts) + f"){RESET}" if extra_parts else ""

        print(f"  {status_color}{bullet}{RESET} {BOLD}{name:<20}{RESET} {status_color}[{status_text}]{RESET}  {extra_str}")

        if url_override:
            print(f"     {CYAN}└─ Web URL  :{RESET} {BOLD}{url_override}{RESET}")
        elif port and is_localhost:
            local_url = f"http://127.0.0.1:{port}{path}"
            print(f"     {CYAN}├─ Local URL:{RESET} {BOLD}{local_url}{RESET}")
            print(f"     {YELLOW}└─ SSH tunnel:{RESET} ssh -L {port}:localhost:{port} {user}@{primary_ip}")
        elif port:
            if ts_ip:
                print(f"     {CYAN}├─ Tailscale:{RESET} {BOLD}http://{ts_ip}:{port}{clean_path}{RESET}")
            if lan_ip:
                tail = "└" if name != "monitor" else "├"
                print(f"     {CYAN}{tail}─ LAN      :{RESET} http://{lan_ip}:{port}{clean_path}")
            if name == "monitor":
                mon_user = get_monitor_user()
                print(f"     {MAGENTA}└─ Login    :{RESET} user: {BOLD}{mon_user}{RESET} {DIM}(password via env/config){RESET}")
        print()

    other_pm2 = [p for p in snap.get("pm2", []) if p["name"] not in registered_names]
    if other_pm2:
        print(f"  {BOLD}{WHITE}PM2 LAINNYA:{RESET}")
        for p in other_pm2:
            st = p.get("status", "?")
            st_color = GREEN if st == "online" else RED
            print(f"  {st_color}●{RESET} {BOLD}{p['name']}{RESET} [{str(st).upper()}] - RAM: {p.get('mem')} │ CPU: {p.get('cpu')} │ Uptime: {p.get('uptime')}")
        print()

    docker = snap.get("docker", []) or []
    running = [d for d in docker if d.get("ok")]
    if running:
        print(f"  {BOLD}{WHITE}DOCKER:{RESET}")
        for d in running:
            print(f"  {GREEN}●{RESET} {BOLD}{d['name']}{RESET} [{d.get('status')}] {DIM}{d.get('image', '')} {d.get('ports', '')}{RESET}")
        print()

    # Infra: semua service TCP/non-HTTP yang tidak masuk grid apps.
    web_ports = {i.get("port") for i in registered_web if i.get("port")}
    infra = [s for s in snap.get("services", []) if s.get("port") not in web_ports and s.get("ok")]
    if infra:
        print(f"  {BOLD}{WHITE}INFRASTRUKTUR:{RESET}")
        print("  " + "   ".join(f"{GREEN}●{RESET} {s['name']} (:{s['port']})" for s in infra))
        print()

    print(f"  {DIM}{'─' * (w - 4)}{RESET}")
    print(f"  {DIM}Perintah:{RESET} {CYAN}monitor restart{RESET} │ {CYAN}monitor logs [nama]{RESET} │ {CYAN}monitor token [app]{RESET} │ {CYAN}monitor help{RESET}")
    print()
    return 0


def cmd_token(args):
    app = args[0] if args else None
    lan_ip, ts_ip = get_network_ips()
    ip = ts_ip or lan_ip
    user = getpass.getuser()
    if not srv or not hasattr(srv, "get_app_token"):
        print(f"{RED}srv.get_app_token tidak tersedia.{RESET}")
        return 1
    tok, found_app, found_port = None, app, None
    if app:
        tok = srv.get_app_token(app)
        # cari port app tersebut dari snapshot
        try:
            snap = srv.snapshot()
            for it in snap.get("web", []):
                if it.get("name") == app and it.get("port"):
                    found_port = it["port"]
                    break
        except Exception:
            pass
    else:
        # auto: cari app localhost-only yang punya token
        try:
            snap = srv.snapshot()
            for it in snap.get("web", []):
                if it.get("host") == "127.0.0.1" and it.get("name"):
                    t = srv.get_app_token(it["name"])
                    if t:
                        tok, found_app, found_port = t, it["name"], it.get("port")
                        break
            if not tok:
                for cand in [p["name"] for p in snap.get("pm2", [])]:
                    t = srv.get_app_token(cand)
                    if t:
                        tok, found_app = t, cand
                        break
        except Exception:
            pass
    if not tok:
        print(f"{RED}Token tidak ditemukan{f' untuk {app}' if app else ''}.{RESET}")
        print("Pastikan aplikasi berjalan dan log-nya mengandung 'token=...'.")
        return 1
    print(f"{BOLD}{GREEN}Akses {found_app}:{RESET}")
    print(f"  • Token      : {BOLD}{tok}{RESET}")
    if found_port:
        print(f"  • Local URL  : {CYAN}http://127.0.0.1:{found_port}/?token={tok}{RESET}")
        print()
        print(f"{BOLD}SSH Tunnel (di PC lokal):{RESET}")
        print(f"  {YELLOW}ssh -L {found_port}:localhost:{found_port} {user}@{ip}{RESET}")
        print(f"  Buka: http://localhost:{found_port}/?token={tok}")
    return 0


def _has(cmd):
    return shutil.which(cmd) is not None


def cmd_logs(args):
    name = args[0] if args else "monitor"
    lines = "50"
    if len(args) > 1 and args[1].isdigit():
        lines = args[1]
    # 1. pm2
    if _has("pm2"):
        try:
            r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
            names = [p.get("name") for p in __import__("json").loads(r.stdout or "[]")]
            if name in names:
                subprocess.run(["pm2", "logs", name, "--lines", lines])
                return 0
        except Exception:
            pass
    # 2. docker
    if _has("docker"):
        try:
            r = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"],
                               capture_output=True, text=True, timeout=3)
            if name in [l.strip() for l in r.stdout.splitlines()]:
                subprocess.run(["docker", "logs", "-f", "--tail", lines, name])
                return 0
        except Exception:
            pass
    # 3. journald (systemd user / system)
    try:
        r = subprocess.run(["journalctl", "--user", "-u", name, "-n", lines, "--no-pager"],
                           capture_output=True, text=True, timeout=5)
        if (r.stdout or "").strip():
            print(r.stdout)
            return 0
        r = subprocess.run(["journalctl", "-u", name, "-n", lines, "--no-pager"])
        print(r.stdout or "(log kosong)")
        return 0
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"{RED}Gagal membaca log: {e}{RESET}")
        return 1
    return 0


def _run_manager(args, action):
    target = args[0] if args else "monitor"
    # monitor itu sendiri -> systemd unit jika ada
    if target in ("monitor", "deck", "srv"):
        for base in (["systemctl", "--user", action, "monitor"],
                     ["systemctl", action, "monitor"]):
            try:
                r = subprocess.run(base, capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    print(f"monitor: {action} OK via {' '.join(base[:2])}")
                    return 0
            except Exception:
                pass
        if _has("pm2"):
            subprocess.run(["pm2", action, "monitor"])
            return 0
        print(f"{RED}Unit monitor tidak ditemukan (systemd/pm2).{RESET}")
        return 1
    # app lain: coba pm2 -> docker -> systemd
    if _has("pm2"):
        try:
            r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
            names = [p.get("name") for p in __import__("json").loads(r.stdout or "[]")]
            if target in names:
                subprocess.run(["pm2", action, target])
                return 0
        except Exception:
            pass
    if _has("docker"):
        try:
            r = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"],
                               capture_output=True, text=True, timeout=3)
            if target in [l.strip() for l in r.stdout.splitlines()]:
                subprocess.run(["docker", action, target])
                return 0
        except Exception:
            pass
    for base in (["systemctl", "--user", action, target], ["systemctl", action, target]):
        try:
            r = subprocess.run(base, capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                print(f"{target}: {action} OK")
                return 0
        except Exception:
            pass
    print(f"{RED}Target '{target}' tidak ditemukan di pm2/docker/systemd.{RESET}")
    return 1


def cmd_help():
    conf = get_conf()
    port = conf.get("port", 8899)
    lan_ip, ts_ip = get_network_ips()
    primary = ts_ip or lan_ip
    mon_user = get_monitor_user()
    print(f"{BOLD}PENGGUNAAN:{RESET}")
    print("  monitor                     Tampilkan status semua aplikasi + link akses")
    print("  monitor token [app]         Tampilkan token app localhost-only + cara SSH tunnel")
    print("  monitor restart [nama]      Restart monitor / container / service")
    print("  monitor start [nama]        Start monitor / container / service")
    print("  monitor stop [nama]         Stop monitor / container / service")
    print("  monitor status [nama]       Status pm2 / docker / systemd")
    print("  monitor logs [nama] [lines] Log pm2 / docker / journalctl")
    print("  monitor json                Snapshot JSON mentah")
    print("  monitor help                Bantuan ini")
    print()
    print(f"{BOLD}WEB DASHBOARD:{RESET}")
    print(f"  URL : http://{primary}:{port}")
    print(f"  User: {mon_user} (password via MONITOR_PASS / monitor.conf.json)")
    return 0


def cmd_status(args):
    target = args[0] if args else ""
    if not target:
        if _has("pm2"):
            subprocess.run(["pm2", "status"])
        if _has("docker"):
            subprocess.run(["docker", "ps", "--format", "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"])
        subprocess.run(["systemctl", "--user", "status", "monitor", "--no-pager", "-l"])
        return 0
    return _run_manager(args, "status")


def main():
    args = sys.argv[1:]
    if not args:
        return render_dashboard()
    cmd = args[0].lower()
    subargs = args[1:]
    if cmd in ("apps", "list", "ls", "all"):
        return render_dashboard()
    elif cmd in ("token", "dsh", "deepseek"):
        return cmd_token(subargs)
    elif cmd == "logs":
        return cmd_logs(subargs)
    elif cmd == "restart":
        # status butuh show, bukan restart
        return _run_manager(subargs, "restart")
    elif cmd == "start":
        return _run_manager(subargs, "start")
    elif cmd == "stop":
        return _run_manager(subargs, "stop")
    elif cmd == "status":
        return cmd_status(subargs)
    elif cmd == "json":
        if srv:
            import json
            print(json.dumps(srv.snapshot(), indent=2))
            return 0
        else:
            print("{}", file=sys.stderr)
            return 1
    elif cmd in ("help", "-h", "--help"):
        return cmd_help()
    else:
        print(f"{RED}Perintah '{cmd}' tidak dikenali.{RESET}\n")
        cmd_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
