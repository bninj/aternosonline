"""Shared audio helpers for refine_cuts.py, conform.py and cut_qa.py (10 ms level envelopes, frame PTS, loaders)."""
import json, subprocess
import numpy as np

HOP = 0.01


def load(path, sr=48000, stream="0:a:0"):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", stream, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(pcm, np.float32).astype(np.float64)


def levels(x, sr, hop=HOP):
    n = int(sr * hop); f = x[:len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((f ** 2).mean(1)) + 1e-9)


def highpass(x, sr, fc=2500.0):
    from scipy.signal import butter, sosfiltfilt
    return sosfiltfilt(butter(4, fc, "highpass", fs=sr, output="sos"), x)


class Env:
    """broadband + >2.5 kHz 10 ms envelopes with floor-relative thresholds.
    Q = noise floor (8th pct) + 12 dB clamped to -56..-40 (griffinwooldridge/talking-head-editor cut.py, MIT);
    the high band catches f/s/sh/th that are quiet broadband but loud above 2.5 kHz (jacobksamuelson, MIT)."""

    def __init__(self, x, sr):
        self.sr = sr
        self.L = levels(x, sr); self.Lh = levels(highpass(x, sr), sr)
        self.floor = float(np.percentile(self.L, 8)); self.floor_h = float(np.percentile(self.Lh, 8))
        self.Q = float(min(max(self.floor + 12, -56), -40)); self.Qh = float(min(max(self.floor_h + 12, -65), -40))
        self.T = len(self.L) * HOP

    def _i(self, t): return min(max(int(t / HOP), 0), len(self.L) - 1)
    def lv(self, t): return self.L[self._i(t)]
    def lvh(self, t): return self.Lh[self._i(t)]
    def quiet(self, t): return self.lv(t) < self.Q and self.lvh(t) < self.Qh
    def loud(self, t, d=4): return self.lv(t) > self.Q + d or self.lvh(t) > self.Qh + d
    def speechy(self, t): return self.lv(t) > self.Q + 10   # clearly voiced (for edge-voice checks)


def frame_times(path):
    """real presentation times of every video frame (iPhone 29.97-30 fps drifts vs frame/30)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.split()
    t = sorted(float(x) for x in out if x not in ("", "N/A"))
    return np.array(t)


def video_rate(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return r or None


def has_video(path):
    return bool(video_rate(path))
