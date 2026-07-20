#!/usr/bin/env bash
# Port-forward the Temporal admin UI from AKS and print its local URL.
# Runs until Ctrl-C.
set -euo pipefail

CONTEXT=${CONTEXT:-tvt-aks}
NAMESPACE=${NAMESPACE:-temporal-video-translator}
PORT=${PORT:-8080}

echo "Temporal admin UI: http://localhost:${PORT}  (Ctrl-C to stop)"
exec kubectl --context "$CONTEXT" -n "$NAMESPACE" port-forward svc/temporal-ui "${PORT}:8080"
