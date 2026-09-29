#!/usr/bin/env python3
"""
ytdl.py — apothecary-lab edition. A Python rewrite of ytdl.sh with the
same UI conventions as lyricbench.py: amber-and-oak palette, shelf rows,
tincture loading bars, and a two-tier render path (rich → plain ANSI).

WHAT IT DOES (parity with ytdl.sh):
  1. Verifies yt-dlp is on PATH.
  2. Prompts for a video URL (validated).
  3. Fetches and displays the format table.
  4. Prompts for a video format code.
  5. Auto-selects the best audio-only format.
  6. Downloads the chosen video + best audio, muxed to MP4.
  7. Reports success or failure.

WHAT'S DIFFERENT FROM THE SHELL VERSION:
  - yt-dlp is invoked with -J (--dump-single-json) once to enumerate
    formats, so we parse formats from structured JSON instead of
    scraping `yt-dlp -F` with awk. Same information, no brittle column
    parsing, no second network round-trip to re-fetch the format list.
  - The format table is rendered through the same kv()/panel() helpers
    as lyricbench, so it visually belongs next to it on the same bench.
  - Two-tier rendering: if `rich` is installed you get a rich.Table for
    the format list; otherwise the plain ANSI helper path. Either way,
    the palette matches lyricbench.py exactly (same hex constants).
  - Everything is one process. yt-dlp itself is still a subprocess
    because it's the tool doing the actual downloading — same as
    lyricbench still shells out to your --whisper script.

REQUIRES:
    yt-dlp   (https://github.com/yt-dlp/yt-dlp)
    rich     (optional — pip install rich --break-system-packages)

USAGE:
    ./ytdl.py                      # interactive, same flow as ytdl.sh
    ./ytdl.py "URL"                # skip the URL prompt
    ./ytdl.py --audio-only "URL"   # best audio, no video prompt
    ./ytdl.py --out ~/Videos       # target directory (default: cwd)
    ./ytdl.py --list-only "URL"    # just show formats and exit
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

START_TIME = time.time()

# --------------------------------------------------------------------------
# Palette — identical hex values to lyricbench.py so the two tools read as
# a matched set on the same shelf. Amber tinctures on dark oak.
# --------------------------------------------------------------------------

def _rgb(r, g, b): return f"\033[38;2;{r};{g};{b}m"

RESET     = "\033[0m"
BOLD      = "\033[1m"
DIM       = "\033[2m"
PLUM      = _rgb(150, 111, 214)  # refine
FLAME     = _rgb(230, 126, 34)   # active accent
HERB      = _rgb(150, 189, 120)  # pale info
TINCTURE  = _rgb(212, 160, 74)   # headers / gold
PARCHMENT = _rgb(150, 132, 104)  # dim text
INK       = _rgb(74, 60, 46)     # border chrome
SAGE      = _rgb(122, 168, 116)  # ok / success
EMBER     = _rgb(196, 78, 61)    # error / fail
SLATE     = _rgb(107, 142, 158)  # instrumental / cool accent
COPPER    = _rgb(196, 138, 64)   # warn
VERDIGRIS = _rgb(90, 156, 143)   # repair / restore

RM_PLUM, RM_FLAME, RM_HERB, RM_TINCTURE = "#966fd6", "#e67e22", "#96bd78", "#d4a04a"
RM_PARCHMENT, RM_INK, RM_SAGE, RM_EMBER = "#968468", "#4a3c2e", "#7aa874", "#c44e3d"
RM_SLATE, RM_COPPER, RM_VERDIGRIS      = "#6b8e9e", "#c48a40", "#5a9c8f"


def _p(s: str = "") -> None:
    print(s)


def shelf_row():
    _p(f"{PARCHMENT}  ⚗ ·  ⚗ ·  ⚗ ·  ⚗ ·  ⚗ ·  ⚗ ·  ⚗ ·  ⚗{RESET}")


def divider():
    _p(f"{INK}  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{RESET}")


def section_header(title: str):
    _p("")
    _p(f"{INK}  ⚗{RESET}  {TINCTURE}{BOLD}{title}{RESET}")
    divider()


def kv(label: str, value, colour: str = PARCHMENT, width: int = 11) -> None:
    _p(f"  {colour}{label:<{width}}{RESET} {value}")


def panel(title: str, rows: list, accent: str = TINCTURE) -> None:
    _p("")
    _p(f"  {INK}⚗{RESET} {accent}{BOLD}{title}{RESET}")
    divider()
    for label, value, colour in rows:
        kv(label, value, colour)
    divider()


# --------------------------------------------------------------------------
# Message emitters — same glyph/tag conventions as lyricbench.
# --------------------------------------------------------------------------

def ok(tag: str, msg: str):   _p(f"  {SAGE}●{RESET}  {SAGE}{BOLD}{tag:<10}{RESET}  {msg}")
def info(tag: str, msg: str): _p(f"  {PARCHMENT}○{RESET}  {PARCHMENT}{BOLD}{tag:<10}{RESET}  {msg}")
def warn(tag: str, msg: str): _p(f"  {COPPER}◐{RESET}  {COPPER}{BOLD}{tag:<10}{RESET}  {msg}")
def err(tag: str, msg: str):  _p(f"  {EMBER}✕{RESET}  {EMBER}{BOLD}{tag:<10}{RESET}  {msg}")
def inst(tag: str, msg: str): _p(f"  {SLATE}◆{RESET}  {SLATE}{BOLD}{tag:<10}{RESET}  {msg}")


def loading_bar(label: str, duration: float = 1.0, steps: int = 20):
    """A tincture filling the vial — same animation as lyricbench."""
    delay = duration / steps
    sys.stdout.write(f"  {PLUM}⚗{RESET}  {PARCHMENT}{label:<34}{RESET} {INK}[{RESET}")
    sys.stdout.flush()
    for i in range(steps):
        if i < 7:
            colour = PARCHMENT
        elif i < 14:
            colour = SLATE
        else:
            colour = SAGE
        sys.stdout.write(f"{colour}●{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(f"{INK}]{RESET}  {SAGE}{BOLD}STEEPED{RESET}\n")


def elapsed_str() -> str:
    secs = int(time.time() - START_TIME)
    return f"{secs // 60:02d}:{secs % 60:02d}"


# --------------------------------------------------------------------------
# rich — soft dependency, same two-tier degrade as lyricbench.
#
# NOTE on the `global` line below: `global` does not support renaming.
# You declare the names you want bound at module scope, and the `import`
# statement does the aliasing. So we declare `rich_box` (the name the
# rest of the file actually uses) and then `from rich import box as
# rich_box` binds it. Declaring `box` here would be wrong — nothing else
# in the file refers to it by that name.
# --------------------------------------------------------------------------

RICH_AVAILABLE = False


def _try_import_rich() -> bool:
    global RICH_AVAILABLE, Table, Console, Text, rich_box
    try:
        from rich.table import Table
        from rich.console import Console
        from rich.text import Text
        from rich import box as rich_box
        RICH_AVAILABLE = True
    except ImportError:
        RICH_AVAILABLE = False
    return RICH_AVAILABLE


_try_import_rich()


# --------------------------------------------------------------------------
# yt-dlp interaction
# --------------------------------------------------------------------------

def have_ytdlp() -> Optional[str]:
    return shutil.which("yt-dlp")


def fetch_formats(url: str) -> Optional[dict]:
    """Run `yt-dlp -J` once and return the parsed JSON. -J (--dump-single-json)
    gives us every format with structured fields (format_id, ext, vcodec,
    acodec, resolution, abr, filesize, format_note), so we don't have to
    scrape the -F table with awk and guess at column boundaries."""
    ytdlp = have_ytdlp()
    if not ytdlp:
        return None
    try:
        proc = subprocess.run(
            [ytdlp, "-J", "--no-warnings", url],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def pick_best_audio(formats: list[dict]) -> Optional[dict]:
    """ytdl.sh's `awk '/audio only/ {print $1}' | tail -1` — same intent,
    done properly: yt-dlp lists formats best-first within each category,
    so 'last' in the shell version was actually picking the *worst*
    audio-only stream. We pick the best by abr when available, falling
    back to yt-dlp's own ordering."""
    audio_only = [f for f in formats
                  if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
    if not audio_only:
        return None
    with_abr = [f for f in audio_only if isinstance(f.get("abr"), (int, float))]
    if with_abr:
        return max(with_abr, key=lambda f: f["abr"])
    return audio_only[-1]


def format_row(f: dict) -> tuple:
    """Compact (id, ext, res, codecs, size/note) summary for display."""
    fid  = str(f.get("format_id", "?"))
    ext  = f.get("ext", "?")
    vcodec = f.get("vcodec") or "none"
    acodec = f.get("acodec") or "none"
    if f.get("resolution"):
        res = f["resolution"]
    elif f.get("height"):
        res = f"{f['height']}p"
    else:
        res = "audio" if vcodec == "none" else "?"
    v = "—" if vcodec == "none" else vcodec.split(".")[0]
    a = "—" if acodec == "none" else acodec.split(".")[0]
    size = f.get("filesize") or f.get("filesize_approx")
    if size:
        size_s = f"{size / 1_048_576:.1f} MiB"
    else:
        size_s = f.get("format_note", "") or "—"
    return fid, ext, res, f"{v}/{a}", size_s


# --------------------------------------------------------------------------
# Format table rendering — rich.Table if available, plain ANSI otherwise.
# --------------------------------------------------------------------------

def _render_formats_plain(formats: list[dict], audio_id: str = "") -> None:
    _p(f"  {INK}{'ID':<8}{'EXT':<6}{'RES':<10}{'CODECS':<20}{'SIZE / NOTE':<14}{RESET}")
    _p(f"  {INK}{'─' * 8}{'─' * 6}{'─' * 10}{'─' * 20}{'─' * 14}{RESET}")
    for f in formats:
        fid, ext, res, codecs, size_s = format_row(f)
        is_audio = (f.get("vcodec") == "none")
        is_video = (f.get("vcodec") not in (None, "none") and f.get("acodec") in (None, "none"))
        marker = "◆" if is_audio else ("▲" if is_video else "·")
        colour = SLATE if is_audio else (PLUM if is_video else PARCHMENT)
        chosen = f"  {SAGE}← best audio{RESET}" if str(f.get("format_id")) == audio_id else ""
        _p(f"  {colour}{marker}{RESET} {fid:<6}{ext:<6}{res:<10}{codecs:<20}{size_s:<14}{chosen}")


def _render_formats_rich(formats: list[dict], audio_id: str = "") -> None:
    table = Table(
        show_header=True, header_style=f"bold {RM_FLAME}",
        border_style=RM_INK, box=rich_box.ROUNDED, pad_edge=False,
    )
    table.add_column("", width=2)
    table.add_column("ID", style=RM_COPPER, no_wrap=True)
    table.add_column("EXT", style=RM_PARCHMENT, no_wrap=True)
    table.add_column("RES", style=RM_SAGE, no_wrap=True)
    table.add_column("CODECS", style=RM_PARCHMENT, no_wrap=True)
    table.add_column("SIZE / NOTE", style=RM_TINCTURE, no_wrap=True)
    table.add_column("", style=RM_SAGE)
    for f in formats:
        fid, ext, res, codecs, size_s = format_row(f)
        is_audio = (f.get("vcodec") == "none")
        is_video = (f.get("vcodec") not in (None, "none") and f.get("acodec") in (None, "none"))
        marker = "◆" if is_audio else ("▲" if is_video else "·")
        marker_style = RM_SLATE if is_audio else (RM_PLUM if is_video else RM_PARCHMENT)
        chosen = "← best audio" if str(f.get("format_id")) == audio_id else ""
        table.add_row(
            f"[{marker_style}]{marker}[/]",
            fid, ext, res, codecs, size_s,
            f"[{RM_SAGE}]{chosen}[/]",
        )
    Console().print(table)


def render_formats(formats: list[dict], audio_id: str = "") -> None:
    if RICH_AVAILABLE:
        _render_formats_rich(formats, audio_id)
    else:
        _render_formats_plain(formats, audio_id)


# --------------------------------------------------------------------------
# Interactive input helpers — same amber-prompt feel as lyricbench's
# "Install optional packages now?" prompt.
# --------------------------------------------------------------------------

def prompt(label: str, default: str = "") -> str:
    suffix = f" {DIM}[{default}]{RESET}" if default else ""
    try:
        return input(f"  {TINCTURE}⚗{RESET}  {PARCHMENT}{label}{RESET}{suffix} ").strip()
    except EOFError:
        return ""


# --------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------

def download(url: str, video_id: Optional[str], audio_id: str, out_dir: Path) -> bool:
    """Mirrors yt-dlp -f 'VIDEO+AUDIO' --merge-output-format mp4, but with
    --newline so progress prints line-by-line (rather than yt-dlp's in-place
    \\r rewriting, which fights our own output). We stream each line straight
    through so the user sees real progress, tinted to match the bench."""
    ytdlp = have_ytdlp()
    if not ytdlp:
        return False

    if video_id:
        fmt = f"{video_id}+{audio_id}"
        cmd = [
            ytdlp,
            "-f", fmt,
            "--merge-output-format", "mp4",
            "--newline",
            "-o", str(out_dir / "%(title)s.%(ext)s"),
            url,
        ]
    else:
        # --audio-only: no video stream to mux, keep native audio container
        cmd = [
            ytdlp,
            "-f", audio_id,
            "--newline",
            "-o", str(out_dir / "%(title)s.%(ext)s"),
            url,
        ]

    info("[DL]", " ".join(cmd))
    _p("")
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
    except FileNotFoundError:
        return False

    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("[download]") and "%" in line:
            _p(f"  {SLATE}>>{RESET} {PARCHMENT}{line}{RESET}")
        elif low.startswith("[merge]") or low.startswith("[fixup"):
            _p(f"  {PLUM}◐{RESET}  {PLUM}{line}{RESET}")
        elif low.startswith("error") or "error" in low:
            _p(f"  {EMBER}✕{RESET}  {EMBER}{line}{RESET}")
        else:
            _p(f"  {PARCHMENT}·{RESET}  {DIM}{line}{RESET}")
    proc.wait()
    return proc.returncode == 0


# --------------------------------------------------------------------------
# Boot banner — same shape as lyricbench's, different wordmark.
# --------------------------------------------------------------------------

def boot_sequence(args) -> None:
    os.system("clear")
    _p("")
    shelf_row(); shelf_row()

    _p(f"{PLUM}{BOLD}")
    _p("  · · · · · · · · · · · · · · · · · · · ·")
    _p("  ██╗   ██╗████████╗██████╗ ██╗     ")
    _p("  ╚██╗ ██╔╝╚══██╔══╝██╔══██╗██║     ")
    _p("   ╚████╔╝    ██║   ██║  ██║██║     ")
    _p("    ╚██╔╝     ██║   ██║  ██║██║     ")
    _p("     ██║      ██║   ██████╔╝███████╗")
    _p("     ╚═╝      ╚═╝   ╚═════╝ ╚══════╝")
    _p("  · · · · · · · · · · · · · · · · · · · ·")
    _p(f"{RESET}")
    _p(f"{FLAME}{BOLD}      Y T - D L P  //  A P O T H E C A R Y{RESET}")
    _p(f"{PARCHMENT}      one URL · best audio auto-selected · muxed to mp4{RESET}\n")

    shelf_row(); divider()
    _p(f"{INK}  ⚗ ⚗  the cabinet is open  ⚗ ⚗{RESET}")
    divider(); shelf_row(); _p("")

    for msg in ("warming the burners...", "checking the reagent shelf...",
                "unstopping the download flask...", "the bench is hot. let's brew."):
        sys.stdout.write(f"  {COPPER}◐{RESET} {PARCHMENT}{msg}{RESET}")
        sys.stdout.flush()
        time.sleep(0.18)
        sys.stdout.write(f"\r  {PLUM}⚗{RESET} {SAGE}{msg}{RESET}\n")
        sys.stdout.flush()
        time.sleep(0.06)
    time.sleep(0.15); _p("")

    import socket
    panel("BENCH LOG", [
        ("chemist", os.environ.get("USER", "user") + "@" + socket.gethostname(), SAGE),
        ("session", time.strftime("%Y-%m-%d %H:%M:%S"), PARCHMENT),
        ("output",  str(args.out_dir)[:38], TINCTURE),
        ("mode",    "audio-only" if args.audio_only else ("list-only" if args.list_only else "video+audio"), SLATE),
    ], accent=PLUM)
    _p("")

    section_header("STOCKING THE REAGENT CHAIN")
    kv("stocking", "yt-dlp + format inspection + muxer...", PARCHMENT)
    _p("")
    loading_bar("[1] YT-DLP BINARY CHECK         ", 0.5)
    loading_bar("[2] FORMAT TABLE ENUMERATION   ", 0.6)
    if not args.list_only and not args.audio_only:
        loading_bar("[3] BEST AUDIO AUTO-PICK       ", 0.5)
        loading_bar("[4] MP4 MUXER                  ", 0.4)
    elif args.audio_only:
        loading_bar("[3] BEST AUDIO AUTO-PICK       ", 0.5)
    _p("")

    # dependency check — mirror lyricbench's check_deps, but shorter (only
    # yt-dlp is required; rich is optional and already attempted above).
    section_header("DEPENDENCY CHECK  ·  SCANNING THE CABINET")
    kv("scanning", "required tools...", PARCHMENT)
    _p("")

    ytdlp = have_ytdlp()
    if ytdlp:
        ok("[ OK ]", f"yt-dlp  // {ytdlp}")
    else:
        err("[MISS]", "yt-dlp  // not found on PATH")
    if RICH_AVAILABLE:
        ok("[ OK ]", "rich   // live-rendered format table")
    else:
        warn("[MISS]", "rich   // optional — format table will use plain ANSI")
        _p(f"  {COPPER}◐{RESET}  {PARCHMENT}Optional: pip install --break-system-packages rich{RESET}")
    _p("")

    if not ytdlp:
        kv("✕ abort", "yt-dlp is required · https://github.com/yt-dlp/yt-dlp", EMBER)
        _p("")
    else:
        kv("● online", "all systems ready · reagents armed", SAGE)
        _p("")

    shelf_row(); divider(); shelf_row(); _p("")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ytdl.py",
        description="yt-dlp wrapper — apothecary-lab edition, same bench as lyricbench.py.",
    )
    p.add_argument("url", nargs="?", default="", help="video URL (prompted if omitted)")
    p.add_argument("--out", dest="out_arg", type=str, default="",
                   help="output directory (default: current working directory)")
    p.add_argument("--audio-only", action="store_true",
                   help="skip video selection entirely — download best audio only")
    p.add_argument("--list-only", action="store_true",
                   help="show the format table and exit without downloading")
    p.add_argument("--format", type=str, default="",
                   help="skip the format prompt and use this video format ID directly")
    return p


def main() -> int:
    args = build_parser().parse_args()

    if args.out_arg:
        out_dir = Path(args.out_arg).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path.cwd()
    args.out_dir = out_dir

    boot_sequence(args)

    if not have_ytdlp():
        return 1

    # -- URL acquisition ---------------------------------------------------
    url = args.url.strip()
    if not url:
        section_header("FLASK LOADING  ·  TARGET URL")
        url = prompt("Enter the URL of the video:")
        _p("")
        if not url:
            err("[ERR!]", "URL cannot be empty · exiting")
            _p("")
            return 1

    # -- fetch formats -----------------------------------------------------
    section_header("REAGENT INSPECTION  ·  ENUMERATING FORMATS")
    kv("url", url[:70], PARCHMENT)
    _p("")
    info("[FETCH]", "asking yt-dlp for the full format table...")

    formats: Optional[dict] = None
    holder: dict = {}

    def _do_fetch():
        holder["json"] = fetch_formats(url)

    t = threading.Thread(target=_do_fetch, daemon=True)
    t.start()

    # Steep a vial while we wait — matches lyricbench's loading_bar style.
    # If the fetch finishes early, we cut the bar short and pad the rest.
    steps = 24
    sys.stdout.write(f"  {PLUM}⚗{RESET}  {PARCHMENT}{'querying yt-dlp':<34}{RESET} {INK}[{RESET}")
    sys.stdout.flush()
    completed = 0
    for i in range(steps):
        if not t.is_alive():
            break
        colour = PARCHMENT if i < 8 else (SLATE if i < 16 else SAGE)
        sys.stdout.write(f"{colour}●{RESET}")
        sys.stdout.flush()
        completed = i + 1
        time.sleep(0.08)
    # pad the remainder so the closing bracket lands cleanly
    for _ in range(steps - completed):
        sys.stdout.write(f"{INK}●{RESET}")
    sys.stdout.write(f"{INK}]{RESET}  {SAGE}{BOLD}DONE{RESET}\n")
    t.join(timeout=65)
    formats = holder.get("json")

    if not formats:
        _p("")
        err("[ERR!]", "failed to fetch formats · check the URL and try again")
        _p("")
        return 1

    title = formats.get("title") or "(untitled)"
    uploader = formats.get("uploader") or formats.get("channel") or "?"
    duration = formats.get("duration")
    dur_s = ""
    if isinstance(duration, (int, float)):
        m, s = divmod(int(duration), 60)
        dur_s = f"{m}:{s:02d}"
    raw_formats = formats.get("formats") or []
    if not raw_formats:
        err("[ERR!]", "no formats returned by yt-dlp")
        _p("")
        return 1

    _p("")
    panel("TARGET REAGENT", [
        ("title",    title[:60], SAGE),
        ("uploader", uploader[:60], PARCHMENT),
        ("duration", dur_s or "?", SLATE),
        ("formats",  f"{len(raw_formats)} available", TINCTURE),
    ], accent=PLUM)

    # -- best audio pick ---------------------------------------------------
    best_audio = pick_best_audio(raw_formats)
    if not best_audio:
        _p("")
        err("[ERR!]", "no audio-only format found · yt-dlp may need updating")
        _p("")
        return 1
    audio_id = str(best_audio.get("format_id"))
    abr = best_audio.get("abr")
    abr_s = f"{abr:.0f} kbps" if isinstance(abr, (int, float)) else "?"

    # -- render the format table ------------------------------------------
    _p("")
    section_header("REAGENT SHELF  ·  AVAILABLE FORMATS")
    kv("legend", f"{SLATE}◆ audio-only{RESET}   {PLUM}▲ video-only{RESET}   {PARCHMENT}· muxed{RESET}", PARCHMENT)
    kv("audio pick", f"{audio_id}  ({abr_s})  — auto-selected as best audio", SLATE)
    _p("")
    render_formats(raw_formats, audio_id)
    _p("")

    if args.list_only:
        panel("LIST ONLY  ·  NO DOWNLOAD", [
            ("next", "re-run without --list-only to fetch", PARCHMENT),
        ], accent=TINCTURE)
        _p("")
        return 0

    # -- choose video format ----------------------------------------------
    video_id: Optional[str] = None
    if args.audio_only:
        video_id = None
    elif args.format:
        video_id = args.format.strip()
    else:
        section_header("FLASK SELECTION  ·  CHOOSE A VIDEO FORMAT")
        _p(f"  {PARCHMENT}tip: pick a video-only row (▲) and the best audio will be muxed in.{RESET}")
        _p(f"  {PARCHMENT}     pick a muxed row (·) and only that stream is used.{RESET}")
        _p("")
        video_id = prompt("Enter the format code for the video you want:")
        _p("")
        if not video_id:
            err("[ERR!]", "video format cannot be empty · exiting")
            _p("")
            return 1

    # -- download ----------------------------------------------------------
    section_header("STEEPING  ·  DOWNLOADING")
    if video_id:
        kv("video", f"{video_id}", PLUM)
        kv("audio", f"{audio_id}  ({abr_s})", SLATE)
    else:
        kv("audio", f"{audio_id}  ({abr_s})  — audio-only run", SLATE)
    kv("output", str(out_dir), TINCTURE)
    _p("")

    ok_dl = download(url, video_id, audio_id, out_dir)
    _p("")

    if ok_dl:
        panel("STEEPING COMPLETE", [
            ("result",  "download finished successfully", SAGE),
            ("saved",   str(out_dir), TINCTURE),
            ("elapsed", elapsed_str(), PARCHMENT),
        ], accent=SAGE)
    else:
        panel("STEEPING FAILED", [
            ("result",  "yt-dlp returned a non-zero exit code", EMBER),
            ("hint",    "check the URL, your network, and that yt-dlp is up to date", PARCHMENT),
            ("elapsed", elapsed_str(), PARCHMENT),
        ], accent=EMBER)

    _p("")
    shelf_row(); divider()
    _p(f"  {DIM}FLASK CORKED  ·  {time.strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    divider(); shelf_row(); _p("")

    return 0 if ok_dl else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _p("")
        _p(f"  {EMBER}✕{RESET}  {EMBER}{BOLD}INTERRUPTED{RESET}  {PARCHMENT}user abort{RESET}")
        _p("")
        sys.exit(130)