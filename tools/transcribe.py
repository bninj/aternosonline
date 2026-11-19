#!/usr/bin/env python3
"""Transcribe speech with word timestamps -> JSON, one speech island at a time (default) or the whole file.

Island mode (default): silero VAD (bundled with faster-whisper, ONNX) with min_silence 300 ms finds speech islands;
each island (+0.1 s padding) is transcribed on its own with the model loaded once. A whole-file pass merges restarts
into one clean sentence, drops short false starts and stretches words over pauses; islands don't. Fillers are kept
(filler-heavy initial_prompt). An island that still holds a stretched word (> --max-word s) is split again at 0.1-0.3 s
level dips (10 ms RMS) and re-transcribed (idea: kurbaitaev/ghost-editor take-selection.md, MIT).

usage: transcribe.py IN.(wav|mov|mp4) OUT.json [MODEL] [--mode islands|whole] [--min-silence-ms 300] [--pad 0.1]
output: {"segments": [{start,end,text,words:[{w,s,e,p}]}], "islands": [{i,s,e,text,words,resplit,suspect}], ...}
(segments == islands in island mode, so tx_to_captions.py etc. keep working)
"""
import argparse, json, subprocess, sys, time
import numpy as np

SR = 16000
import os
PROMPT = os.environ.get("TX_PROMPT", "Umm, let me think like, hmm... Okay, here's what I'm, like, thinking. Uh, so, DDN, GPU, AI.")


def load_audio(src, sr=SR):
    # decode with ffmpeg ourselves: faster-whisper 1.2.1's PyAV path breaks with av>=17 ("metadata_errors")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-map", "0:a:0", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def load_model(name="large-v3-turbo"):
    from faster_whisper import WhisperModel
    return WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=4)


def tx(model, audio, offset=0.0, prompt=PROMPT):
    """transcribe one array; returns (words, text, suspect). times are absolute (offset added)."""
    segs, _ = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=False, beam_size=5,
                               condition_on_previous_text=False, initial_prompt=prompt)
    words, texts, suspect = [], [], False
    for s in segs:
        texts.append(s.text.strip())
        suspect |= (s.no_speech_prob > 0.6 and s.avg_logprob < -0.8)
        for w in s.words or []:
            words.append({"w": w.word.strip(), "s": round(w.start + offset, 3), "e": round(w.end + offset, 3), "p": round(w.probability, 3)})
    return words, " ".join(texts).strip(), suspect


def levels_db(x, sr=SR, hop=0.01):
    n = int(sr * hop); f = x[:len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((f.astype(np.float64) ** 2).mean(1)) + 1e-9)


def islands_vad(audio, min_silence_ms=300, threshold=0.5):
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    ts = get_speech_timestamps(audio, VadOptions(threshold=threshold, min_silence_duration_ms=min_silence_ms,
                                                 min_speech_duration_ms=100, speech_pad_ms=0))
    return [(t["start"] / SR, t["end"] / SR) for t in ts]


def dips(x, floor_db, lo=0.1, hi=0.3):
    """centres of 0.1-0.3 s runs below floor+12 dB inside an island (10 ms RMS)"""
    L = levels_db(x); q = floor_db + 12; out = []; k = 0
    while k < len(L):
        if L[k] < q:
            j = k
            while j + 1 < len(L) and L[j + 1] < q: j += 1
            d = (j - k + 1) * 0.01
            if lo <= d <= hi and k > 5 and j < len(L) - 5: out.append((k + j + 1) / 2 * 0.01)
            k = j + 1
        else:
            k += 1
    return out


def run_islands(model, audio, min_silence_ms=300, pad=0.1, max_word=1.0):
    dur = len(audio) / SR
    floor = float(np.percentile(levels_db(audio), 8))
    isl = []
    for k, (s, e) in enumerate(islands_vad(audio, min_silence_ms)):
        a, b = max(0.0, s - pad), min(dur, e + pad)
        words, text, sus = tx(model, audio[int(a * SR):int(b * SR)], a)
        rec = {"i": k, "s": round(s, 3), "e": round(e, 3), "text": text, "words": words, "resplit": False, "suspect": sus}
        if any(w["e"] - w["s"] > max_word for w in words):
            cuts = dips(audio[int(s * SR):int(e * SR)], floor)
            if cuts:
                bounds = [s] + [s + c for c in cuts] + [e]; ws, ts = [], []
                for p0, p1 in zip(bounds[:-1], bounds[1:]):
                    a2, b2 = max(0.0, p0 - 0.05), min(dur, p1 + 0.05)
                    w2, t2, _ = tx(model, audio[int(a2 * SR):int(b2 * SR)], a2); ws += w2; ts.append(t2)
                rec.update(words=ws, text=" | ".join(ts), resplit=True)
        isl.append(rec)
    return isl


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("model", nargs="?", default="large-v3-turbo")
    ap.add_argument("--mode", choices=["islands", "whole"], default="islands")
    ap.add_argument("--min-silence-ms", type=int, default=300); ap.add_argument("--pad", type=float, default=0.1)
    ap.add_argument("--max-word", type=float, default=1.0, help="re-split an island holding a word longer than this (s)")
    a = ap.parse_args()
    t0 = time.time(); m = load_model(a.model); t1 = time.time()
    audio = load_audio(a.src); dur = len(audio) / SR
    if a.mode == "whole":
        words, text, _ = tx(m, audio)
        isl = [{"i": 0, "s": 0.0, "e": round(dur, 3), "text": text, "words": words, "resplit": False, "suspect": False}]
    else:
        isl = run_islands(m, audio, a.min_silence_ms, a.pad, a.max_word)
    t2 = time.time()
    segs = [{"start": x["words"][0]["s"] if x["words"] else x["s"], "end": x["words"][-1]["e"] if x["words"] else x["e"],
             "text": x["text"], "words": x["words"]} for x in isl if x["words"]]
    json.dump({"model": a.model, "mode": a.mode, "duration": dur, "load_s": t1 - t0, "transcribe_s": t2 - t1,
               "min_silence_ms": a.min_silence_ms, "segments": segs, "islands": isl}, open(a.out, "w"), indent=1)
    for x in isl:
        print(f"  [{x['s']:7.2f}-{x['e']:7.2f}]{' R' if x['resplit'] else ''}{' ?' if x['suspect'] else ''} {x['text']}")
    print(f"{a.model} {a.mode}: {len(isl)} islands, load {t1 - t0:.1f}s, transcribe {t2 - t1:.1f}s for {dur:.1f}s audio (RTF {(t2 - t1) / dur:.2f})")


if __name__ == "__main__":
    main()
