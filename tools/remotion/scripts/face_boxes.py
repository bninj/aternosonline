"""Per-segment face boxes for PitchFinal (px @1920x1080, before zoom).
Usage: tools/venv/bin/python scripts/face_boxes.py <video> <SHOTPLAN.json> <out.json>
Samples 6 fps with mediapipe FaceLandmarker (tools/models/face_landmarker.task); per segment: median centre and a
box covering the 5th..95th percentile extents of the face over the segment (hair margin added)."""
import json, subprocess, sys, os
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

video, plan, out = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
model = os.path.abspath(os.path.join(HERE, '..', '..', 'models', 'face_landmarker.task'))
W, H, FPS = 1920, 1080, 5
lm = FaceLandmarker.create_from_options(FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model), running_mode=RunningMode.IMAGE, num_faces=1))
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', video, '-vf', f'fps={FPS},scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
rows = []
i = 0
while True:
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.frombuffer(b, np.uint8).reshape(H, W, 3))
    r = lm.detect(img)
    t = i / FPS; i += 1
    if r.face_landmarks:
        xs = [q.x * 1920 for q in r.face_landmarks[0]]; ys = [q.y * 1080 for q in r.face_landmarks[0]]
        rows.append((t, min(xs), min(ys), max(xs), max(ys)))
segs = json.load(open(plan))['segments']
res = []
for s in segs:
    w = [r for r in rows if s['start'] <= r[0] < s['end']]
    if s['i'] == 0: w = [r for r in w if r[0] > 3.0] or w  # chair alone first
    a = np.array([r[1:] for r in w])
    if not len(a): res.append({'i': s['i'], 'face': None}); continue
    x0, y0 = np.percentile(a[:, 0], 5), np.percentile(a[:, 1], 5)
    x1, y1 = np.percentile(a[:, 2], 95), np.percentile(a[:, 3], 95)
    h = y1 - y0
    box = {'x': round(x0 - 0.15 * h), 'y': round(y0 - 0.35 * h), 'w': round(x1 - x0 + 0.3 * h), 'h': round(h * 1.5)}
    cx, cy = float(np.median((a[:, 0] + a[:, 2]) / 2)), float(np.median((a[:, 1] + a[:, 3]) / 2))
    res.append({'i': s['i'], 'n': len(w), 'center': [round(cx), round(cy)], 'box': box})
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res))
