"""
ffmpeg_tools.py
---------------
Low-level video assembly, built directly on the ffmpeg binary via
subprocess (no moviepy dependency — one less heavy install, and it's
easy to see exactly what command is being run if something breaks).

Every function here does ONE mechanical step. trailer_builder.py chains
them together.
"""

import subprocess
from pathlib import Path

FPS = 25
RESOLUTION = "1280x720"
CROSSFADE_DURATION = 0.5  # seconds, overlap between consecutive scenes


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{' '.join(cmd)}\n\n{result.stderr[-2000:]}")


def image_to_clip(image_path: Path, out_path: Path, duration: float, caption: str = "") -> None:
    """
    Turns one still image into a short video clip with a slow zoom
    ("ken burns" effect) and an optional caption burned in at the bottom.
    """
    frames = int(duration * FPS)
    zoompan = f"zoompan=z='min(zoom+0.0015,1.2)':d={frames}:s={RESOLUTION}:fps={FPS}"
    vf = f"scale={RESOLUTION},{zoompan}"

    if caption:
        # Escape characters ffmpeg's drawtext filter treats specially
        safe_caption = caption.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        vf += (
            f",drawtext=text='{safe_caption}':fontcolor=white:fontsize=48"
            ":x=(w-text_w)/2:y=h-120:box=1:boxcolor=black@0.4:boxborderw=20"
        )

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(image_path),
        "-t", str(duration),
        "-vf", vf,
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    _run(cmd)


def concat_with_crossfade(clip_paths: list[Path], out_path: Path) -> float:
    """
    Chains multiple clips together with a crossfade transition between
    each pair. Returns the resulting total duration in seconds.
    """
    if len(clip_paths) == 1:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip_paths[0]),
               "-c", "copy", str(out_path)]
        _run(cmd)
        return _probe_duration(out_path)

    inputs = []
    for p in clip_paths:
        inputs += ["-i", str(p)]

    # Need each clip's duration to compute cumulative xfade offsets
    durations = [_probe_duration(p) for p in clip_paths]

    filter_parts = []
    running_total = durations[0]
    prev_label = "0:v"
    for i in range(1, len(clip_paths)):
        offset = running_total - CROSSFADE_DURATION
        out_label = f"v{i}" if i < len(clip_paths) - 1 else "v"
        filter_parts.append(
            f"[{prev_label}][{i}:v]xfade=transition=fade:"
            f"duration={CROSSFADE_DURATION}:offset={offset}[{out_label}]"
        )
        running_total = running_total + durations[i] - CROSSFADE_DURATION
        prev_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    _run(cmd)
    return running_total


def add_music(video_path: Path, music_path: Path, out_path: Path, fade_out: float = 1.0) -> None:
    """
    Mixes a music track under the video, trimmed to the video's length
    with a fade-out at the end. If music_path is None, just copies the
    video through untouched.
    """
    video_duration = _probe_duration(video_path)
    fade_start = max(0.0, video_duration - fade_out)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-i", str(music_path),
        "-filter_complex",
        f"[1:a]atrim=0:{video_duration},afade=t=out:st={fade_start}:d={fade_out}[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-shortest",
        str(out_path),
    ]
    _run(cmd)


def concat_hard(clip_paths: list[Path], out_path: Path) -> None:
    """
    Concatenates clips with a hard cut (no crossfade) — used by the
    music video maker, where scene durations are already derived from
    the song's actual timing and a crossfade would blur that sync.
    """
    inputs = []
    filter_inputs = ""
    for i, p in enumerate(clip_paths):
        inputs += ["-i", str(p)]
        filter_inputs += f"[{i}:v]"
    filter_complex = f"{filter_inputs}concat=n={len(clip_paths)}:v=1:a=0[v]"

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    _run(cmd)


def mux_full_track(video_path: Path, audio_path: Path, out_path: Path) -> None:
    """
    Replaces/adds the full audio track under a video with no trimming or
    fading — used for music videos, where the audio IS the content and
    its length already matches the video by construction.
    """
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac",
        "-shortest",
        str(out_path),
    ]
    _run(cmd)


def _probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())
