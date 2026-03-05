#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: scripts/deploy_cloud_run.sh <gcp-project-id> <service-name> [region]"
  exit 1
fi

PROJECT_ID="$1"
SERVICE_NAME="$2"
REGION="${3:-australia-southeast1}"

gcloud config set project "${PROJECT_ID}"
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated
