#!/bin/bash
# Search all transcripts for a term
# Usage: bash search.sh "quarter time"
#        bash search.sh "CAP" --context   (shows surrounding lines)

QUERY="$1"
BASE="F:/flow-arts-wiki/transcripts-pipeline/transcripts"

if [ -z "$QUERY" ]; then
  echo "Usage: bash search.sh \"search term\" [--context]"
  exit 1
fi

if [ "$2" = "--context" ]; then
  grep -rni "$QUERY" "$BASE/" --include="*.vtt" -B1 -A1 | grep -v "^--$"
else
  # Show filename and matching line
  grep -rni "$QUERY" "$BASE/" --include="*.vtt" | sed 's|.*/transcripts/||'
fi
