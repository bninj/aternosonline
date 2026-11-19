"""Frame-difference scan for a rendered video.
Usage: python3 scripts/flicker_scan.py video.mp4 [known_cut_frames comma list]
Reports (1) single-frame outliers: a frame that differs from both neighbours while the neighbours agree
(blank plate, missing frost, dropped layer), and (2) the largest frame-to-frame jumps (pops / hard cuts).
"""
import subprocess, sys
import numpy as np

path = sys.argv[1]
known = {int(x) for x in sys.argv[2].split(',')} if len(sys.argv) > 2 and sys.argv[2] else set()
W, H = 480, 270
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
frames = []
while True:
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        break
    frames.append(np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.int16))
n = len(frames)
d = lambda a, b: float(np.abs(frames[a] - frames[b]).mean())
# local (per 16x16 block) max difference catches a small plate blinking even if the frame mean barely moves
def blockmax(a, b):
    x = np.abs(frames[a] - frames[b]).mean(axis=2)
    x = x[: H // 15 * 15, : W // 16 * 16].reshape(H // 15, 15, W // 16, 16).mean(axis=(1, 3))
    return float(x.max())
out = []
for i in range(1, n - 1):
    a, b, c = blockmax(i - 1, i), blockmax(i, i + 1), blockmax(i - 1, i + 1)
    if a > 6 and b > 6 and c < 0.35 * min(a, b):
        out.append((i, a, b, c))
jumps = sorted(((blockmax(i - 1, i), i) for i in range(1, n)), reverse=True)[:12]
print(f'frames: {n}')
print(f'single-frame outliers: {len(out)}')
for o in out[:20]:
    print('  outlier frame %d  prev %.1f next %.1f prev-next %.1f' % o)
print('largest block jumps (value, frame):', ', '.join(f'{v:.1f}@{i}{"(known cut)" if i in known else ""}' for v, i in jumps))
