#!/usr/bin/env bash
# Run the workflow on the AKS deployment from this machine:
#   ./test.sh [video-url] [language ...]
set -euo pipefail

TEMPORAL_ADDRESS=${TEMPORAL_ADDRESS:-tvt-temporal.eastus.cloudapp.azure.com:7233}
VIDEO_URL=${1:-https://s3.us-east-1.amazonaws.com/blobs.chrisumbel.com/jfk.mp4}
shift || true
LANGUAGES=${@:-fr es}

export TEMPORAL_ADDRESS
exec python3 -m tvt.temporal.start "$VIDEO_URL" $LANGUAGES
