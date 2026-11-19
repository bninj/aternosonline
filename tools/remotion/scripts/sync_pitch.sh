#!/usr/bin/env bash
# Snapshot the edit's timing files into the Remotion source (run after SHOTPLAN / captions change).
set -e
cd "$(dirname "$0")/.."
cp ../../edit/SHOTPLAN.json src/pitch/shotplan.json 2>/dev/null || true
cp ../../edit/captions_v2.json src/pitch/captions_v2.json 2>/dev/null || true
cp ../../edit/SHOTPLAN_v4.json src/pitch/shotplan_v4.json
cp ../../edit/captions_v3.json src/pitch/captions_v3.json
echo synced
