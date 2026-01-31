#!/usr/bin/env bash
set -euo pipefail

# Batch-generate samples for a list of VCTK speaker IDs using the coqui sidecar
# Usage: ./scripts/generate_vctk_samples.sh [p225 p226 ...]
# Default list contains a mix of speakers to audition.

PORT=${COQUI_PORT:-5002}
VOICE="coqui-tts:en_vctk"

DEFAULT_SPEAKERS=(p225 p226 p227 p228 p229 p230 p231 p232 p233 p236 p241 p247 p252 p259 p266 p273 p280 p287 p294 p301 p308 p316 p323 p330 p336 p343 p351 p360)

SPEAKERS=(${@:-${DEFAULT_SPEAKERS[@]}})

mkdir -p samples

for s in "${SPEAKERS[@]}"; do
  out="samples/out_${s}.wav"
  echo "Generating $out..."
  http_code=$(curl -s -w "%{http_code}" -o "$out" -X POST "http://localhost:${PORT}/api/tts" \
    -H "Content-Type: application/json" \
    -d "{\"voice\":\"${VOICE}\",\"speaker\":\"${s}\",\"text\":\"Testing speaker ${s} for audition.\"}")
  echo "  $s: HTTP $http_code"
  if [[ "$http_code" != "200" ]]; then
    echo "  failed to generate $s (HTTP $http_code), removing $out"
    rm -f "$out"
  fi
done

echo "Samples written to samples/*.wav — play with ffplay or your preferred player."
