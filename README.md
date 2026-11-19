# Why DDN pitch: edit files

Working files for a 90 second entry to the DDN Partner SPIFF "Why DDN" pitch contest. The example customer is Sky. The video was filmed on an iPhone 12 (4K, 30 fps) in a classroom across five camera spots. The raw clips are kept in Google Drive, not in this repo.

## Where things stand
Paused on 19 Nov 2026.
- **Done:** take picks, cut list, rough cut, captions, colour grade and shot plan.
- **Not done:**
  - background blur (the edge around the speaker during movement isn't good enough yet)
  - the final graphics composition
  - the music
  - the mix and final render

Read `edit/DIRECTION.md` first. It holds every decision made so far and the open issues.

## Layout
| Path | What it is |
|---|---|
| `edit/DIRECTION.md` | Decisions, open issues, and where each job stopped |
| `edit/script.txt`, `edit/script_spoken.txt` | The written script, and the wording actually spoken on camera |
| `edit/picks.json` | Chosen take for each line |
| `edit/edl_v2.json`, `edit/timeline_v2.json` | Frame-accurate cut list (source clip, in and out points) and the resulting timeline: 77.0 s plus a 3 s end card |
| `edit/captions_v2.json`, `edit/captions_v2.srt` | Caption phrases with word timings |
| `edit/SHOTPLAN.json` | Zoom per shot, and when each graphic and sound effect comes in, tied to the spoken words |
| `edit/grade/grade.json` | Exposure and white balance correction per shot |
| `edit/tx/` | Transcripts of every clip, with word timestamps |
| `deliverables/` | TAKES.md, DEVIATIONS.md (script vs spoken) and FACTS.md (every on-screen claim with its source) |
| `research/` | DDN style guide, font match, blur notes, and notes on the tools and repos looked at |
| `brand/` | DDN logos, third-party logos with their sources, Inter Tight and Manrope (OFL) |
| `tools/` | Pipeline scripts: transcription, take matching, cut refinement, conform, cut QA, grading, background blur, plate rendering. `tools/setup.sh` rebuilds the environment. |
| `tools/remotion/` | Graphics and caption components (Remotion) |
| `music/` | Music scripts, MIDI and MUSIC.md (sample licences) |

## Rebuilding
```bash
bash tools/setup.sh
```
Then download the clips from Drive into `footage/raw/` and run `tools/ingest.sh` on each one.
