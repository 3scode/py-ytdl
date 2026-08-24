#!/usr/bin/env python3
import os
import sys
import shutil
import webbrowser
import urllib.request
import zipfile
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn,
)
from rich.align import Align
from rich.rule import Rule
from rich import print as rprint

try:
    import yt_dlp
except ImportError:
    rprint("[bold red]Error: yt-dlp tidak terinstall. Jalankan: pip install yt-dlp[/]")
    sys.exit(1)

console = Console()

# Bitrate/kualitas audio (dipakai untuk MP3, M4A/AAC, dan OPUS)
AUDIO_QUALITIES = {
    '128': {'label': '128kbps (Cepat, ukuran kecil)', 'value': '128'},
    '192': {'label': '192kbps (Recommended)', 'value': '192'},
    '256': {'label': '256kbps (High Quality)', 'value': '256'},
    '320': {'label': '320kbps (Max Quality)', 'value': '320'},
    'vbr0': {'label': 'VBR 0 (Terbaik - variable bitrate)', 'value': 'vbr0'},
}

MP4_QUALITIES = {
    '720': {'label': '720p (HD - cepat, kecil, codec modern)', 'value': '720'},
    '1080': {'label': '1080p (Full HD - recommended)', 'value': '1080'},
    'best': {'label': 'Best (kualitas tertinggi)', 'value': 'best'},
    'max': {'label': 'Kompresi Maks (x265 + opus, sangat kecil)', 'value': 'max'},
}

# Worker batch dinamis berdasarkan jumlah core CPU
CONCURRENT_WORKERS = min(32, (os.cpu_count() or 4) + 4)

FORMAT_LABELS = {
    'mp3': 'MP3',
    'm4a': 'M4A (AAC)',
    'opus': 'OPUS',
    'mp4': 'MP4',
}

# Mapping kualitas MP3 (VBR libmp3lame) untuk kompresi agresif tanpa kehilangan kualitas
MP3_VBR_MAP = {
    '128': '7',
    '192': '4',
    '256': '2',
    '320': '0',
    'vbr0': '0',
}


def show_welcome():
    console.print()
    console.print(Panel(
        Align.center(
            "[bold cyan size=20]🎬 YT Downloader[/]\n\n"
            "[dim]Download video & audio dari YouTube dengan mudah[/]\n"
            f"[dim]{CONCURRENT_WORKERS}x parallel workers ready[/]"
        ),
        border_style="cyan",
        padding=(1, 3),
    ))


def show_menu(download_format, quality):
    fmt_text = FORMAT_LABELS.get(download_format, download_format.upper())
    if download_format == 'mp4':
        q_text = MP4_QUALITIES.get(quality, {}).get('label', quality)
    else:
        q_text = AUDIO_QUALITIES.get(quality, {}).get('label', quality)

    table = Table.grid(padding=1)
    table.add_column(style="cyan", justify="right")
    table.add_column(style="white")

    table.add_row("1.", "📥 Single Download")
    table.add_row("2.", "📦 File List Download")
    table.add_row("3.", "💝 Donasi")
    table.add_row("4.", "🚪 Keluar")

    panel = Panel(
        table,
        title=f"[bold green]🎵 CLI YouTube Downloader[/]",
        subtitle=f"[dim]{fmt_text} | {q_text} | {CONCURRENT_WORKERS}x parallel[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def donasi():
    console.print(Panel(
        "[green]🙏 Terima kasih untuk donasi![/] Membuka halaman donasi...",
        border_style="green",
    ))
    webbrowser.open("https://sociabuzz.com/trisnosanjaya")
    console.print("[dim]Jika browser tidak terbuka otomatis, kunjungi:[/]")
    console.print("[cyan]https://sociabuzz.com/trisnosanjaya[/]")


def build_ydl_opts(output_dir, ffmpeg_path, download_format, quality):
    ydl_opts = {
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # 1) Bypass throttling & percepat fragment download (optimasi performa)
        'concurrent_fragment_downloads': 10,
        'http_chunk_size': 10485760,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        # 2) Ketahanan koneksi & pengaturan habis waktu (fix crash "read operation timed out")
        'socket_timeout': 60,
        'retries': 10,
        'fragment_retries': 10,
        'file_access_retries': 5,
        'retry_sleep': {'http': 3, 'fragment': 3, 'file_access': 3},
        # 3) Dukungan lanjutkan (resume otomatis dari titik terakhir)
        'continuedl': True,
    }

    # Integrasi aria2c (external downloader) jika tersedia
    ydl_opts.update(get_aria2c_opts())

    if download_format in ('mp3', 'm4a', 'opus'):
        # 2) Kompresi audio dengan codec modern (Opus / AAC) atau MP3 teroptimasi
        ydl_opts['format'] = 'bestaudio/best'
        if ffmpeg_path:
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            ffprobe = (
                shutil.which('ffprobe')
                or shutil.which('ffprobe.exe')
                or os.path.exists(os.path.join(ffmpeg_dir, 'ffprobe.exe'))
            )
            if not ffprobe:
                console.print("[yellow]⚠️ ffprobe tidak ditemukan, pasca-proses audio dilewati.[/]")
            else:
                codec_map = {'mp3': 'mp3', 'm4a': 'aac', 'opus': 'opus'}
                pp = {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec_map[download_format],
                }
                if download_format == 'mp3':
                    # Kompresi agresif tanpa kehilangan kualitas via libmp3lame VBR
                    pp['preferredquality'] = quality if quality != 'vbr0' else '320'
                    vbr = MP3_VBR_MAP.get(quality, '4')
                    ydl_opts['postprocessor_args'] = {
                        'ffmpeg': ['-codec:a', 'libmp3lame', '-q:a', vbr],
                    }
                elif download_format == 'm4a':
                    pp['preferredquality'] = quality if quality != 'vbr0' else '256'
                else:  # opus -> kualitas jauh lebih baik pada ukuran sangat kecil
                    pp['preferredquality'] = quality if quality != 'vbr0' else '256'
                ydl_opts['postprocessors'] = [pp]
                ydl_opts['ffmpeg_location'] = ffmpeg_dir
    else:
        # 3) Kompresi video: prioritaskan codec efisiensi tinggi (AV1/VP9) -> H.265/H.264
        if ffmpeg_path:
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            modern = 'vcodec~="(av01|vp9)"'
            height_fmt = {
                '720': (
                    f'bestvideo[height<=720][{modern}][ext=webm]+bestaudio[ext=webm]'
                    f'/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]'
                    f'/best[height<=720]'
                ),
                '1080': (
                    f'bestvideo[height<=1080][{modern}][ext=webm]+bestaudio[ext=webm]'
                    f'/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]'
                    f'/best[height<=1080]'
                ),
                'best': (
                    f'bestvideo[{modern}][ext=webm]+bestaudio[ext=webm]'
                    f'/bestvideo[ext=mp4]+bestaudio[ext=m4a]'
                    f'/best'
                ),
                'max': 'bestvideo+bestaudio/best',
            }

            if quality == 'max':
                # Pengkodean ulang FFmpeg opsional: libx265 + libopus (Kompresi Maks)
                ydl_opts['format'] = height_fmt['max']
                ydl_opts['postprocessors'] = [
                    {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mkv'},
                ]
                ydl_opts['postprocessor_args'] = {
                    'ffmpeg': [
                        '-c:v', 'libx265', '-crf', '28', '-preset', 'veryslow',
                        '-c:a', 'libopus', '-b:a', '96k',
                        '-tag:v', 'hvc1', '-strict', '-2',
                    ],
                }
                console.print("[cyan]🗜️ Mode Kompresi Maks:[/] re-encode ke x265 + opus (mkv).")
            else:
                ydl_opts['format'] = height_fmt.get(quality, height_fmt['1080'])

            ydl_opts['ffmpeg_location'] = ffmpeg_dir
        else:
            fallback = {
                '720': 'best[height<=720][ext=mp4]/best[height<=720]',
                '1080': 'best[height<=1080][ext=mp4]/best[height<=1080]',
                'best': 'best[ext=mp4]/best',
                'max': 'best[ext=mp4]/best',
            }
            ydl_opts['format'] = fallback.get(quality, fallback['1080'])

    return ydl_opts


def download_audio(url, output_dir="downloads", ffmpeg_path=None, download_format='mp3', quality='192'):
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = build_ydl_opts(output_dir, ffmpeg_path, download_format, quality)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True, None
    except Exception as e:
        error_msg = str(e)
        if 'ffmpeg' in error_msg.lower() or 'ffprobe' in error_msg.lower():
            return False, "FFmpeg/ffprobe tidak ditemukan"
        if 'libx265' in error_msg.lower() or 'libopus' in error_msg.lower():
            return False, "FFmpeg Anda tidak mendukung libx265/libopus (pakai build full)"
        if 'aria2c' in error_msg.lower():
            return False, "aria2c gagal, coba nonaktifkan atau install aria2c"
        return False, str(e)


def single_download(ffmpeg_path=None, download_format='mp3', quality='192'):
    url = Prompt.ask("\n[bold cyan]📎 Masukkan URL YouTube[/]").strip()
    if not url:
        console.print("[bold red]❌ URL tidak boleh kosong![/]")
        return

    console.print(f"\n[bold]🎯 Mendownload:[/] [cyan]{url}[/]")

    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = build_ydl_opts(output_dir, ffmpeg_path, download_format, quality)

    fmt_label = FORMAT_LABELS.get(download_format, download_format.upper())
    q_label = AUDIO_QUALITIES.get(quality, MP4_QUALITIES.get(quality, {})).get('label', quality)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info) if info else "unknown"

            console.print(Panel(
                f"[bold green]✅ Download selesai![/]\n\n"
                f"[dim]File:[/] [cyan]{os.path.basename(filename)}[/]\n"
                f"[dim]Format:[/] {fmt_label} | {q_label}",
                border_style="green",
            ))
    except Exception as e:
        error_msg = str(e)
        if 'ffmpeg' in error_msg.lower() or 'ffprobe' in error_msg.lower():
            console.print(f"[bold red]❌ Error:[/] FFmpeg/ffprobe tidak ditemukan")
        elif 'libx265' in error_msg.lower() or 'libopus' in error_msg.lower():
            console.print(f"[bold red]❌ Error:[/] FFmpeg tidak mendukung libx265/libopus")
        else:
            console.print(f"[bold red]❌ Error:[/] {error_msg[:100]}")


def batch_download(ffmpeg_path=None, download_format='mp3', quality='192'):
    file_path = Prompt.ask("\n[bold cyan]📂 Masukkan path file .txt[/]").strip()

    if not os.path.exists(file_path):
        console.print(f"[bold red]❌ Error: File '{file_path}' tidak ditemukan![/]")
        return

    urls = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)

    if not urls:
        console.print("[bold red]❌ Tidak ada URL yang valid dalam file![/]")
        return

    total = len(urls)
    success_count = 0
    fail_count = 0
    console.print(f"\n[bold cyan]🚀 Memulai batch {total} download ({CONCURRENT_WORKERS}x parallel)...[/]")

    results = {}

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold]{task.description}[/]"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]0/{total} selesai", total=total)

        def process_url(url):
            succ, err = download_audio(url, ffmpeg_path=ffmpeg_path, download_format=download_format, quality=quality)
            return url, succ, err

        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            futures = {executor.submit(process_url, url): url for url in urls}
            for future in as_completed(futures):
                url, succ, err = future.result()
                if succ:
                    success_count += 1
                    results[url] = ("✅", None)
                else:
                    fail_count += 1
                    results[url] = ("❌", err)
                progress.update(task, advance=1,
                                description=f"[cyan]{success_count}/{total} berhasil, {fail_count} gagal")

    console.print(Rule(style="green"))
    panel_style = "green" if fail_count == 0 else "yellow"
    console.print(Panel(
        f"[bold green]{'✅ Batch selesai! Semua berhasil!' if fail_count == 0 else '⚠️ Batch selesai!'}\n\n"
        f"[green]Berhasil:[/] {success_count}  [red]Gagal:[/] {fail_count}  [dim]Total:[/] {total}",
        border_style=panel_style,
    ))

    if results:
        console.print("\n[bold]📋 Detail hasil:[/]")
        for url, (status, err) in results.items():
            short_url = url[:50] + "..." if len(url) > 50 else url
            if err:
                console.print(f"  [red]{status}[/] {short_url} — [dim]{err[:30]}[/]")
            else:
                console.print(f"  [green]{status}[/] {short_url}")


def select_format_and_quality():
    console.print("\n[bold]📦 Pilih format download:[/]")
    console.print(Panel(
        "[cyan]1.[/] 🎵 MP3 (Audio - MP3, kompresi agresif)\n"
        "[cyan]2.[/] 🎶 M4A (Audio - AAC, efisien)\n"
        "[cyan]3.[/] 🔊 OPUS (Audio - kualitas terbaik, ukuran terkecil)\n"
        "[cyan]4.[/] 🎬 MP4 (Video - codec modern AV1/VP9)",
        border_style="blue",
        padding=(1, 2),
    ))
    format_choice = Prompt.ask("Pilih format", choices=["1", "2", "3", "4"], default="1")
    fmt_map = {'1': 'mp3', '2': 'm4a', '3': 'opus', '4': 'mp4'}
    download_format = fmt_map[format_choice]

    if download_format == 'mp4':
        console.print("\n[bold]📺 Pilih kualitas MP4:[/]")
        q_keys = list(MP4_QUALITIES.keys())
        lines = [f"  [cyan]{i+1}.[/] {v['label']}" for i, v in enumerate(MP4_QUALITIES.values())]
        console.print(Panel("\n".join(lines), border_style="blue", padding=(1, 2)))
        q_choice = Prompt.ask("Pilih kualitas", choices=[str(i + 1) for i in range(len(q_keys))], default="2")
        quality = q_keys[int(q_choice) - 1]
    else:
        console.print("\n[bold]🎚️ Pilih kualitas audio:[/]")
        q_keys = list(AUDIO_QUALITIES.keys())
        lines = [f"  [cyan]{i+1}.[/] {v['label']}" for i, v in enumerate(AUDIO_QUALITIES.values())]
        console.print(Panel("\n".join(lines), border_style="blue", padding=(1, 2)))
        q_choice = Prompt.ask("Pilih kualitas", choices=[str(i + 1) for i in range(len(q_keys))], default="2")
        quality = q_keys[int(q_choice) - 1]

    return download_format, quality


def find_ffmpeg():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_names = ['ffmpeg', 'ffmpeg.exe']
    common_paths = [
        os.path.join(script_dir, 'ffmpeg', 'bin'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'ffmpeg', 'bin'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'ffmpeg', 'bin'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'WinGet', 'Packages', 'FFmpeg', 'ffmpeg', 'bin'),
    ]

    if shutil.which('ffmpeg'):
        return shutil.which('ffmpeg')

    for path in common_paths:
        for name in ffmpeg_names:
            full_path = os.path.join(path, name)
            if os.path.exists(full_path):
                return full_path
    return None


def find_aria2c():
    """Cek ketersediaan aria2c di sistem (dengan penanganan error)."""
    try:
        path = shutil.which('aria2c')
        if path:
            return path
    except Exception as e:
        console.print(f"[yellow]Gagal mendeteksi aria2c:[/] {e}")
    return None


def get_aria2c_opts():
    """Kembalikan opsi external downloader aria2c jika tersedia."""
    opts = {}
    try:
        if find_aria2c():
            opts['external_downloader'] = 'aria2c'
            opts['external_downloader_args'] = {
                'aria2c': ['-x', '16', '-s', '16', '-k', '1M', '--max-tries=5', '--retry-wait=3'],
            }
    except Exception as e:
        console.print(f"[yellow]Integrasi aria2c dilewati (error):[/] {e}")
    return opts


def check_ffmpeg():
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path is None:
        console.print(Panel(
            "[yellow]⚠️ FFmpeg tidak ditemukan di sistem.[/]\n\n"
            "Pilihan:\n"
            "  [cyan]1.[/] Download otomatis FFmpeg (direkomendasikan)\n"
            "  [cyan]2.[/] Lewati (tanpa FFmpeg, fitur terbatas)\n"
            "  [cyan]3.[/] Install manual: winget install ffmpeg",
            title="[yellow]Peringatan[/]",
            border_style="yellow",
        ))
        choice = Prompt.ask("Pilih", choices=["1", "2"], default="1")
        if choice == "1":
            return auto_install_ffmpeg()
        return None
    return ffmpeg_path


FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def auto_install_ffmpeg():
    install_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg")
    bin_dir = os.path.join(install_dir, "bin")

    if os.path.exists(os.path.join(bin_dir, "ffmpeg.exe")):
        console.print(f"[green]✅ FFmpeg sudah terinstall di:[/] [cyan]{bin_dir}[/]")
        return os.path.join(bin_dir, "ffmpeg.exe")

    console.print(Panel(
        "[bold cyan]⬇️ Mengunduh FFmpeg...[/]\n\n"
        f"URL: {FFMPEG_URL}\n"
        f"Tujuan: {bin_dir}",
        border_style="cyan",
    ))

    os.makedirs(bin_dir, exist_ok=True)

    try:
        req = urllib.request.Request(
            FFMPEG_URL,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
        )

        with urllib.request.urlopen(req) as resp:
            total = int(resp.headers.get('Content-Length', 0))

            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                tmp_path = tmp.name
                progress = Progress(
                    TextColumn("[bold cyan]Mengunduh FFmpeg...[/]"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn(),
                    console=console,
                )
                with progress:
                    task = progress.add_task("", total=total)
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        tmp.write(chunk)
                        progress.update(task, advance=len(chunk))

        console.print("[green]✅ Ekstraksi FFmpeg...[/]")
        with zipfile.ZipFile(tmp_path, 'r') as zf:
            ffmpeg_members = [m for m in zf.namelist() if m.endswith('ffmpeg.exe')]
            ffprobe_members = [m for m in zf.namelist() if m.endswith('ffprobe.exe')]

            for member in ffmpeg_members:
                zf.extract(member, install_dir)
                src = os.path.join(install_dir, member)
                dst = os.path.join(bin_dir, 'ffmpeg.exe')
                shutil.move(src, dst)

            for member in ffprobe_members:
                zf.extract(member, install_dir)
                src = os.path.join(install_dir, member)
                dst = os.path.join(bin_dir, 'ffprobe.exe')
                shutil.move(src, dst)

        for item in os.listdir(install_dir):
            item_path = os.path.join(install_dir, item)
            if item != 'bin' and os.path.isdir(item_path):
                shutil.rmtree(item_path)

        os.unlink(tmp_path)

        ffmpeg_exe = os.path.join(bin_dir, 'ffmpeg.exe')
        if os.path.exists(ffmpeg_exe):
            console.print(f"[bold green]✅ FFmpeg berhasil diinstall![/] [cyan]{ffmpeg_exe}[/]")
            return ffmpeg_exe
        else:
            console.print("[bold red]❌ Gagal mengekstrak FFmpeg.[/]")
            return None

    except Exception as e:
        console.print(f"[bold red]❌ Gagal mendownload FFmpeg:[/] {e}")
        console.print("[yellow]Silakan install manual: winget install ffmpeg[/]")
        return None


def main():
    show_welcome()

    ffmpeg_path = check_ffmpeg()
    if ffmpeg_path:
        console.print(f"\n[green]✅ FFmpeg:[/] [cyan]{ffmpeg_path}[/]")
    else:
        console.print("\n[yellow]⚠️ Berjalan tanpa FFmpeg (fitur MP3/MP4+Audio terbatas)[/]")

    if find_aria2c():
        console.print("[green]✅ aria2c terdeteksi:[/] [cyan]download paralel diaktifkan[/]")
    else:
        console.print("[dim]ℹ️ aria2c tidak terdeteksi (opsional): pip install aria2c / install aria2c[/]")

    download_format, quality = select_format_and_quality()

    while True:
        show_menu(download_format, quality)
        choice = Prompt.ask("[bold cyan]Pilih menu[/]", choices=["1", "2", "3", "4"])

        if choice == '1':
            single_download(ffmpeg_path, download_format, quality)
        elif choice == '2':
            batch_download(ffmpeg_path, download_format, quality)
        elif choice == '3':
            donasi()
        elif choice == '4':
            console.print("\n[bold green]👋 Keluar program. Terima kasih![/]")
            break


if __name__ == "__main__":
    main()
