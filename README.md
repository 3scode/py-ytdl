# CLI YouTube Downloader

Downloader YouTube dengan dual-interface (CLI + GUI). Download video/audio dari YouTube dengan mudah — single atau batch 3x paralel.

## Fitur

- **Dua Antarmuka** — CLI (Rich) & GUI (CustomTkinter)
- **Single Download** — Download satu URL langsung
- **Batch Download** — Download banyak URL dari file `.txt` (3 thread paralel)
- **Progress Real-time** — Progress bar, kecepatan & ETA langsung
- **Kualitas MP3** — 128kbps / 192kbps / 320kbps / VBR 0
- **Kualitas MP4** — 720p (HD) / 1080p (Full HD) / Best
- **Auto FFmpeg** — Download & install FFmpeg otomatis (~60MB)
- **Bypass 403 YouTube** — Pakai `android` + `web` player client agar tidak kena throttle
- **Donasi** — Dukung developer via Sociabuzz

## Requirements

- Python 3.8+
- `pip install -r requirements.txt`

## Instalasi

### Windows

1. **Install Python**
   - Download Python 3.8+ dari [python.org](https://www.python.org/downloads/)
   - **Centang** "Add Python to PATH" saat instalasi
   - Verifikasi: buka `CMD` atau `PowerShell`, ketik:
     ```cmd
     python --version
     ```

2. **Clone atau Download Repo**
   ```cmd
   git clone https://github.com/codebytrisno/cli-ytdownloader.git
   cd cli-ytdownloader
   ```
   Atau download ZIP dan extract.

3. **Install Dependencies**
   ```cmd
   pip install -r requirements.txt
   ```

4. **Jalankan**
   ```cmd
   python cli.py    # CLI version
   python gui.py    # GUI version
   ```

5. **FFmpeg** — Jika belum terinstall, program akan otomatis mendownload FFmpeg saat pertama kali dijalankan. Atau bisa juga [download manual](https://ffmpeg.org/download.html) dan taruh di `ffmpeg/bin/`.

### Linux

```bash
pip install -r requirements.txt
python cli.py
python gui.py
```

## Cara Pakai

### CLI Version
```bash
python cli.py
```
Pilih format (MP3/MP4), kualitas, lalu pilih menu:
1. **Single Download** — Masukkan URL YouTube
2. **File List Download** — Masukkan path file `.txt` berisi daftar URL (batch 3x paralel)
3. **Donasi** — Buka halaman donasi
4. **Keluar**

### GUI Version
```bash
python gui.py
```
Tersedia 3 tab:
- **Single** — Input URL, download dengan progress bar
- **Batch** — Pilih file `.txt`, batch download dengan log real-time
- **Pengaturan** — Ganti format/kualitas, folder output

### Format File Batch

Buat file teks (contoh: `list.txt`) dengan satu URL YouTube per baris:

```txt
# Komentar (baris diawali # akan diabaikan)
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/QkPk1mXIMZo
```

File `list.txt` yang tersedia saat ini berisi 50 lagu tarling (musik khas Cirebon/Indramayu).

## Pilihan Kualitas

| MP3 | Bitrate |
|-----|---------|
| 128kbps | Cepat, file kecil |
| 192kbps | Recommended (default) |
| 320kbps | Kualitas tinggi |
| VBR 0 | Kualitas terbaik (variable bitrate) |

| MP4 | Resolusi |
|-----|----------|
| 720p | HD |
| 1080p | Full HD (default) |
| Best | Tertinggi yang tersedia |

## Cara Kerja Auto FFmpeg

1. Program cek PATH, lokasi instalasi umum, dan folder lokal `ffmpeg/bin/`
2. Kalau tidak ketemu, muncul prompt untuk download otomatis (~60MB)
3. Download `ffmpeg-release-essentials.zip` dari gyan.dev dengan progress bar
4. Extract `ffmpeg.exe` dan `ffprobe.exe` ke `ffmpeg/bin/` (portable, tidak perlu admin)
5. Langsung bisa dipakai — tersimpan permanen

## Struktur Project

```
cli-ytdownloader/
├── cli.py   # CLI version (Rich)
├── gui.py   # GUI version (CustomTkinter)
├── requirements.txt      # yt-dlp, rich, customtkinter
├── README.md             # Dokumentasi
├── list.txt              # Daftar URL untuk batch download
├── downloads/            # Hasil download (gitignored)
└── ffmpeg/               # FFmpeg auto-install (gitignored)
    └── bin/
        ├── ffmpeg.exe
        └── ffprobe.exe
```

## Lisensi

MIT License — Silakan pakai dan modifikasi!

## Dukungan

Kalau tool ini bermanfaat, dukung developer:
- [Donate via Sociabuzz](https://sociabuzz.com/trisnosanjaya)
