#!/usr/bin/env python3
import os
import sys
import shutil
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed

import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    messagebox.showerror("Error", "yt-dlp tidak terinstall.\nJalankan: pip install yt-dlp")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Programmatic theme overrides (indigo accent) ───────────────
_t = ctk.ThemeManager.theme
_t["CTk"]["fg_color"] = ["#f0f0f0", "#0e0e12"]
_t["CTkFrame"]["fg_color"] = ["#ffffff", "#16161c"]
_t["CTkFrame"]["top_fg_color"] = ["#fafafa", "#1c1c24"]
_t["CTkButton"]["fg_color"] = ["#6366f1", "#6366f1"]
_t["CTkButton"]["hover_color"] = ["#5558e3", "#7c7ff5"]
_t["CTkButton"]["corner_radius"] = 10
_t["CTkLabel"]["text_color"] = ["#1a1a1a", "#e4e4e7"]
_t["CTkEntry"]["fg_color"] = ["#f4f4f5", "#1a1a22"]
_t["CTkEntry"]["border_color"] = ["#d4d4d8", "#2a2a34"]
_t["CTkEntry"]["text_color"] = ["#1a1a1a", "#e4e4e7"]
_t["CTkEntry"]["placeholder_text_color"] = ["#a1a1aa", "#52525b"]
_t["CTkEntry"]["corner_radius"] = 10
_t["CTkComboBox"]["fg_color"] = ["#f4f4f5", "#1a1a22"]
_t["CTkComboBox"]["border_color"] = ["#d4d4d8", "#2a2a34"]
_t["CTkComboBox"]["text_color"] = ["#1a1a1a", "#e4e4e7"]
_t["CTkComboBox"]["button_color"] = ["#6366f1", "#6366f1"]
_t["CTkComboBox"]["button_hover_color"] = ["#5558e3", "#7c7ff5"]
_t["CTkComboBox"]["corner_radius"] = 10
_t["CTkProgressBar"]["fg_color"] = ["#e4e4e7", "#2a2a34"]
_t["CTkProgressBar"]["progress_color"] = ["#6366f1", "#818cf8"]
_t["CTkProgressBar"]["corner_radius"] = 8
_t["CTkRadioButton"]["fg_color"] = ["#6366f1", "#6366f1"]
_t["CTkRadioButton"]["hover_color"] = ["#5558e3", "#7c7ff5"]
_t["CTkTextbox"]["fg_color"] = ["#f4f4f5", "#1a1a22"]
_t["CTkTextbox"]["border_color"] = ["#d4d4d8", "#2a2a34"]
_t["CTkTextbox"]["text_color"] = ["#1a1a1a", "#e4e4e7"]
_t["CTkTextbox"]["corner_radius"] = 10
_t["CTkSegmentedButton"]["selected_color"] = ["#6366f1", "#6366f1"]
_t["CTkSegmentedButton"]["selected_hover_color"] = ["#5558e3", "#7c7ff5"]
_t["CTkSegmentedButton"]["unselected_color"] = ["#f4f4f5", "#1a1a22"]
_t["CTkSegmentedButton"]["unselected_hover_color"] = ["#e4e4e7", "#2a2a34"]
_t["CTkSegmentedButton"]["corner_radius"] = 10
_t["CTkSwitch"]["fg_color"] = ["#d4d4d8", "#2a2a34"]
_t["CTkSwitch"]["progress_color"] = ["#6366f1", "#6366f1"]
_t["CTkSlider"]["progress_color"] = ["#6366f1", "#818cf8"]
_t["CTkSlider"]["button_color"] = ["#6366f1", "#818cf8"]
_t["CTkOptionMenu"]["fg_color"] = ["#6366f1", "#6366f1"]
_t["CTkOptionMenu"]["button_color"] = ["#5558e3", "#5558e3"]
_t["CTkCheckBox"]["fg_color"] = ["#6366f1", "#6366f1"]
_t["CTkCheckBox"]["hover_color"] = ["#5558e3", "#7c7ff5"]
_t["CTkFont"]["family"] = "Roboto"

# ── Color palette ──────────────────────────────────────────────
ACCENT       = "#6366f1"
ACCENT_HOVER = "#5558e3"
ACCENT_LIGHT = "#818cf8"
SUCCESS      = "#10b981"
ERROR        = "#ef4444"
WARNING      = "#f59e0b"
ROSE         = "#f43f5e"
ROSE_HOVER   = "#e11d48"
TEXT         = "#e4e4e7"
TEXT_SEC     = "#a1a1aa"
TEXT_MUTED   = "#71717a"
CARD         = "#16161c"
CARD_ALT     = "#1c1c24"
BORDER       = "#27272f"

# ── Font definitions ───────────────────────────────────────────
F_TITLE    = ("Roboto", 24, "bold")
F_SUBTITLE = ("Roboto", 13)
F_SECTION  = ("Roboto", 12, "bold")
F_BODY     = ("Roboto", 13)
F_SMALL    = ("Roboto", 11)
F_BTN      = ("Roboto", 13, "bold")
F_BTN_SM   = ("Roboto", 12, "bold")
F_MONO     = ("Consolas", 11)

MP3_QUALITIES = {
    '128': '128kbps (Cepat)',
    '192': '192kbps (Recommended)',
    '256': '256kbps (High)',
    '320': '320kbps (Max)',
    'vbr0': 'VBR 0 (Terbaik)',
}

MP4_QUALITIES = {
    '720': '720p (HD)',
    '1080': '1080p (Full HD)',
    'best': 'Best (Tertinggi)',
    'max': 'Max (Kompresi)',
}

CONCURRENT_WORKERS = min(32, (os.cpu_count() or 4) + 4)


class DownloadCancelled(Exception):
    pass


def find_ffmpeg():
    if shutil.which('ffmpeg'):
        return shutil.which('ffmpeg')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_names = ['ffmpeg', 'ffmpeg.exe']
    common_paths = [
        os.path.join(script_dir, 'ffmpeg', 'bin'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'ffmpeg', 'bin'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'ffmpeg', 'bin'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'WinGet', 'Packages', 'FFmpeg', 'ffmpeg', 'bin'),
    ]
    for path in common_paths:
        for name in ffmpeg_names:
            full_path = os.path.join(path, name)
            if os.path.exists(full_path):
                return full_path
    return None


def build_ydl_opts(output_dir, ffmpeg_path, download_format, quality):
    ydl_opts = {
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'throttled_rate': '100M',
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    if download_format == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        if ffmpeg_path:
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            ffprobe = shutil.which('ffprobe') or shutil.which('ffprobe.exe') or os.path.exists(os.path.join(ffmpeg_dir, 'ffprobe.exe'))
            if ffprobe:
                pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}
                if quality == 'vbr0':
                    pp['preferredquality'] = '320'
                    ydl_opts['postprocessor_args'] = {'ffmpeg': ['-q:a', '0']}
                else:
                    pp['preferredquality'] = quality
                ydl_opts['postprocessors'] = [pp]
            ydl_opts['ffmpeg_location'] = ffmpeg_dir
    else:
        if ffmpeg_path:
            height_fmt = {
                '720': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
                '1080': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
                'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'max': 'bestvideo+bestaudio/best',
            }
            ydl_opts['format'] = height_fmt.get(quality, height_fmt['1080'])
            ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)
        else:
            fallback = {
                '720': 'best[height<=720][ext=mp4]/best[height<=720]',
                '1080': 'best[height<=1080][ext=mp4]/best[height<=1080]',
                'best': 'best[ext=mp4]/best',
                'max': 'best',
            }
            ydl_opts['format'] = fallback.get(quality, fallback['1080'])

    return ydl_opts


class DownloadThread(threading.Thread):
    def __init__(self, url, output_dir, download_format, ffmpeg_path, quality, finished_callback, progress_callback=None, index=0, total=1, cancel_event=None):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.download_format = download_format
        self.ffmpeg_path = ffmpeg_path
        self.quality = quality
        self.finished_callback = finished_callback
        self.progress_callback = progress_callback
        self.index = index
        self.total = total
        self.cancel_event = cancel_event or threading.Event()
        self.daemon = True

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)
        ydl_opts = build_ydl_opts(self.output_dir, self.ffmpeg_path, self.download_format, self.quality)

        if self.progress_callback:
            def hook(d):
                if self.cancel_event.is_set():
                    raise DownloadCancelled("Download dibatalkan oleh pengguna")
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    pct = (downloaded / total * 100) if total > 0 else 0
                    speed = d.get('_speed_str', '?')
                    eta = d.get('_eta_str', '?')
                    self.progress_callback(pct, speed, eta, 'downloading')
                elif d['status'] == 'finished':
                    self.progress_callback(100, '', '', 'processing')
            ydl_opts['progress_hooks'] = [hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.finished_callback(True, self.url, self.index, self.total, None)
        except DownloadCancelled:
            self.finished_callback(False, self.url, self.index, self.total, "Dibatalkan")
        except Exception as e:
            self.finished_callback(False, self.url, self.index, self.total, str(e))


# ════════════════════════════════════════════════════════════════
#  UI HELPERS
# ════════════════════════════════════════════════════════════════
def make_card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                        border_width=1, border_color=BORDER, **kw)

def make_section_label(parent, text):
    return ctk.CTkLabel(parent, text=text, font=F_SECTION,
                        text_color=TEXT_SEC, anchor="w")

def make_primary_btn(parent, text, command, width=160):
    return ctk.CTkButton(parent, text=text, command=command, width=width,
                         font=F_BTN, height=40, corner_radius=10,
                         fg_color=ACCENT, hover_color=ACCENT_HOVER)

def make_ghost_btn(parent, text, command, width=120):
    return ctk.CTkButton(parent, text=text, command=command, width=width,
                         font=F_BTN_SM, height=40, corner_radius=10,
                         fg_color=CARD_ALT, hover_color=BORDER,
                         text_color=TEXT_SEC, border_width=1, border_color=BORDER)

def make_danger_btn(parent, text, command, width=100):
    return ctk.CTkButton(parent, text=text, command=command, width=width,
                         font=F_BTN_SM, height=40, corner_radius=10,
                         fg_color="#dc2626", hover_color="#b91c1c", text_color="#ffffff")


# ════════════════════════════════════════════════════════════════
#  APP
# ════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Downloader")
        self.geometry("750x720")
        self.minsize(690, 660)

        self.ffmpeg_path = find_ffmpeg()
        self.download_format = "mp3"
        self.mp3_quality = "192"
        self.mp4_quality = "1080"
        self.output_dir = os.path.join(SCRIPT_DIR, "downloads")
        os.makedirs(self.output_dir, exist_ok=True)

        self._cancel_event = threading.Event()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.after(100, self.setup_ui)

    # ── Layout skeleton ────────────────────────────────────────
    def setup_ui(self):
        self._build_header()
        self._build_tabs()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        header.grid_columnconfigure(0, weight=1)

        # Accent bar
        bar = ctk.CTkFrame(header, height=3, fg_color=ACCENT, corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        # Title row
        title = ctk.CTkLabel(header, text="🎬 YouTube Downloader",
                             font=F_TITLE, text_color=TEXT, anchor="w")
        title.grid(row=1, column=0, sticky="w")

        sub = ctk.CTkLabel(header, text=f"Download video & audio dari YouTube • {CONCURRENT_WORKERS}x parallel workers ready",
                           font=F_SUBTITLE, text_color=TEXT_SEC, anchor="w")
        sub.grid(row=2, column=0, sticky="w", pady=(0, 10))

        # FFmpeg badge
        badge_frame = ctk.CTkFrame(header, fg_color="transparent")
        badge_frame.grid(row=3, column=0, sticky="w")

        ok = self.ffmpeg_path is not None
        dot_color = SUCCESS if ok else ERROR
        badge_text = "✅ FFmpeg Terdeteksi" if ok else "❌ FFmpeg Tidak Ditemukan — fitur terbatas"

        dot = ctk.CTkLabel(badge_frame, text="\u25CF", text_color=dot_color,
                           font=("Roboto", 8))
        dot.pack(side="left", padx=(0, 5))

        ctk.CTkLabel(badge_frame, text=badge_text, text_color=dot_color,
                     font=F_SMALL).pack(side="left")

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(
            self, corner_radius=14,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=CARD_ALT,
            segmented_button_unselected_hover_color=BORDER,
            fg_color=CARD,
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=24, pady=12)

        tab_single = self.tabview.add("📥 Single")
        tab_batch = self.tabview.add("📦 Batch")
        tab_settings = self.tabview.add("⚙️ Pengaturan")

        self.setup_single_tab(tab_single)
        self.setup_batch_tab(tab_batch)
        self.setup_settings_tab(tab_settings)

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent", height=24)
        footer.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)

        self.footer_label = ctk.CTkLabel(footer, text="", font=F_SMALL,
                                         text_color=TEXT_MUTED, anchor="w")
        self.footer_label.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(footer, text="yt-dlp  ·  customtkinter  ·  🎬",
                     font=("Roboto", 10), text_color=TEXT_MUTED
                     ).grid(row=0, column=1, sticky="e")

        self.update_footer()

    def update_footer(self):
        q = self.get_current_quality_label()
        fmt = "🎵 MP3" if self.download_format == 'mp3' else "🎬 MP4"
        self.footer_label.configure(
            text=f"{fmt}  ·  Kualitas: {q}  ·  Parallel: {CONCURRENT_WORKERS}x")

    # ── Single tab ─────────────────────────────────────────────
    def setup_single_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Card: URL input
        card_url = make_card(parent)
        card_url.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        card_url.grid_columnconfigure(0, weight=1)

        make_section_label(card_url, "🔗 URL YOUTUBE").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        self.url_entry = ctk.CTkEntry(card_url, placeholder_text="https://www.youtube.com/watch?v=...",
                                      height=38, font=F_BODY)
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        self.single_info = ctk.CTkLabel(card_url, text="", font=F_SMALL,
                                        text_color=TEXT_MUTED, anchor="w")
        self.single_info.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 14))

        # Card: Progress
        card_prog = make_card(parent)
        card_prog.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))
        card_prog.grid_columnconfigure(0, weight=1)

        self.single_progress = ctk.CTkProgressBar(card_prog, height=10)
        self.single_progress.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))
        self.single_progress.set(0)

        self.single_status = ctk.CTkLabel(card_prog, text="📋 Siap untuk download",
                                          font=F_SMALL, text_color=TEXT_MUTED, anchor="w")
        self.single_status.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 16))

        # Buttons
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=(4, 8))

        self.single_btn = make_primary_btn(btn_frame, "⬇ Download", self.start_single_download, width=170)
        self.single_btn.pack(side="left", padx=6)

        self.single_cancel_btn = make_danger_btn(btn_frame, "⏹ Batal", self.cancel_single, width=100)
        self.single_cancel_btn.pack(side="left", padx=6)
        self.single_cancel_btn.pack_forget()

        make_ghost_btn(btn_frame, "📂 Buka Folder", self.open_downloads, width=140).pack(side="left", padx=6)

        self.update_single_info()

    # ── Batch tab ──────────────────────────────────────────────
    def setup_batch_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Card: File selection
        card_file = make_card(parent)
        card_file.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        card_file.grid_columnconfigure(0, weight=1)

        make_section_label(card_file, "📁 FILE URL LIST").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        file_sel = ctk.CTkFrame(card_file, fg_color="transparent")
        file_sel.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        file_sel.grid_columnconfigure(0, weight=1)

        self.batch_file_entry = ctk.CTkEntry(file_sel, placeholder_text="Pilih file .txt berisi URL...",
                                             height=38, font=F_BODY)
        self.batch_file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(file_sel, text="Browse", width=80, height=38,
                      font=F_BTN_SM, corner_radius=10,
                      fg_color=CARD_ALT, hover_color=BORDER,
                      text_color=TEXT_SEC, border_width=1, border_color=BORDER,
                      command=self.browse_file).grid(row=0, column=1)

        self.batch_info = ctk.CTkLabel(card_file, text="", font=F_SMALL,
                                       text_color=TEXT_MUTED, anchor="w")
        self.batch_info.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 14))

        # Card: Progress
        card_prog = make_card(parent)
        card_prog.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))
        card_prog.grid_columnconfigure(0, weight=1)

        self.batch_progress = ctk.CTkProgressBar(card_prog, height=10)
        self.batch_progress.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))
        self.batch_progress.set(0)

        self.batch_status = ctk.CTkLabel(card_prog, text="📋 Siap untuk batch download",
                                         font=F_SMALL, text_color=TEXT_MUTED, anchor="w")
        self.batch_status.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 16))

        # Card: Log (expands)
        card_log = make_card(parent)
        card_log.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 8))
        card_log.grid_columnconfigure(0, weight=1)
        card_log.grid_rowconfigure(1, weight=1)

        make_section_label(card_log, "📊 LOG PROGRESS").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        self.batch_detail = ctk.CTkTextbox(card_log, font=F_MONO,
                                           fg_color="#12121a", text_color=TEXT, border_width=0)
        self.batch_detail.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.batch_detail.insert("end", "Siap menampilkan log download...\n")

        # Buttons
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=(4, 8))

        self.batch_btn = make_primary_btn(btn_frame, "🚀 Mulai Batch", self.start_batch_download, width=170)
        self.batch_btn.pack(side="left", padx=6)

        self.batch_cancel_btn = make_danger_btn(btn_frame, "⏹ Batal", self.cancel_batch, width=100)
        self.batch_cancel_btn.pack(side="left", padx=6)
        self.batch_cancel_btn.pack_forget()

        make_ghost_btn(btn_frame, "📂 Buka Folder", self.open_downloads, width=140).pack(side="left", padx=6)

        self.update_batch_info()

    # ── Settings tab ───────────────────────────────────────────
    def setup_settings_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        # ── Card: Format ───────────────────────────────────────
        card_fmt = make_card(parent)
        card_fmt.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        card_fmt.grid_columnconfigure(0, weight=1)

        make_section_label(card_fmt, "🎵 FORMAT DOWNLOAD").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        self.format_var = ctk.StringVar(value="MP3 (Audio)")
        self.format_seg = ctk.CTkSegmentedButton(
            card_fmt,
            values=["MP3 (Audio)", "MP4 (Video)"],
            variable=self.format_var,
            command=self.on_format_change,
            height=38, corner_radius=10,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=CARD_ALT, unselected_hover_color=BORDER,
            text_color=TEXT, font=F_BTN_SM,
        )
        self.format_seg.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))

        # ── Card: Quality ──────────────────────────────────────
        card_q = make_card(parent)
        card_q.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))
        card_q.grid_columnconfigure(0, weight=1)

        make_section_label(card_q, "💾 KUALITAS").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        self.mp3_q_frame = ctk.CTkFrame(card_q, fg_color="transparent")
        self.mp3_q_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.mp3_q_frame.grid_columnconfigure(0, weight=1)

        self.mp3_quality_var = ctk.StringVar(value="192")
        self.mp3_combo = ctk.CTkComboBox(
            self.mp3_q_frame, values=list(MP3_QUALITIES.values()),
            command=self.on_mp3_quality_change, height=38,
            font=F_BODY, dropdown_font=F_BODY,
        )
        self.mp3_combo.grid(row=0, column=0, sticky="ew")
        self.mp3_combo.set(MP3_QUALITIES["192"])

        self.mp4_q_frame = ctk.CTkFrame(card_q, fg_color="transparent")
        self.mp4_q_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.mp4_q_frame.grid_columnconfigure(0, weight=1)

        self.mp4_quality_var = ctk.StringVar(value="1080")
        self.mp4_combo = ctk.CTkComboBox(
            self.mp4_q_frame, values=list(MP4_QUALITIES.values()),
            command=self.on_mp4_quality_change, height=38,
            font=F_BODY, dropdown_font=F_BODY,
        )
        self.mp4_combo.grid(row=0, column=0, sticky="ew")
        self.mp4_combo.set(MP4_QUALITIES["1080"])

        self._toggle_quality_frames()

        # Parallel info
        ctk.CTkLabel(card_q, text=f"🔄 Parallel Batch: {CONCURRENT_WORKERS}x download",
                     font=F_SMALL, text_color=TEXT_MUTED, anchor="w"
                     ).grid(row=3, column=0, sticky="w", padx=16, pady=(0, 14))

        # ── Card: Output directory ─────────────────────────────
        card_dir = make_card(parent)
        card_dir.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 8))
        card_dir.grid_columnconfigure(0, weight=1)

        make_section_label(card_dir, "📂 FOLDER DOWNLOAD").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        dir_frame = ctk.CTkFrame(card_dir, fg_color="transparent")
        dir_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        dir_frame.grid_columnconfigure(0, weight=1)

        self.dir_label = ctk.CTkLabel(dir_frame, text=self.output_dir, font=F_SMALL,
                                      text_color=TEXT_MUTED, anchor="w", wraplength=400)
        self.dir_label.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(dir_frame, text="Ganti", width=70, height=34,
                      font=F_BTN_SM, corner_radius=10,
                      fg_color=CARD_ALT, hover_color=BORDER,
                      text_color=TEXT_SEC, border_width=1, border_color=BORDER,
                      command=self.change_output_dir).grid(row=0, column=1)

        # ── Donasi ─────────────────────────────────────────────
        donasi_btn = ctk.CTkButton(parent, text="❤  Donasi", width=140, height=40,
                                   font=F_BTN, corner_radius=10,
                                   fg_color=ROSE, hover_color=ROSE_HOVER,
                                   command=self.open_donasi)
        donasi_btn.grid(row=3, column=0, pady=(8, 12))

    # ── Toggle & callbacks ─────────────────────────────────────
    def _toggle_quality_frames(self):
        is_mp3 = "MP3" in self.format_var.get()
        if is_mp3:
            self.mp3_q_frame.grid()
            self.mp4_q_frame.grid_remove()
        else:
            self.mp3_q_frame.grid_remove()
            self.mp4_q_frame.grid()

    def on_format_change(self, choice=None):
        self.download_format = "mp3" if "MP3" in self.format_var.get() else "mp4"
        self._toggle_quality_frames()
        self.update_single_info()
        self.update_batch_info()
        self.update_footer()

    def on_mp3_quality_change(self, choice):
        rev = {v: k for k, v in MP3_QUALITIES.items()}
        self.mp3_quality = rev.get(choice, '192')
        self.update_single_info()
        self.update_batch_info()
        self.update_footer()

    def on_mp4_quality_change(self, choice):
        rev = {v: k for k, v in MP4_QUALITIES.items()}
        self.mp4_quality = rev.get(choice, '1080')
        self.update_single_info()
        self.update_batch_info()
        self.update_footer()

    def get_current_quality_label(self):
        if self.download_format == 'mp3':
            return MP3_QUALITIES.get(self.mp3_quality, self.mp3_quality)
        else:
            return MP4_QUALITIES.get(self.mp4_quality, self.mp4_quality)

    def update_single_info(self):
        q = self.get_current_quality_label()
        fmt = "🎵 MP3" if self.download_format == 'mp3' else "🎬 MP4"
        self.single_info.configure(text=f"Format: {fmt}  ·  Kualitas: {q}")

    def update_batch_info(self):
        q = self.get_current_quality_label()
        fmt = "🎵 MP3" if self.download_format == 'mp3' else "🎬 MP4"
        self.batch_info.configure(text=f"Format: {fmt}  ·  Kualitas: {q}  ·  Parallel: {CONCURRENT_WORKERS}x")

    # ── File / directory helpers ───────────────────────────────
    def change_output_dir(self):
        path = filedialog.askdirectory(initialdir=self.output_dir, title="Pilih folder download")
        if path:
            self.output_dir = path
            self.dir_label.configure(text=path)

    def browse_file(self):
        path = filedialog.askopenfilename(title="Pilih file .txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self.batch_file_entry.delete(0, "end")
            self.batch_file_entry.insert(0, path)

    def open_downloads(self):
        os.makedirs(self.output_dir, exist_ok=True)
        if sys.platform == "darwin":
            os.system(f'open "{self.output_dir}"')
        elif sys.platform == "win32":
            os.startfile(self.output_dir)
        else:
            try:
                import subprocess
                subprocess.Popen(['xdg-open', self.output_dir],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                self.batch_status.configure(text="Error: xdg-open tidak ditemukan.", text_color=ERROR)

    def open_donasi(self):
        webbrowser.open("https://sociabuzz.com/trisnosanjaya")

    # ── Single download ────────────────────────────────────────
    def start_single_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Peringatan", "URL tidak boleh kosong!")
            return

        self._cancel_event.clear()
        self.single_btn.configure(state="disabled", text="⏳ Downloading...")
        self.single_cancel_btn.pack(side="left", padx=6)
        self.single_progress.set(0)
        self.single_status.configure(text=f"⬇ Mendownload: {url[:50]}...", text_color=ACCENT_LIGHT)

        quality = self.mp3_quality if self.download_format == 'mp3' else self.mp4_quality

        def on_progress(pct, speed, eta, status):
            self.after(0, lambda: self._update_single_progress(pct, speed, eta, status))

        DownloadThread(
            url, self.output_dir, self.download_format, self.ffmpeg_path, quality,
            finished_callback=self.single_finished,
            progress_callback=on_progress,
            cancel_event=self._cancel_event,
        ).start()

    def cancel_single(self):
        self._cancel_event.set()
        self.single_status.configure(text="⏹ Membatalkan...", text_color=WARNING)

    def _update_single_progress(self, pct, speed, eta, status):
        self.single_progress.set(pct / 100)
        if status == 'processing':
            self.single_status.configure(text="⏳ Memproses audio... (FFmpeg)", text_color=WARNING)
        else:
            self.single_status.configure(text=f"⬇ {pct:.1f}%  ·  {speed}  ·  ETA {eta}", text_color=ACCENT_LIGHT)

    def single_finished(self, success, url, *args):
        self.after(0, lambda: self._single_finished_ui(success, url, args))

    def _single_finished_ui(self, success, url, args):
        self.single_progress.set(1 if success else 0)
        self.single_cancel_btn.pack_forget()
        self.single_btn.configure(state="normal", text="⬇ Download")

        if success:
            self.single_status.configure(text="✓ Selesai! File tersimpan di folder downloads/", text_color=SUCCESS)
        else:
            err = args[-1] if len(args) > 2 and args[-1] else "Unknown error"
            self.single_status.configure(text=f"✗ Gagal: {err[:60]}", text_color=ERROR)

    # ── Batch download ─────────────────────────────────────────
    def start_batch_download(self):
        file_path = self.batch_file_entry.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("Peringatan", "File tidak ditemukan!")
            return

        with open(file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        if not urls:
            messagebox.showwarning("Peringatan", "Tidak ada URL valid dalam file!")
            return

        self._cancel_event.clear()
        self.total_batch = len(urls)
        self.batch_success = 0

        self.batch_btn.configure(state="disabled", text="⏳ Memproses...")
        self.batch_cancel_btn.pack(side="left", padx=6)
        self.batch_progress.set(0)
        self.batch_detail.delete("0.0", "end")
        self.batch_detail.insert("end", f"🚀 Memulai batch {self.total_batch} download ({CONCURRENT_WORKERS}x parallel)...\n")
        self.batch_status.configure(text=f"0/{self.total_batch} selesai", text_color=ACCENT_LIGHT)

        self._run_parallel_batch(urls)

    def cancel_batch(self):
        self._cancel_event.set()
        self.batch_status.configure(text="⏹ Membatalkan...", text_color=WARNING)

    def _run_parallel_batch(self, urls):
        quality = self.mp3_quality if self.download_format == 'mp3' else self.mp4_quality
        self._batch_progress_lines = {}

        def on_item_progress(idx, pct, speed, eta, status):
            self.after(0, lambda: self._update_batch_item_progress(idx, pct, speed, eta, status))

        def on_item_done(success, url, idx, total, error):
            self.after(0, lambda: self._batch_item_done(success, url, idx, total, error))

        def worker(url, idx, total):
            t = DownloadThread(
                url, self.output_dir, self.download_format, self.ffmpeg_path, quality,
                finished_callback=lambda s, u, i, t, e: on_item_done(s, u, i, t, e),
                progress_callback=lambda p, s, e, st: on_item_progress(idx, p, s, e, st),
                index=idx, total=total, cancel_event=self._cancel_event,
            )
            t.run()

        threading.Thread(target=self._batch_worker, args=(urls, worker), daemon=True).start()

    def _update_batch_item_progress(self, idx, pct, speed, eta, status):
        line_num = self._batch_progress_lines.get(idx)
        if line_num is None:
            self.batch_detail.insert("end", f"[#{idx+1}] 0% | ...\n")
            self._batch_progress_lines[idx] = int(self.batch_detail.index("end-1c").split('.')[0])
            line_num = self._batch_progress_lines[idx]

        if status == 'processing':
            text = f"[#{idx+1}] ⏳ Memproses audio... (FFmpeg)\n"
        else:
            text = f"[#{idx+1}] {pct:.1f}% | {speed} | ETA {eta}\n"

        self.batch_detail.delete(f"{line_num}.0", f"{line_num}.0 lineend")
        self.batch_detail.insert(f"{line_num}.0", text)
        self.batch_detail.see("end")

    def _batch_worker(self, urls, worker_fn):
        total = len(urls)
        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            fut_map = {
                executor.submit(worker_fn, url, idx, total): (url, idx)
                for idx, url in enumerate(urls)
            }
            for future in as_completed(fut_map):
                pass

        self.after(0, self._batch_all_done)

    def _batch_item_done(self, success, url, idx, total, error):
        self.batch_success += 1 if success else 0
        done = int(self.batch_progress.get() * total) + 1

        line_num = self._batch_progress_lines.get(idx)
        if line_num:
            if success:
                self.batch_detail.delete(f"{line_num}.0", f"{line_num}.0 lineend")
                self.batch_detail.insert(f"{line_num}.0", f"[#{idx+1}] ✓ OK] {url[:40]}...\n")
            else:
                err = error or "Unknown"
                self.batch_detail.delete(f"{line_num}.0", f"{line_num}.0 lineend")
                self.batch_detail.insert(f"{line_num}.0", f"[#{idx+1}] ✗ FAIL] {url[:40]}... - {err[:30]}\n")

        self.batch_detail.see("end")
        self.batch_progress.set(done / total)
        self.batch_status.configure(text=f"{done}/{total} selesai", text_color=ACCENT_LIGHT)

    def _batch_all_done(self):
        total = self.total_batch
        self.batch_btn.configure(state="normal", text="🚀 Mulai Batch")
        self.batch_cancel_btn.pack_forget()
        if self.batch_success == total:
            self.batch_status.configure(
                text=f"✓ Batch selesai! {self.batch_success}/{total} berhasil.",
                text_color=SUCCESS)
        else:
            self.batch_status.configure(
                text=f"✗ Batch selesai! {self.batch_success}/{total} berhasil.",
                text_color=ERROR)


if __name__ == "__main__":
    app = App()
    app.mainloop()
