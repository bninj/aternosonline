#!/usr/bin/env bash
# Snapshot the edit's timing files into the Remotion source (run after SHOTPLAN / captions change).
set -e
cd "$(dirname "$0")/.."
cp ../../edit/SHOTPLAN.json src/pitch/shotplan.json
cp ../../edit/captions_v2.json src/pitch/captions_v2.json
echo synced
