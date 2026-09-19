#!/usr/bin/env python3
"""
DECK / Server Monitor CLI
Perintah terminal untuk memantau server, menampilkan status semua aplikasi,
dan alamat akses lengkap (Tailscale, LAN, Domain, Localhost).
"""

import os
import re
import shutil
import socket
import subprocess
import sys

# Tambahkan path direktori monitor jika belum ada
MONITOR_DIR = os.path.dirname(os.path.realpath(__file__))
if MONITOR_DIR not in sys.path:
    sys.path.insert(0, MONITOR_DIR)

try:
    import srv
except ImportError:
    srv = None

# ANSI Escape Colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"


def strip_ansi(s: str) -> str:
    """Hapus kode ANSI untuk menghitung panjang karakter visual."""
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def box_line(content: str, width: int) -> str:
    """Format satu baris box dengan border kiri-kanan rata."""
    vis = len(strip_ansi(content))
    pad = max(0, width - 4 - vis)
    return f"{BOLD}{CYAN}│{RESET}  {content}{' ' * pad}{BOLD}{CYAN}│{RESET}"


def get_network_ips():
    """Dapatkan IP LAN dan IP Tailscale."""
    lan = "192.168.10.149"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        lan = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    ts = ""
    try:
        r = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
        ts = r.stdout.strip()
    except Exception:
        pass
    return lan, ts


def render_dashboard():
    """Tampilkan ringkasan status server dan daftar aplikasi berserta link aksesnya."""
    if not srv:
        print(f"{RED}Error: Modul srv.py tidak ditemukan di {MONITOR_DIR}{RESET}")
        return 1

    lan_ip, ts_ip = get_network_ips()
    primary_ip = ts_ip if ts_ip else lan_ip

    snap = srv.snapshot()

    # Lookup dictionaries
    pm2_by_name = {p["name"]: p for p in snap.get("pm2", [])}
    svc_by_port = {s["port"]: s for s in snap.get("services", [])}
    sites = snap.get("sites", {})

    # Tentukan lebar tampilan
    term_w = shutil.get_terminal_size((80, 24)).columns
    w = max(76, min(term_w, 92))

    # --- HEADER BOX ---
    print(f"{BOLD}{CYAN}╭{'─' * (w - 2)}╮{RESET}")
    print(box_line(f"{BOLD}DECK{RESET} {DIM}• Server Monitor & Application Directory{RESET}", w))
    
    host_parts = []
    if ts_ip:
        host_parts.append(f"{GREEN}{ts_ip} (Tailscale){RESET}")
    if lan_ip:
        host_parts.append(f"{WHITE}{lan_ip} (LAN){RESET}")
    host_str = f"{DIM}Host:{RESET} " + f" {DIM}•{RESET} ".join(host_parts)
    print(box_line(host_str, w))

    sys_info = (
        f"Uptime: {snap['uptime']} │ CPU: {snap['cpu']}% │ "
        f"RAM: {snap['mem_used_gb']}/{snap['mem_total_gb']}GB ({snap['mem_pct']}%) │ "
        f"Disk: {snap['disk_pct']}%"
    )
    print(box_line(f"{DIM}{sys_info}{RESET}", w))
    print(f"{BOLD}{CYAN}╰{'─' * (w - 2)}╯{RESET}")
    print()

    # --- DAFTAR APLIKASI WEB & SERVICE ---
    print(f"{BOLD}{WHITE}  DAFTAR APLIKASI & ALAMAT AKSES:{RESET}")
    print(f"  {DIM}{'─' * (w - 4)}{RESET}")

    registered_web = snap.get("web", [])
    registered_names = set()

    for item in registered_web:
        name = item["name"]
        registered_names.add(name)
        port = item.get("port")
        path = item.get("path", "")
        # Bersihkan path jika hanya '/'
        clean_path = "" if path == "/" else path
        desc = item.get("desc", "")
        url_override = item.get("url")

        pm2_info = pm2_by_name.get(name)
        svc_info = svc_by_port.get(port) if port else None

        # Tentukan status online / starting / offline
        status_text = "OFFLINE"
        status_color = RED
        bullet = "○"

        if url_override:
            ok = sites.get(name, False)
            if ok:
                status_text = "ONLINE"
                status_color = GREEN
                bullet = "●"
        elif pm2_info:
            pm2_st = pm2_info.get("status")
            if pm2_st == "online" and (svc_info and svc_info.get("ok")):
                status_text = "ONLINE"
                status_color = GREEN
                bullet = "●"
            elif pm2_st == "online":
                status_text = "STARTING"
                status_color = YELLOW
                bullet = "◐"
            else:
                status_text = pm2_st.upper()
        elif svc_info and svc_info.get("ok"):
            status_text = "ONLINE"
            status_color = GREEN
            bullet = "●"

        # Tampilkan Resource / Info Tambahan
        extra_parts = []
        if port:
            extra_parts.append(f"Port: {port}")
        if pm2_info:
            extra_parts.append(f"RAM: {pm2_info.get('mem', '-')}")
            extra_parts.append(f"CPU: {pm2_info.get('cpu', '-')}")
        elif desc and not port:
            extra_parts.append(desc)

        extra_str = f"{DIM}(" + " │ ".join(extra_parts) + f"){RESET}" if extra_parts else ""

        # Nama tampilan khusus
        display_name = name
        if name == "monitor":
            display_name = "deck (monitor)"

        print(f"  {status_color}{bullet}{RESET} {BOLD}{display_name:<18}{RESET} {status_color}[{status_text}]{RESET}  {extra_str}")

        # URL Branches
        if url_override:
            print(f"     {CYAN}└─ Web URL  :{RESET} {BOLD}{url_override}{RESET}")
        elif name == "link-shortener":
            print(f"     {CYAN}├─ Domain   :{RESET} {BOLD}https://s.kemenkopmk.go.id{RESET}")
            if ts_ip:
                print(f"     {CYAN}├─ Tailscale:{RESET} http://{ts_ip}:{port}{clean_path}")
            print(f"     {CYAN}└─ LAN      :{RESET} http://{lan_ip}:{port}{clean_path}")
        elif name == "sapa-server":
            print(f"     {CYAN}├─ API Route:{RESET} https://sapa.kemenkopmk.go.id/api/")
            if ts_ip:
                print(f"     {CYAN}├─ Tailscale:{RESET} http://{ts_ip}:{port}{clean_path}")
            print(f"     {CYAN}└─ LAN      :{RESET} http://{lan_ip}:{port}{clean_path}")
        elif name == "dsh-web":
            dsh_url = f"http://127.0.0.1:{port}{path}"
            print(f"     {CYAN}├─ Local URL:{RESET} {BOLD}{dsh_url}{RESET}")
            print(f"     {YELLOW}└─ Akses SSH:{RESET} ssh -L 3080:localhost:3080 fata@{primary_ip}")
        elif name == "monitor":
            if ts_ip:
                print(f"     {CYAN}├─ Tailscale:{RESET} {BOLD}http://{ts_ip}:{port}{clean_path}{RESET}")
            print(f"     {CYAN}├─ LAN      :{RESET} http://{lan_ip}:{port}{clean_path}")
            print(f"     {MAGENTA}└─ Login    :{RESET} user: {BOLD}fata{RESET} │ pass: {BOLD}1232{RESET}")
        else:
            if ts_ip:
                print(f"     {CYAN}├─ Tailscale:{RESET} {BOLD}http://{ts_ip}:{port}{clean_path}{RESET}")
                print(f"     {CYAN}└─ LAN      :{RESET} http://{lan_ip}:{port}{clean_path}")
            else:
                print(f"     {CYAN}└─ LAN      :{RESET} {BOLD}http://{lan_ip}:{port}{clean_path}{RESET}")

        print()

    # --- PM2 PROSES LAIN (JIKA ADA YANG BELUM TERDAFTAR) ---
    other_pm2 = [p for p in snap.get("pm2", []) if p["name"] not in registered_names]
    if other_pm2:
        print(f"  {BOLD}{WHITE}PM2 LAINNYA:{RESET}")
        for p in other_pm2:
            st = p.get("status", "?")
            st_color = GREEN if st == "online" else RED
            print(f"  {st_color}●{RESET} {BOLD}{p['name']}{RESET} [{st.upper()}] - RAM: {p.get('mem')} │ CPU: {p.get('cpu')} │ Uptime: {p.get('uptime')}")
        print()

    # --- INFRASTRUKTUR / SERVICE BACKGROUND LAINNYA ---
    infra_ports = [22, 53, 3105, 5432, 6379]
    active_infra = []
    for p in infra_ports:
        s = svc_by_port.get(p)
        if s and s.get("ok"):
            active_infra.append(f"{GREEN}●{RESET} {s['name']} (:{p})")
    if active_infra:
        print(f"  {BOLD}{WHITE}INFRASTRUKTUR & DATABASE:{RESET}")
        print(f"  {'   '.join(active_infra)}")
        print()

    # --- FOOTER PETUNJUK ---
    print(f"  {DIM}{'─' * (w - 4)}{RESET}")
    print(f"  {DIM}Perintah:{RESET} {CYAN}monitor restart{RESET} │ {CYAN}monitor logs [nama]{RESET} │ {CYAN}monitor token{RESET} │ {CYAN}monitor help{RESET}")
    print()
    return 0


def cmd_token():
    """Tampilkan token dsh-web dan cara tunneling."""
    tok = srv.dsh_token() if srv else None
    lan_ip, ts_ip = get_network_ips()
    ip = ts_ip if ts_ip else lan_ip

    if not tok:
        print(f"{RED}Token dsh-web tidak ditemukan di log.{RESET}")
        print("Pastikan service dsh-web berjalan: pm2 status dsh-web")
        return 1

    print(f"{BOLD}{GREEN}Akses dsh-web (DeepSeek Harness):{RESET}")
    print(f"  • Token      : {BOLD}{tok}{RESET}")
    print(f"  • Local URL  : {CYAN}http://127.0.0.1:3080/?token={tok}{RESET}")
    print()
    print(f"{BOLD}Perintah SSH Tunnel (Jalankan di terminal lokal PC Anda):{RESET}")
    print(f"  {YELLOW}ssh -L 3080:localhost:3080 fata@{ip}{RESET}")
    print(f"  Lalu buka di browser lokal: http://localhost:3080/?token={tok}")
    return 0


def cmd_logs(args):
    """Buka log pm2 untuk aplikasi tertentu (default: monitor)."""
    name = args[0] if args else "monitor"
    lines = "50"
    if len(args) > 1 and args[1].isdigit():
        lines = args[1]
    cmd = ["pm2", "logs", name, "--lines", lines]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_start(args):
    """Start service monitor via PM2."""
    target = args[0] if args else "monitor"
    if target == "monitor" or target == "deck":
        srv_file = os.path.join(MONITOR_DIR, "srv.py")
        subprocess.run(["pm2", "start", srv_file, "--name", "monitor", "--interpreter", "python3"])
        subprocess.run(["pm2", "save"])
    else:
        subprocess.run(["pm2", "start", target])
    return 0


def cmd_stop(args):
    """Stop service via PM2."""
    target = args[0] if args else "monitor"
    subprocess.run(["pm2", "stop", target])
    return 0


def cmd_restart(args):
    """Restart service via PM2."""
    target = args[0] if args else "monitor"
    subprocess.run(["pm2", "restart", target])
    return 0


def cmd_status(args):
    """Lihat status PM2."""
    target = args[0] if args else "monitor"
    subprocess.run(["pm2", "status", target])
    return 0


def cmd_help():
    """Tampilkan bantuan penggunaan command monitor."""
    lan_ip, ts_ip = get_network_ips()
    primary = ts_ip if ts_ip else lan_ip
    print(f"{BOLD}PENGGUNAAN:{RESET}")
    print("  monitor                     Tampilkan daftar semua aplikasi, status, dan link akses")
    print("  monitor token               Tampilkan token autentikasi dsh-web & perintah tunnel")
    print("  monitor restart [nama]      Restart service monitor (atau app lain seperti sapa-server)")
    print("  monitor start [nama]        Nyalakan service monitor (atau app lain)")
    print("  monitor stop [nama]         Hentikan service monitor (atau app lain)")
    print("  monitor status [nama]       Lihat status PM2 service")
    print("  monitor logs [nama] [lines] Lihat log realtime aplikasi (default: monitor)")
    print("  monitor json                Output data snapshot dalam format JSON mentah")
    print("  monitor help                Tampilkan pesan bantuan ini")
    print()
    print(f"{BOLD}WEB DASHBOARD (DECK):{RESET}")
    print(f"  URL : http://{primary}:8899")
    print("  Auth: fata / 1232")
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        return render_dashboard()

    cmd = args[0].lower()
    subargs = args[1:]

    if cmd in ("apps", "list", "ls", "all"):
        return render_dashboard()
    elif cmd in ("token", "dsh", "deepseek"):
        return cmd_token()
    elif cmd == "logs":
        return cmd_logs(subargs)
    elif cmd == "restart":
        return cmd_restart(subargs)
    elif cmd == "start":
        return cmd_start(subargs)
    elif cmd == "stop":
        return cmd_stop(subargs)
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
