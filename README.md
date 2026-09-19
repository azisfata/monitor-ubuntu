<div align="center">

# ⚙️ Monitor Ubuntu

### **Ultra-Lightweight, Modern & Single-File Server Monitoring Dashboard**
*Dashboard monitoring server Linux modern, cepat, aman, dan tanpa dependensi eksternal (100% Python Standard Library).*

<br/>

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%2F%20Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](https://ubuntu.com/)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(stdlib%20only)-2ea44f?style=for-the-badge)](https://github.com/azisfata/monitor-ubuntu)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br/>

```text
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ ⚙️ server     [↓ 12 KB/s · ↑ 170 KB/s] [up 1d 4h] [sw 0/4G]  ● LIVE 10:50:00│
 ├─────────────────────────────────────────────────────────────────────────────┤
 │   ╭──────────╮    ╭──────────╮    ╭──────────╮    ╭──────────╮              │
 │   │  14.2 %  │    │  31.0 %  │    │  18.7 %  │    │   1.25   │              │
 │   │   CPU    │    │   MEM    │    │   DISK   │    │   LOAD   │              │
 │   ╰──────────╯    ╰──────────╯    ╰──────────╯    ╰──────────╯              │
 │                                                                             │
 │ ▶ APPS & PM2 SERVICES (7)                                                   │
 │ ┌──────────────────────┐ ┌──────────────────────┐ ┌───────────────────────┐ │
 │ │ ● sapa-server      ↗ │ │ ● dsh-web          ↗ │ │ ● hermes-dashboard  ↗ │ │
 │ │ [📄 log] [↻] [■]     │ │ [📄 log] [↻] [■]     │ │ [📄 log] [↻] [■]      │ │
 │ │ 0.5% · 105MB · up 2h │ │ 1.6% · 755MB · up 2h │ │ 0.5% · 143MB · up 2h  │ │
 │ └──────────────────────┘ └──────────────────────┘ └───────────────────────┘ │
 └─────────────────────────────────────────────────────────────────────────────┘
```

</div>

---

## 🌟 Mengapa Monitor Ubuntu?

- 🪶 **Ultra-Ringan**: Hanya satu file Python tunggal (`srv.py`), konsumsi memori hanya **~8 MB RAM**, dan pemakaian CPU **< 0.01%**.
- 📦 **Zero External Dependencies**: Tidak memerlukan `pip install`, tidak membutuhkan Redis/Database eksternal, hanya murni menggunakan modul bawaan Python (*Standard Library*).
- ⚡ **Super Cepat & Responsif**: Backend asinkron/multithreaded dengan waktu respon API sub-milidetik (< 15ms) dan auto-refresh 3 detik.
- 🎨 **Tampilan Modern & Dinamis**: Desain gelap (*dark theme*) elegan dengan 4 SVG arc gauges simetris di grid utama, badge header informatif, dan adaptif untuk Mobile, Tablet, serta Desktop.
- 📱 **WhatsApp Alerting Built-in**: Peringatan otomatis langsung ke WhatsApp admin saat aplikasi PM2 bermasalah atau RAM/Disk kritis (>90%).

---

## 📊 Fitur-Fitur Utama

### 1. 📈 Real-Time Dynamic Metrics
- **Dynamic Semi-Circle SVG Gauges**: Indikator melengkung halus untuk **CPU**, **RAM**, **DISK**, dan **LOAD** dengan pewarnaan dinamis 5-level:
  - 🟢 **Normal** ($<30\%$) $\rightarrow$ 🩵 **Rendah** ($30-54\%$) $\rightarrow$ 🟡 **Sedang** ($55-74\%$) $\rightarrow$ 🟠 **Tinggi** ($75-89\%$) $\rightarrow$ 🔴 **Kritis** ($\ge 90\%$)
- **Header Info Badges (Sticky Navbar)**:
  - **Live Network Bandwidth**: Kecepatan Download ($\downarrow$ RX) & Upload ($\uparrow$ TX) real-time dari delta `/proc/net/dev`.
  - **Server Uptime**: Durasi server aktif (`up 1d 4h`).
  - **Swap Memory Detail**: Kapasitas Swap terpakai vs total (`sw 0/4G`).
  - **Live Status Pulse**: Indikator titik hijau berkedip real-time lengkap dengan waktu server.

### 2. 🚀 Unified Apps & PM2 Manager
- Menyatukan daftar Web Portal dan PM2 Service dalam satu grid kartu interaktif.
- **Dual-Layer Health Check Verification**: Memverifikasi status hidup aplikasi secara berlapis (proses PM2 berstatus `online` **DAN** socket port web benar-benar telah terbuka & merespons), sehingga saat aplikasi sedang restart/booting (*cold start*), indikator akan menampilkan warna **Merah/Oranye (`starting...` / `restarting...`)** sampai port benar-benar siap melayani koneksi.
- **Smart URL Resolving**: Menyesuaikan IP/Domain klien secara otomatis, atau dikunci ke `127.0.0.1` (misal untuk `dsh-web`) yang siap diakses via SSH Port Forwarding.
- **Live Metrics Badge**: Menampilkan persentase CPU, pemakaian RAM, dan uptime/status tiap aplikasi secara individual.
- **Quick Action Buttons**: Tombol interaktif untuk **Restart (↻)**, **Stop (■)**, dan **Start (▶)** aplikasi langsung dari browser.

### 3. 📄 Interactive Quick Log Viewer
- Modal terminal pop-up instan untuk membaca 50–100 baris log PM2 (*stdout* & *stderr*) tanpa perlu login SSH ke server.
- Dilengkapi tombol **↻ Refresh Log** dan **📋 Copy to Clipboard**.

### 4. 🛡️ Systemd Core Services & Docker Monitor
- **Systemd Watcher**: Memantau status unit sistem dan user unit penting (`tailscaled`, `nginx`, `docker`, `ssh`, `postgresql`, `redis-server`, `hermes-gateway`).
- **Docker Containers**: Deteksi dinamis semua container Docker yang sedang berjalan beserta statusnya (`Up`, `Exited`, port).

### 5. 🔍 Ports, Services & Top Processes
- **Port Scanner & Health Checker**: Pemindaian port listening via `ss -tlnpH` dan verifikasi HTTP/HTTPS/TCP paralel.
- **Top Memory Processes**: Pelacakan 8 proses teratas pemakan RAM dari `/proc/*/status` dengan resolusi nama aplikasi otomatis.

### 6. 🔔 WhatsApp Background Alert Notifier
- Daemon background ultra-ringan yang mengecek kesehatan server secara berkala tiap **5 menit**.
- Mengirim pesan WhatsApp instan via Hermes Bridge jika:
  - Ada aplikasi PM2 berstatus `errored` atau `stopped`.
  - Pemakaian RAM fisik atau Disk melebihi **90%**.
- **Fitur Anti-Spam Cooldown**: Jeda peringatan **1 jam** per insiden + notifikasi **Recovery** otomatis saat server pulih kembali.

---

## 🚦 Arsitektur & Efisiensi Sistem

```mermaid
flowchart TD
    subgraph Browser["🖥️ Client Browser"]
        UI["Dashboard Web (HTML5/CSS3/Vanilla JS)"]
        MODAL["Quick Terminal Log Viewer"]
    end

    subgraph Server["🐧 Ubuntu Server (srv.py)"]
        HTTP["ThreadingHTTPServer (:8899)"]
        AUTH["HMAC-SHA256 Session Auth"]
        PROC["/proc filesystem (/proc/stat, /proc/meminfo, /proc/net/dev)"]
        SS["Socket Scanner (ss -tlnpH)"]
        PM2["PM2 CLI Bridge (jlist, logs)"]
        ALERT["Background Alert Worker (Daemon Thread)"]
    end

    subgraph WA["📱 Hermes WhatsApp Bridge"]
        BRIDGE["WhatsApp Bridge (:3105/send)"]
        ADMIN["Nomor Admin (WhatsApp)"]
    end

    UI -->|Poll /api tiap 3s| HTTP
    MODAL -->|Fetch /logs?name=...| HTTP
    HTTP --> AUTH
    AUTH --> PROC
    AUTH --> SS
    AUTH --> PM2
    ALERT -->|Cek Status Tiap 5m| PROC
    ALERT -->|Cek App Tiap 5m| PM2
    ALERT -->|Kirim Peringatan| BRIDGE
    BRIDGE --> ADMIN
```

---

## ⚡ Panduan Instalasi & Penggunaan

### 1. Menjalankan Langsung (Testing / Standalone)
```bash
python3 srv.py
```
Buka browser Anda dan akses: `http://<IP-SERVER>:8899`

---

### 2. Menjalankan di Background dengan PM2 (Direkomendasikan)
Gunakan PM2 agar service monitor otomatis berjalan di background dan hidup kembali saat server di-reboot:

```bash
# Clone repositori
git clone https://github.com/azisfata/monitor-ubuntu.git ~/monitor
cd ~/monitor

# Jalankan dengan PM2
pm2 start srv.py --name monitor --interpreter python3

# Simpan state PM2 untuk auto-start saat reboot
pm2 save
```

---

## 🖥️ Command-Line Interface (`monitor` CLI)

Selain web dashboard, Anda dapat memantau server dan melihat semua link akses aplikasi langsung dari terminal menggunakan perintah `monitor`:

```bash
# Setup symlink ke binary lokal (cukup sekali)
ln -sf ~/aplikasi/monitor/cli.py ~/.local/bin/monitor
chmod +x ~/aplikasi/monitor/cli.py
```

### Penggunaan di Terminal:
```bash
# 1. Tampilkan ringkasan sistem, status semua aplikasi, dan alamat aksesnya
monitor

# 2. Tampilkan token autentikasi dsh-web (DeepSeek) & panduan SSH tunneling
monitor token

# 3. Restart service monitor atau aplikasi tertentu
monitor restart
monitor restart sapa-server

# 4. Lihat status PM2 semua service
monitor status

# 5. Baca live log aplikasi
monitor logs monitor
monitor logs dsh-web 100

# 6. Ekspor seluruh snapshot sistem dalam format JSON
monitor json
```

### Preview Tampilan Terminal:
```text
╭──────────────────────────────────────────────────────────────────────────────╮
│  DECK • Server Monitor & Application Directory                               │
│  Host: 100.126.4.94 (Tailscale) • 192.168.10.149 (LAN)                       │
│  Uptime: 4d 17h 20m │ CPU: 0.0% │ RAM: 3.3/7.7GB (43.6%) │ Disk: 19.5%       │
╰──────────────────────────────────────────────────────────────────────────────╯

  DAFTAR APLIKASI & ALAMAT AKSES:
  ────────────────────────────────────────────────────────────────────────────
  ● link-shortener     [ONLINE]  (Port: 8080 │ RAM: 18MB │ CPU: 0%)
     ├─ Domain   : https://s.kemenkopmk.go.id
     ├─ Tailscale: http://100.126.4.94:8080
     └─ LAN      : http://192.168.10.149:8080

  ● adminer            [ONLINE]  (Port: 9090 │ RAM: 31MB │ CPU: 0%)
     ├─ Tailscale: http://100.126.4.94:9090
     └─ LAN      : http://192.168.10.149:9090

  ● cockpit            [ONLINE]  (Port: 9091)
     ├─ Tailscale: http://100.126.4.94:9091
     └─ LAN      : http://192.168.10.149:9091

  ● 9router            [ONLINE]  (Port: 20128 │ RAM: 198MB │ CPU: 0.4%)
     ├─ Tailscale: http://100.126.4.94:20128/dashboard
     └─ LAN      : http://192.168.10.149:20128/dashboard

  ● dsh-web            [ONLINE]  (Port: 3080 │ RAM: 986MB │ CPU: 3.4%)
     ├─ Local URL: http://127.0.0.1:3080/?token=...
     └─ Akses SSH: ssh -L 3080:localhost:3080 fata@100.126.4.94

  ● hermes-dashboard   [ONLINE]  (Port: 9119 │ RAM: 286MB │ CPU: 0.8%)
     ├─ Tailscale: http://100.126.4.94:9119
     └─ LAN      : http://192.168.10.149:9119

  ● sapa-server        [ONLINE]  (Port: 3000 │ RAM: 105MB │ CPU: 0.2%)
     ├─ API Route: https://sapa.kemenkopmk.go.id/api/
     ├─ Tailscale: http://100.126.4.94:3000
     └─ LAN      : http://192.168.10.149:3000

  ● pub-fata           [ONLINE]  (Port: 4080 │ RAM: 77MB │ CPU: 0.2%)
     ├─ Tailscale: http://100.126.4.94:4080
     └─ LAN      : http://192.168.10.149:4080

  ● deck (monitor)     [ONLINE]  (Port: 8899 │ RAM: 24MB │ CPU: 0%)
     ├─ Tailscale: http://100.126.4.94:8899
     ├─ LAN      : http://192.168.10.149:8899
     └─ Login    : user: fata │ pass: 1232

  ● sapa-web           [ONLINE]  (portal sapa)
     └─ Web URL  : https://sapa.kemenkopmk.go.id

  INFRASTRUKTUR & DATABASE:
  ● ssh (:22)   ● dns (:53)   ● hermes-wa (:3105)   ● postgres (:5432)   ● redis (:6379)
```

---

## ⚙️ Variabel Lingkungan (*Environment Variables*)

Semua pengaturan bersifat opsional dengan nilai bawaan yang siap pakai:

| Variabel | Tipe | Default | Penjelasan |
| :--- | :---: | :---: | :--- |
| `PORT` | *Integer* | `8899` | Port HTTP listen server |
| `MONITOR_USER` | *String* | `fata` | Username login dashboard |
| `MONITOR_PASS` | *String* | `1232` | Password login dashboard |
| `MONITOR_TOKEN` | *String* | `.token` file / fallback | Secret key untuk penandatanganan cookie sesi HMAC |
| `MONITOR_WA_ADMIN` | *String* | Auto dari `.env` Hermes | Nomor tujuan notifikasi WhatsApp (format: `6281335004509`) |
| `MONITOR_ALERT_INTERVAL` | *Integer* | `300` | Interval pengecekan background dalam detik (default: 5 menit) |
| `MONITOR_ALERT_COOLDOWN` | *Integer* | `3600` | Jeda anti-spam pengiriman ulang alert dalam detik (default: 1 jam) |

---

## 🔒 Keamanan & Praktik Terbaik

- 🔑 **Password Hashing**: Menggunakan `hashlib.sha256` dengan perbandingan `hmac.compare_digest` untuk mencegah *timing attacks*.
- 🛡️ **Signed Session Cookies**: Cookie sesi ditandatangani secara kriptografis menggunakan algoritma `HMAC-SHA256` dengan TTL 30 hari.
- 🗂️ **Allowlist Log Viewer**: Endpoint `/logs` hanya mengizinkan nama aplikasi yang terdaftar di PM2 untuk mencegah *Path Traversal*.
- 🌐 **Zero External Callout**: Dashboard tidak memuat file CSS/JS dari CDN eksternal sehingga aman digunakan di jaringan privat/intranet tanpa akses internet publik.

---

## 📄 Lisensi
Proyek ini didistribusikan di bawah lisensi [MIT License](LICENSE).
