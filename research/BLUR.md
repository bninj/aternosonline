# BLUR: shallow depth-of-field background blur for the classroom takes

## v2 (19 Nov 2026): rebuilt matte + compositing. USE THIS for the plate.
The v1 pipeline below produced the "weird outline" the user saw whenever the speaker moved. Diagnosed with a 4-panel debug (original | alpha | fill mask | composite, 100% crops, `tools/blur/dbg/`) on the hook roll-in (IMG_3845 209–212 s). Confirmed causes, in order of visibility:
1. **Alpha lag ghost** (`stabilise_alpha` EMA): faint copies of previous silhouettes trail the body; with the composite this drew a light-grey contour round the hair and shoulders.
2. **Soft edge showed the sharp original background**: composite used source pixels in the 0<alpha<1 band, so unblurred desk/room texture ringed him.
3. **The moving swivel chair was background**: RVM/MediaPipe ignore it, so the plate fill and blur tore the yellow seat into blotches with a dark outline (the worst artefact in the roll-in).
4. **RVM on fast limbs**: holes and blotches at wrists/hands, hard steps where the eroded MediaPipe core was max()-ed in.
5. Depth "collar" (floor at his depth stays sharp): physically right and not what reads as the outline; left as is.

**New pipeline** (`tools/blur/matte2.py` then `tools/blur/bgblur2.py`; plate: `tools/render_plates_v2.py`):
- **SAM 2.1 Hiera-Tiny** video tracker (Apache-2.0), streamed forward and backward from a prompt frame (handles the roll-in from the frame edge). Person prompt is automatic (MediaPipe box + 3 points); extra objects come from a `"track"` list in `keep/<clip>.json` (IMG_3845 tracks his swivel chair, so it rides in sharp with him).
- **Motion-adaptive trimap**: the unknown band around the SAM mask widens per pixel with DIS optical-flow magnitude (10 px + |flow|, up to 60 px at 1080p), so motion-blurred limbs become partial alpha instead of a hard cut.
- **ViTMatte-S** (hustvl/vitmatte-small-composition-1k; weights Apache-2.0, code MIT) on the person crop at half scale, guided-filter upsampled.
- **Temporal**: flow-warped previous alpha, blended only in the band with weight 0.5·exp(−|flow|/2 px). Smooth when still, no lag when moving. No EMA, no MediaPipe core.
- **Composite** = α·F + (1−α)·blurred background, with F from `pymatting.estimate_foreground_ml` (MIT) in the band: the sharp background never shows through the edge.
- **Fill / no-spread mask** = alpha support dilated by H/160 + 0.75·speaker speed, so motion-blur tails never smear into the blur.
- **Motion easing**: background CoC × (1 − 0.25·smoothstep(6, 22 px/frame)), 4-frame look-ahead, ~0.6 s release (0.5 looked like visible pumping). Light wrap 0.15 on the outer edge. Fixed focus per clip (no focus breathing; `--focus-every 0.5` restores tracking).
- Speed on this box (4 shared cores): SAM ≈ 5 s/frame for one object, ≈ 10 s/frame with the chair as a second object; ViTMatte ≈ 1 s/frame; render ≈ 1.2 s/frame at 2304x1296. The 77 s plate takes about 4–6 h.

Evidence: `output/blur_v2/` (before/after MP4 of the roll-in, 100% crop sequences, flicker numbers). Results and remaining issues: see "v2 verdict" at the end of this file.

---

# v1 (superseded)

Tool: `tools/blur/bgblur.py`. QA: `tools/blur/qa.py`. Evidence: `tools/blur/qa/`, test renders in `tools/blur/out/`.
CPU only, ffmpeg in and out. The output is H.264 with BT.709 tags and the source audio over the same range.

## Verdict
Good enough for the pitch edit at the default **`--strength 1.0`** (maximum blur radius is 1.25% of frame height, about 13 px at 1080p). The look is a fast-lens shot: wide, but with real subject separation.
- Hair, hands and shoulders hold clean edges. There are no halos.
- The AI sign chair stays tack-sharp. The ddn and Sky logos stay legible.
- Blur grows smoothly with depth, with no stair-steps.
- Grain is matched to the source noise (about 1.3–1.6 code values).
- Flicker scan: the background and the edge ring around the speaker flicker no more than the original (table below). No frame drops: frames are decoded at a forced constant rate.

The DDN reference interviews use a stronger blur (about 2–3% of height). Their background sits much further behind the speaker. Here, going above about 1.5 makes edge errors more visible. Following the "gentle beats unstable" rule, keep it at 1.0–1.3.

## Pipeline
1. **Per-clip cache** in `tools/blur/cache/<clip>_<t0>_<t1>/`, about 3 MB per clip. It is built once, in about 1–3 minutes (faster when a 1080p proxy exists).
   - **Clean plate**: 40 frames sampled across the clip, run through the person matte, then a masked temporal median.
   - A **plate confidence map** marks unreliable areas. These are places the speaker never left, or props that moved between samples (the swivel chair). There the fill comes from the live surroundings instead (push-pull inpainting), so you get no ghosts.
   - **Static depth**: the median of Depth Anything V2 Small depth maps over the samples, each aligned to the plate's depth scale, with person pixels excluded.
   - **Default focus** is the speaker's own depth. The cache also stores a **sensor noise** estimate from frame differences.
2. **Per frame**:
   - **Matte**: RVM mobilenetv3 (recurrent, so temporally stable; good on hair) is combined with an eroded MediaPipe multiclass body core. The core is there because RVM alone let dark trousers on the dark floor go semi-transparent.
   - **Edge stabiliser**: a motion-gated temporal blend. Edges settle when still and follow fast hands at once.
   - **Fill**: the speaker region is filled with the exposure-matched clean plate. This is only done where the blur is big enough to smear his colours. Speaker pixels left in the fill are excluded from spreading. Together these fixed the shoulder glow and halo.
   - **Blur**: a layered, *normalised* **disc (bokeh) blur** in roughly linear light (gamma 2), with highlight boost and a soft shoulder (bloom). It uses 8–10 radius levels, with large radii done at reduced resolution. Each level only lets pixels that are themselves at least that blurred spread, so in-focus props never bleed into the background.
   - **Grain**: grain matched to the source is re-added in proportion to the blur.
   - **Composite**: the speaker is composited back with RVM foreground colours on the soft edge only.
   - **Focus tracking**: Depth Anything runs every 0.5 s and the focus pulls with about 0.8 s smoothing. A deadband stops it "breathing", and it holds when someone walks past close to the lens.
   - **Live depth correction**: where the scene moved relative to the plate (for example the chair swivelled), the depth map is corrected live.

## CLI
```
venv/bin/python tools/blur/bgblur.py --in footage/raw/IMG_3856.MOV --out out.mp4 \
   --start 20 --end 24 --keep-polygon tools/blur/keep/IMG_3856.json [--strength 1.0] \
   [--size 1920x1080 | 3840x2160] [--crop x,y,w,h]   # crop in 4K source px = punch-in
```
- **Ranges**: render only the ranges used in the edit, plus about 0.5 s of handles. `--preroll 1.0` warms the matte up before `--start`, and that time is not output.
- **Punch-ins**: `--crop 640,180,2740,1540 --size 1920x1080` processes the 4K crop natively. The matte runs at up to 1080 lines and is guided-filter upsampled.
- **Native 4K output** (`--size 3840x2160`) works. It is slow (about 185 s per output second) and peaks at about 5.3 GB RAM, so run one at a time.
- **Keep-polygon JSON**: coordinates are normalised to the full source frame. `strength` multiplies the blur inside the polygon: 0 = sharp, 0.4 = light, 1 = unchanged. Examples are in `tools/blur/keep/`:
  - sign chair and empty chair sharp: `IMG_3856.json`, `IMG_3857.json`
  - ddn monitor and laptop at 0.4: `IMG_3854.json`
- **Other knobs**:
  - `--dof`: in-focus band, default 0.04
  - `--falloff`: default 0.7
  - `--near`: foreground blur, default 0.25
  - `--bloom`: default 0.35
  - `--grain`: default 1
  - `--alpha-smooth`: default 0.5
  - `--focus`: fixed focus, from 0 (far) to 1 (near)
  - `--depth-update`: default 0.5
  - `--plate-range t0,t1`: build the plate from part of the clip only, for example if the lighting changes mid-clip (IMG_3849)
  - `--fps 30`: for the 120 fps clip IMG_3855
  - `--rebuild-cache`
- **Threads**: `BGBLUR_THREADS` defaults to 2. On this shared box, 2 was faster than 4 because of oversubscription.

## QA / evidence (`tools/blur/qa/`)
| test | clip / range | before-after | strip |
|---|---|---|---|
| seated, sign chair | IMG_3856 20–24 s | `t3856_before_after_1.0s.jpg`, `_3.0s.jpg` | `t3856_strip.jpg`, `t3856_hair_6consecutive.jpg` (6 consecutive frames, hair edge) |
| 4K punch-in to 1080 | IMG_3856 20–23 s, crop 2740x1540 | `t3856_punchin_before_after_1.0s.jpg` | `t3856_punchin_strip.jpg`; 4K output detail `t3856_4k_detail.jpg` |
| walk-in, sit down, prop chairs | IMG_3857 19–28 s | `t3857_before_after_1.0s/4.5s/7.5s.jpg` | `t3857_strip.jpg` |
| ddn monitor (light blur), swivel chair, gestures | IMG_3854 28–32 s | `t3854_before_after_0.4s/2.0s.jpg` | `t3854_strip.jpg` |

**Flicker scan** (`qa.py`): the mean absolute luma change between consecutive frames, measured after a low-pass filter at 480x270. It is reported for background pixels away from the speaker and for a 2–20 px ring around him. If the output is no higher than the input, no flicker or edge boiling was added.

| test | bg in → out (mean) | ring in → out (mean / p95) |
|---|---|---|
| 3856 seated | 0.26 → 0.30 | 0.36 → 0.40 / 0.59 → 0.70 |
| 3856 punch-in | 0.31 → 0.33 | 0.42 → 0.46 / 0.73 → 0.85 |
| 3857 walk/sit | 0.95 → 0.97 | 1.51 → 1.52 / 4.77 → 4.79 |
| 3854 monitor | 0.34 → 0.38 | 0.62 → 0.63 / 1.92 → 1.87 |

Every "spike" frame the scan flagged is also high in the input. Those are real motion: the speaker sitting down or the monitor content changing.

## Speed (4-core Xeon 2.1 GHz, shared with other jobs, load 7–15)
- **1080p**: about **22–25 s of compute per output second** (about 0.6–0.75 s per frame), with matting and rendering in parallel threads. One minute of selected A-roll takes about 25 minutes. Under heavy contention it rose to 35–45 s per output second.
- The cache adds about 1–3 minutes per clip, once.
- Native 4K output: about 185 s per output second.

## Models and licences
- **RVM** (Robust Video Matting, `rvm_mobilenetv3_fp32.onnx`): **GPL-3.0**. Used only as an internal tool. The model file stays in `tools/blur/models/rvm/` (LICENSE alongside) and is not shipped in any product.
- **Depth Anything V2 Small** (ONNX, onnx-community): **Apache-2.0**.
- **MediaPipe selfie_multiclass_256x256**: **Apache-2.0**.
- All the processing code is ours. Models take about 130 MB.

## Remaining weaknesses
- **Places the speaker never leaves** (seated takes) have no true clean plate. Behind him the fill is a smooth inpaint. It is fine under blur, but a big fast arm swing can briefly show a soft, smeared patch rather than real detail.
- **The speaker's own swivel chair** moves, so its depth is approximate. A small dark band or soft chair-back can appear beside him, as in 3854. It reads as a real out-of-focus object, not a matte error, and live depth correction limits it.
- **Fast hand motion** is blurred in the source, so hands get a soft matte. They show slightly blended rather than crisp edges. This is natural, but very fast gestures over high-contrast background can show a faint soft "trail".
- **Close walk-past** (3857 around 23 s): focus deliberately holds. Edges of a huge motion-blurred body are only as good as RVM.
- **Lighting changes inside a clip** (IMG_3849 lights off/on): use `--plate-range` for each lighting state.
- **Monitor screens** change content (Sky, ddn, terminal), so they are always taken from the live frame and are never plate-filled. Bright white screens bloom a little: lower `--bloom` if that bothers you.
- **Speed**: it is CPU-bound. Render only the ranges used.
