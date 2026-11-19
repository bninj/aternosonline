"""Sample players for the v2 bed. Every sound comes from a recorded,
licence-verified sample (see MUSIC.md); only gain/pitch/EQ/reverb processing
is applied here."""
import os, re, glob, math
from fractions import Fraction
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
CAND = "/home/user/ddn-project/music/candidates"
VCSL = os.path.join(CAND, "VCSL")
ND = os.path.join(CAND, "NakedDrums", "Wilkinson Audio", "Naked Drums")
RBX = os.path.join(CAND, "freepats_yamaha_rbx_bass", "PickedBassYR", "PickedBassYR SFZ+WAV-20190930")
RBXF = os.path.join(CAND, "freepats_yamaha_rbx_bass", "FingerBassYR", "FingerBassYR SFZ+WAV-20190930")
REN = os.path.join(CAND, "renoise_acoustic_kit_two_handed", "extracted", "SampleData")

PCS = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8,
       "A": 9, "A#": 10, "B": 11}

_cache = {}
USED = set()          # every sample file actually used in a render (for the credits)


def load(path, trim=True):
    """Load a sample, convert to stereo float, resample to 48 kHz and trim
    leading silence (keeps 1 ms) so onsets sit on the grid."""
    if path in _cache:
        USED.add(path)
        return _cache[path]
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    x = x[:, :2]
    if sr != SR:
        fr = Fraction(SR, sr).limit_denominator(1000)
        x = signal.resample_poly(x, fr.numerator, fr.denominator, axis=0)
    if trim:
        m = np.abs(x).max(1)
        if m.max() > 0:
            i0 = int(np.argmax(m > 0.03 * m.max()))
            i0 = max(0, i0 - int(0.001 * SR))
            x = x[i0:]
    x = x.copy()
    n = min(24, len(x))
    x[:n] *= np.linspace(0, 1, n)[:, None]
    _cache[path] = x
    USED.add(path)
    return x


def shift(x, semis):
    if abs(semis) < 1e-6:
        return x
    ratio = 2 ** (semis / 12.0)
    fr = Fraction(1 / ratio).limit_denominator(500)
    return signal.resample_poly(x, fr.numerator, fr.denominator, axis=0)


def envelope(x, dur_s, release_s):
    n_on = int(dur_s * SR)
    n_rel = int(release_s * SR)
    y = x[: n_on + n_rel].copy()
    if len(y) > n_on:
        t = np.arange(len(y) - n_on) / SR
        y[n_on:] *= (np.exp(-5.0 * t / max(release_s, 1e-3)) * np.clip(1 - t / max(release_s, 1e-3), 0, 1))[:, None]
    return y


def note_from_name(s):
    m = re.search(r"(?<![A-Za-z])([A-G]#?)(-?\d)(?!\d)", s)
    if not m:
        return None
    return 12 * (int(m.group(2)) + 1) + PCS[m.group(1)]


class Multi:
    """Pitched multisample instrument. `offset` corrects the library's octave
    naming to the measured sounding pitch (measured with an FFT: VCSL mallets
    and hand chimes sound an octave above the file name; TX81Z Clavisynth's
    perceived fundamental is two octaves above; TX81Z FM Piano as named)."""

    def __init__(self, files, offset, vel_key, max_shift=4, release=0.25, gain=1.0):
        self.s = []                         # (note, layer, path)
        for f in files:
            n = note_from_name(os.path.basename(f))
            if n is None:
                continue
            self.s.append((n + offset, vel_key(os.path.basename(f)), f))
        self.layers = sorted({l for _, l, _ in self.s})
        self.max_shift = max_shift
        self.release = release
        self.gain = gain

    def render(self, pitch, vel, dur_s, release=None):
        # velocity -> layer
        li = min(len(self.layers) - 1, int(vel / 128 * len(self.layers)))
        layer = self.layers[li]
        cands = [c for c in self.s if c[1] == layer] or self.s
        n, l, f = min(cands, key=lambda c: (abs(c[0] - pitch), c[0] < pitch))
        x = shift(load(f), pitch - n)
        rel = self.release if release is None else release
        y = envelope(x, dur_s, rel)
        return y * self.gain * (0.35 + 0.65 * (vel / 127.0) ** 1.6)


class Kit:
    """Round-robin, velocity-layered one-shots."""

    def __init__(self, layers, gain=1.0):
        # layers: list (low->high) of lists of file paths (round robins)
        self.layers = [l for l in layers if l]
        self.rr = {}
        self.gain = gain

    def render(self, vel, choke_s=None, layer=None):
        li = layer if layer is not None else min(len(self.layers) - 1, int(vel / 128 * len(self.layers)))
        rrs = self.layers[li]
        k = self.rr.get(li, 0)
        self.rr[li] = k + 1
        x = load(rrs[k % len(rrs)])
        if choke_s:
            x = envelope(x, choke_s, 0.06)
        return x * self.gain * (0.3 + 0.7 * (vel / 127.0) ** 1.4)


# ----------------------------------------------------------------------------
# Instrument builders
# ----------------------------------------------------------------------------

def vcsl(*parts):
    return os.path.join(VCSL, *parts)


def marimba():
    files = glob.glob(vcsl("Idiophones", "Struck Idiophones", "Marimba", "*.wav"))
    lay = lambda b: {"soft": 0, "med": 1, "loud": 2}[re.search(r"_(soft|med|loud)_", b).group(1)]
    return Multi(files, +12, lay, release=0.35)


def vibes(kind="Soft Mallets"):
    files = glob.glob(vcsl("Idiophones", "Struck Idiophones", "Vibraphone", kind, "*.wav"))
    def lay(b):
        m = re.search(r"_v(\d)_", b)
        return int(m.group(1)) if m else 1
    return Multi(files, +12, lay, release=1.2)


def tx81z(patch):
    files = glob.glob(vcsl("Electrophones", "TX81Z", patch, "*.wav"))
    lay = lambda b: int(re.search(r"_vl(\d)", b).group(1))
    off = {"Clavisynth": +24, "FM Piano": 0, "Piano 1": 0}[patch]
    return Multi(files, off, lay, release=0.08)   # VCSL: "sounds best with super short release"


def hand_chimes():
    files = glob.glob(vcsl("Idiophones", "Struck Idiophones", "Hand Chimes", "*.wav"))
    return Multi(files, +12, lambda b: 0, release=2.0)


class RBXBass:
    """FreePats 'Picked Bass YR' (Yamaha RBX), chromatic E1-D#2, E2 sample stretched up."""

    def __init__(self, root=RBX, gain=1.0):
        sfz = glob.glob(os.path.join(root, "*.sfz"))[0]
        txt = open(sfz, encoding="latin-1").read()
        self.reg = []
        for blk in txt.split("<region>")[1:]:
            d = dict(re.findall(r"(\w+)=(\S+)", blk))
            lo = int(d.get("lokey", d.get("key")))
            hi = int(d.get("hikey", d.get("key")))
            c = int(d.get("pitch_keycenter", d.get("key")))
            self.reg.append((lo, hi, c, os.path.join(root, d["sample"])))
        self.gain = gain

    def render(self, pitch, vel, dur_s, release=0.09):
        r = [g for g in self.reg if g[0] <= pitch <= g[1]]
        lo, hi, c, f = r[0] if r else min(self.reg, key=lambda g: abs(g[2] - pitch))
        x = shift(load(f), pitch - c)
        y = envelope(x, dur_s, release)
        return y * self.gain * (0.25 + 0.75 * (vel / 127.0) ** 1.5)


def _nd_map():
    import subprocess, sys
    here = os.path.dirname(os.path.abspath(__file__))
    out = subprocess.run([sys.executable, "-I", os.path.join(here, "nd_resolve.py"), os.path.join(ND, "Data"),
                          "kick_in", "kick_sub", "kick_oh", "snare_top1", "snare_bot", "snare_oh",
                          "tom2_di", "tom4_di", "tom5_di", "tom2_oh", "tom4_oh", "tom5_oh", "hats_di", "hats_oh"],
                         capture_output=True, text=True, check=True).stdout
    m = {}
    for line in out.splitlines():
        g, lab, s = line.split(" ", 2)
        m.setdefault((g, lab), []).append(s)
    return m


class NDPiece:
    """One Naked Drums articulation, several mics summed (close + some OH)."""

    def __init__(self, ndmap, mics, label, gain=1.0):
        # mics: list of (group, mic gain)
        self.parts = []
        for g, mg in mics:
            names = ndmap[(g, label)]                # first block wins per (vel, rr)
            by = {}
            for s in names:
                if not os.path.exists(os.path.join(ND, "Samples", s)):
                    continue
                vl = int(re.search(r"_(\d0)_(one|two|three|four)-", s).group(1))
                rr = re.search(r"_(one|two|three|four)-", s).group(1)
                by.setdefault(vl, {}).setdefault(rr, os.path.join(ND, "Samples", s))
            self.parts.append((by, mg))
        self.vls = sorted(self.parts[0][0])
        self.k = 0
        self.gain = gain

    def render(self, vel, choke_s=None):
        li = min(len(self.vls) - 1, int(vel / 128 * len(self.vls)))
        vl = self.vls[li]
        rrs = ["one", "two", "three", "four"]
        rr = rrs[self.k % 4]
        self.k += 1
        out = None
        for by, mg in self.parts:
            d = by.get(vl) or by[sorted(by)[-1]]
            f = d.get(rr) or list(d.values())[0]
            x = load(f, trim=False) * mg
            if out is None:
                out = x
            else:
                n = max(len(out), len(x))
                o = np.zeros((n, 2)); o[: len(out)] += out; o[: len(x)] += x
                out = o
        # trim common leading silence
        m = np.abs(out).max(1)
        i0 = max(0, int(np.argmax(m > 0.03 * m.max())) - int(0.001 * SR))
        out = out[i0:]
        if choke_s:
            out = envelope(out, choke_s, 0.05)
        return out * self.gain * (0.3 + 0.7 * (vel / 127.0) ** 1.3)


def drums():
    m = _nd_map()
    kit = {
        # Yamaha Recording Custom 22" kick: inside + sub + a little overhead
        "kick": NDPiece(m, [("kick_in", 1.0), ("kick_sub", 0.3), ("kick_oh", 0.35)], "$center"),
        # Naked Drums snare (Ayotte/Pearl), top + bottom + OH
        "snare": NDPiece(m, [("snare_top1", 1.0), ("snare_bot", 0.35), ("snare_oh", 0.4)], "$center"),
        "side": NDPiece(m, [("snare_top1", 1.0), ("snare_oh", 0.4)], "$sidestick"),
        # Yamaha Recording Custom toms 12" / 14" / 16"
        "tom_hi": NDPiece(m, [("tom2_di", 1.0), ("tom2_oh", 0.4)], "$center"),
        "tom_mid": NDPiece(m, [("tom4_di", 1.0), ("tom4_oh", 0.4)], "$center"),
        "tom_lo": NDPiece(m, [("tom5_di", 1.0), ("tom5_oh", 0.4)], "$center"),
        "hat": NDPiece(m, [("hats_di", 1.0), ("hats_oh", 0.3)], "$closed"),
        "hat_open": NDPiece(m, [("hats_di", 1.0), ("hats_oh", 0.3)], "$open"),
        "hat_pedal": NDPiece(m, [("hats_di", 1.0), ("hats_oh", 0.3)], "$pedal"),
    }
    sh = vcsl("Idiophones", "Struck Idiophones", "Shaker, Small")
    kit["shaker_dn"] = Kit([sorted(glob.glob(os.path.join(sh, "Mid_ShakerLowFaster_Down_rr*.wav")))])
    kit["shaker_up"] = Kit([sorted(glob.glob(os.path.join(sh, "Mid_ShakerLowFaster_Up_rr*.wav")))])
    return kit


def cymbal(name):
    for d in ["Suspended Cymbal 1", "Suspended Cymbal 2"]:
        p = vcsl("Idiophones", "Struck Idiophones", d, name)
        if os.path.exists(p):
            return load(p, trim=not ("cresc" in name or "bow" in name))
    raise FileNotFoundError(name)
