"""
audio_analysis.py
------------------
Lightweight audio analysis for the music video maker. Decodes audio to
raw PCM via ffmpeg (no extra dependency needed) and uses numpy to find
"onset" points — moments where the energy jumps — which make natural
places to cut between scenes. This isn't full beat-detection (that would
need librosa), but it's a real improvement over cutting at fixed,
arbitrary intervals: cuts land on actual moments of change in the song.
"""

import subprocess
import numpy as np
from pathlib import Path

SAMPLE_RATE = 22050


def _decode_to_mono_pcm(audio_path: Path) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", str(audio_path),
        "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Could not decode audio: {result.stderr.decode()[-500:]}")
    audio = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return audio


def get_duration(audio_path: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def find_cut_points(audio_path: Path, num_scenes: int, min_gap: float = 1.5) -> list[float]:
    """
    Returns `num_scenes - 1` timestamps (seconds) that are good places to
    cut between scenes, spread across the song and biased toward moments
    where the energy noticeably increases (new section, drum hit, etc).
    Falls back to even spacing if the audio is too short/quiet to find
    good onsets.
    """
    duration = get_duration(audio_path)
    if num_scenes <= 1:
        return []

    try:
        audio = _decode_to_mono_pcm(audio_path)
    except RuntimeError:
        # Fall back to even spacing if decoding fails for any reason
        step = duration / num_scenes
        return [round(step * i, 2) for i in range(1, num_scenes)]

    # Energy envelope: RMS over short windows
    window = int(SAMPLE_RATE * 0.1)  # 100ms windows
    n_windows = len(audio) // window
    if n_windows < num_scenes * 2:
        step = duration / num_scenes
        return [round(step * i, 2) for i in range(1, num_scenes)]

    energy = np.array([
        np.sqrt(np.mean(audio[i * window:(i + 1) * window] ** 2))
        for i in range(n_windows)
    ])
    # Onset strength = how much energy increased vs the previous window
    onset_strength = np.diff(energy, prepend=energy[0])
    onset_strength[onset_strength < 0] = 0

    window_seconds = window / SAMPLE_RATE
    min_gap_windows = max(1, int(min_gap / window_seconds))

    # Divide the song into num_scenes roughly-equal target regions, and
    # within each boundary search a NON-OVERLAPPING nearby range for the
    # strongest onset (capped so adjacent search windows can't collide,
    # which previously let multiple boundaries collapse onto one onset).
    target_step = n_windows / num_scenes
    search_radius = min(min_gap_windows * 2, max(1, int(target_step / 2) - 1))

    cut_indices = []
    for i in range(1, num_scenes):
        target = int(target_step * i)
        search_lo = max(0, target - search_radius)
        search_hi = min(n_windows, target + search_radius)
        if search_hi <= search_lo:
            cut_indices.append(target)
            continue
        local_slice = onset_strength[search_lo:search_hi]
        best = search_lo + int(np.argmax(local_slice))
        cut_indices.append(best)

    # Guarantee strictly increasing, minimum-gap-respecting cut points
    # even if two searches still landed close together.
    cut_indices.sort()
    for i in range(1, len(cut_indices)):
        min_allowed = cut_indices[i - 1] + min_gap_windows
        if cut_indices[i] < min_allowed:
            cut_indices[i] = min_allowed

    cut_times = [round(idx * window_seconds, 2) for idx in cut_indices if idx < n_windows]
    return cut_times
