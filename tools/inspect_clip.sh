#!/usr/bin/env bash
# Verify a generated clip. A video job that reports success proves nothing: past the
# model's limit it writes a valid file of the right length containing damage.
#
#   usage: tools/inspect_clip.sh <clip.mp4> [samples] [cols]
#
# Prints mean luma at each sample and writes a tiled montage next to the clip.
#
# Reading the output:
#   luma flat at 16.0            -> video black, the clip is empty
#   luma drops to mid 80s, flat  -> "mud": frame 0 survived, everything generated is gone
#   luma normal but soft frames  -> "melting": numerically fine, structurally wrong.
#                                   There is no number for this. You have to look.
#
# The LAST sample is the one that matters. In image-to-video the first frame is baked in
# from the start frame, so it is guaranteed to look right and tells you nothing.

set -uo pipefail

SRC="${1:?usage: inspect_clip.sh <clip.mp4> [samples] [cols]}"
N="${2:-6}"
COLS="${3:-3}"

command -v ffprobe >/dev/null || { echo "ffprobe not found"; exit 127; }
command -v ffmpeg  >/dev/null || { echo "ffmpeg not found";  exit 127; }
[ -f "$SRC" ] || { echo "no such file: $SRC"; exit 1; }
[ "$N" -ge 2 ] || { echo "need at least 2 samples"; exit 1; }

DIR="$(cd "$(dirname "$SRC")" && pwd)"
BASE="$(basename "$SRC")"; BASE="${BASE%.*}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

TOTAL="$(ffprobe -v error -select_streams v:0 -count_frames \
          -show_entries stream=nb_read_frames -of csv=p=0 "$SRC")"
DIMS="$(ffprobe -v error -select_streams v:0 \
          -show_entries stream=width,height -of csv=p=0:s=x "$SRC")"
[ -n "$TOTAL" ] && [ "$TOTAL" -ge 1 ] || { echo "could not count frames"; exit 1; }

LAST=$((TOTAL - 1))
EXPR=""
IDX_LIST=()
i=0
while [ "$i" -lt "$N" ]; do
  f=$(( i * LAST / (N - 1) ))
  IDX_LIST+=("$f")
  if [ -z "$EXPR" ]; then EXPR="eq(n\,$f)"; else EXPR="$EXPR+eq(n\,$f)"; fi
  i=$((i + 1))
done

echo "$BASE  $DIMS  frames=$TOTAL  sampling: ${IDX_LIST[*]}"
ffmpeg -v error -y -i "$SRC" -vf "select='$EXPR'" -vsync 0 "$TMP/f%03d.png"

echo "--- mean luma (0-255) ---"
n=0
for p in "$TMP"/f*.png; do
  L="$(ffprobe -v error -f lavfi -i "movie=$p,signalstats" \
        -show_entries frame_tags=lavfi.signalstats.YAVG -of csv=p=0 2>/dev/null | head -1)"
  idx="${IDX_LIST[$n]}"
  tag=""
  [ "$n" -eq 0 ] && tag="  (first, baked in, ignore it)"
  [ "$idx" = "$LAST" ] && tag="  (LAST, the one that matters)"
  printf '  frame %-7s %8s%s\n' "$idx" "${L:-n/a}" "$tag"
  n=$((n + 1))
done

ROWS=$(( (N + COLS - 1) / COLS ))
ffmpeg -v error -y -pattern_type glob -i "$TMP/f*.png" \
  -vf "scale=384:-1,tile=${COLS}x${ROWS}:margin=6:padding=4:color=0x101014" \
  -frames:v 1 "$DIR/${BASE}_montage.png"
echo "montage: $DIR/${BASE}_montage.png"
