#!/usr/bin/env bash
# (a) Assemble a numbered PNG sequence (captureSequence output) into a constant-frame-rate mp4.
#   make-video.sh <frames-dir> <out.mp4> [fps=30] [prefix=orbit-] [crf=16]
# Frames and video contain game imagery: keep both OUTSIDE the git repo.
# Playback speed is set by the frame rate you choose, NOT by the game's real speed.
set -euo pipefail
dir=${1:?frames dir}; out=${2:?output mp4}; fps=${3:-30}; prefix=${4:-orbit-}; crf=${5:-16}
case "$(cd "$(dirname "$out")" && pwd)/" in "$(cd "$(dirname "$0")/.." && pwd)/"*) echo "refusing to write inside the repo" >&2; exit 2;; esac
n=$(ls "$dir"/"$prefix"[0-9]*.png 2>/dev/null | wc -l); [ "$n" -gt 0 ] || { echo "no frames $dir/${prefix}NNNNN.png" >&2; exit 1; }
# even dimensions are required for yuv420p
ffmpeg -hide_banner -loglevel error -y -framerate "$fps" -i "$dir/${prefix}%05d.png" \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -c:v libx264 -preset slow -crf "$crf" -pix_fmt yuv420p -movflags +faststart "$out"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames,duration -of default=nw=1 "$out"
echo "frames in: $n"
