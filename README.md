# ⚙️ Monitor Ubuntu

Dashboard monitoring server Linux single-file yang ringan, cepat, modern, dan tanpa dependensi eksternal (menggunakan Python Standard Library saja).

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Dependencies](https://img.shields.io/badge/dependencies-Zero%20(stdlib%20only)-success.svg)

---

## ✨ Fitur Utama

- **Zero External Dependencies**: Dibangun murni menggunakan modul bawaan Python (`http.server.ThreadingHTTPServer`, `http.client`, `hashlib`, `hmac`, `subprocess`, `concurrent.futures`, `shutil`, dll.).
- **Modern Responsive UI**:
  - **Dynamic SVG Arc Gauges**: Visualisasi meteran melengkung dinamis dengan 5-tingkat pewarnaan kapasitas (*Green* $\rightarrow$ *Teal* $\rightarrow$ *Yellow* $\rightarrow$ *Orange* $\rightarrow$ *Red*).
  - **Live Pulse Indicator**: Status polling real-time tiap 3 detik dengan indikator jam server.
  - Tampilan adaptif mobile, tablet, dan desktop.
- **Real-time System Metrics**:
  - **CPU Usage & Load Average**: Pembacaan presisi dari `/proc/stat` dan `/proc/loadavg` terhadap core CPU.
  - **Memory & Swap Detail**: Menampilkan persentase RAM fisik serta kapasitas Swap terpakai vs total (`0/4G`).
  - **Storage Usage**: Persentase kapasitas disk root `/`.
  - **Live Network Bandwidth**: Kecepatan Download ($\downarrow$ RX) dan Upload ($\uparrow$ TX) real-time dari delta `/proc/net/dev` di grid metrik & sticky navbar.
  - **Uptime & Total Proses**: Durasi server berjalan dan jumlah proses aktif di `/proc`.
- **Unified App Cards & PM2 Integration**:
  - Menggabungkan Web Apps dan PM2 Process dalam satu kartu interaktif.
  - Tautan langsung dinamis (menyesuaikan hostname klien atau dikunci ke `127.0.0.1` untuk service lokal dengan SSH Port Forwarding).
  - Badge live CPU, RAM, dan Uptime aplikasi.
  - Tombol kontrol cepat: **Restart (↻)**, **Stop (■)**, dan **Start (▶)**.
- **Interactive Quick Log Viewer**:
  - Tombol **`📄 log`** pada setiap kartu PM2 untuk membuka modal terminal log interaktif.
  - Menampilkan 50–100 baris log stdout/stderr PM2 terbaru lengkap dengan tombol **Refresh** dan **Copy to Clipboard**.
- **Core Systemd Services Watcher**:
  - Memantau status unit systemd sistem maupun `--user` (`tailscaled`, `nginx`, `docker`, `ssh`, `postgresql`, `redis-server`, `hermes-gateway`).
- **Docker Containers Monitor**:
  - Secara otomatis mendeteksi dan menampilkan container Docker yang sedang berjalan beserta statusnya.
- **Service & Port Health Check**:
  - Pemindaian socket listening port via `ss` secara cerdas dan parallel health-check (HTTP/HTTPS/TCP).
- **Top Processes**:
  - Membaca 8 proses teratas dengan konsumsi RAM tertinggi dari `/proc/*/status` dengan pemetaan nama service otomatis.
- **WhatsApp Background Alert Notifier**:
  - Daemon worker background ringan (cek berkala tiap 60 detik) yang mengirimkan notifikasi via Hermes WhatsApp bridge (`http://127.0.0.1:3105/send`).
  - Mengirim alert ke nomor admin jika ada aplikasi PM2 yang *crashed*/*stopped* atau penggunaan RAM/Disk $> 90\%$.
  - Dilengkapi sistem **Anti-Spam Cooldown (30 menit)** dan **Recovery Notification** ketika kondisi kembali normal.
- **Autentikasi & Keamanan**:
  - Login terlindungi SHA-256 password hash.
  - Sesi berbasis cookie bertanda tangan HMAC-SHA256 (TTL 30 hari).
  - Token rahasia dapat dikonfigurasi via file `.token` atau environment variable.

---

## 🚀 Cara Menjalankan

### 1. Menjalankan Langsung (Direct)
```bash
python3 srv.py
```
Akses dashboard di browser melalui: `http://localhost:8899`

### 2. Menjalankan di Background dengan PM2 (Direkomendasikan)
```bash
# Start service
pm2 start srv.py --name monitor --interpreter python3

# Simpan agar otomatis hidup saat server reboot
pm2 save
```

---

## ⚙️ Konfigurasi Environment Variables (Opsional)

| Variable | Default | Keterangan |
| :--- | :--- | :--- |
| `PORT` | `8899` | Port HTTP listen server |
| `MONITOR_USER` | `fata` | Username login dashboard |
| `MONITOR_PASS` | `1232` | Password login dashboard |
| `MONITOR_TOKEN` | `.token` file / fallback | Secret key untuk penandatanganan cookie sesi HMAC |
| `MONITOR_WA_ADMIN` | Auto-detect dari Hermes `.env` | Nomor tujuan notifikasi WhatsApp (misal: `6281335004509`) |

---

## 📄 Lisensi
[MIT License](LICENSE)
