# ⚙️ Monitor Ubuntu

Dashboard monitoring server Linux single-file yang ringan, cepat, dan tanpa dependensi eksternal (menggunakan Python Standard Library saja).

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## ✨ Fitur Utama

- **Zero External Dependencies**: Dibangun murni menggunakan modul bawaan Python (`ThreadingHTTPServer`, `http.client`, `hashlib`, `hmac`, `subprocess`, dll.).
- **Real-time Metrics**: Memantau metrik CPU (dari `/proc/stat`), RAM (`/proc/meminfo`), Disk (`shutil.disk_usage`), Load Average, Uptime, dan Total Proses.
- **Service & Port Health Check**: Memindai socket aktif via `ss` dan melakukan health check HTTP/HTTPS/TCP paralel ke service lokal (Nginx, Postgres, Redis, PM2 apps, Hermes, dll.).
- **Integrasi PM2**: Menampilkan status aplikasi PM2, penggunaan memori/CPU, serta mendukung kontrol langsung (`start`, `stop`, `restart`) dari web UI.
- **Top Processes**: Membaca penggunaan RAM proses tertinggi di server dan secara cerdas melabeli nama service (PM2 / proses background).
- **Web App Launcher**: Mendeteksi URL host secara dinamis (mendukung akses via Localhost, LAN IP, atau Tailscale).
- **Autentikasi & Keamanan**:
  - Login terlindungi SHA-256 password hash.
  - Sesi berbasis cookie bertanda tangan HMAC-SHA256.
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
| `PORT` | `8899` | Port listen server |
| `MONITOR_TOKEN` | `.token` file / fallback | Secret key untuk penandatanganan cookie sesi HMAC |
| `MONITOR_USER` | `fata` | Username login dashboard |
| `MONITOR_PASS` | `1232` | Password login dashboard |

---

## 📄 Lisensi
[MIT License](LICENSE)
