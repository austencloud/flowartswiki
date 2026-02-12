"""Transcribe audio files to SRT using faster-whisper (CPU, int8 quantization)."""

import os
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def format_timestamp(seconds: float) -> str:
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def transcribe_file(audio_path: str, model: WhisperModel) -> str:
    segments, info = model.transcribe(audio_path)
    lines = []
    for i, segment in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}")
        lines.append(segment.text.strip())
        lines.append("")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file_or_directory> [model_size]")
        print("  model_size: large-v3 (default, best quality) or medium (2-3x faster)")
        sys.exit(1)

    target = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "large-v3"

    print(f"Loading {model_size} model (int8, CPU)...", file=sys.stderr)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    if os.path.isfile(target):
        # Single file mode - output to stdout
        print(f"Transcribing: {target}", file=sys.stderr)
        print(transcribe_file(target, model))
    elif os.path.isdir(target):
        # Directory mode - process all mp3s, write .srt alongside
        audio_files = sorted(Path(target).rglob("*.mp3"))
        print(f"Found {len(audio_files)} MP3 files", file=sys.stderr)
        for audio_path in audio_files:
            srt_path = audio_path.with_suffix(".srt")
            if srt_path.exists():
                print(f"Skipping (SRT exists): {audio_path}", file=sys.stderr)
                continue
            print(f"Transcribing: {audio_path}", file=sys.stderr)
            result = transcribe_file(str(audio_path), model)
            srt_path.write_text(result, encoding="utf-8")
            print(f"  -> {srt_path}", file=sys.stderr)
    else:
        print(f"Error: {target} is not a file or directory", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
