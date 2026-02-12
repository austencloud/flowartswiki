#!/bin/bash
# Download auto-subs for all channels. Re-run after rate limit expires (~1 hour).
# Uses --download-archive to skip already-downloaded videos.

YT_DLP="/c/Python313/Scripts/yt-dlp.exe"
BASE="F:/flow-arts-wiki/transcripts-pipeline"
ARCHIVE="$BASE/subs-done.txt"

CHANNELS=(
  "https://www.youtube.com/@DrexFactor"
  "https://www.youtube.com/channel/UCxNTT-bLX8l61ozRcrs41VQ"   # Noel Yee
  "https://www.youtube.com/channel/UC9ttFS8kzStkmXjwrQ2Y12g"   # SpinMorePoi
  "https://www.youtube.com/channel/UC1JgoAfZwzwO7himGUiYPlQ"   # PlayPoi
  "https://www.youtube.com/channel/UC0pD2gHJQX-YDAZZNrSy67g"   # LORQ NICHOLS
  "https://www.youtube.com/channel/UCsU3nT26Emz8INF8ULL5GCQ"   # Alien Jon
)

for url in "${CHANNELS[@]}"; do
  echo ""
  echo "=== Downloading: $url ==="
  "$YT_DLP" \
    --write-auto-subs \
    --sub-langs "en" \
    --skip-download \
    --no-overwrites \
    --download-archive "$ARCHIVE" \
    -o "$BASE/transcripts/%(channel)s/%(title)s.%(ext)s" \
    -t sleep \
    "$url"
done

echo ""
echo "=== Done. File counts: ==="
for dir in "$BASE/transcripts"/*/; do
  count=$(ls -1 "$dir" 2>/dev/null | wc -l)
  [ "$count" -gt 0 ] && echo "  $(basename "$dir"): $count"
done
