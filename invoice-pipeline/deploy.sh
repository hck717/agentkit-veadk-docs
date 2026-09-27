#!/usr/bin/env bash
set -euo pipefail

# Invoice Pipeline — Deployment Script
# Prerequisites: AgentKit CLI installed, AK/SK configured
# Usage: ./deploy.sh [staging|production]

ENV="${1:-staging}"
echo "==> Deploying invoice pipeline to: $ENV"

deploy_agent() {
  local name=$1 app=$2
  echo "  -> Deploying $name as $app-$ENV"
  ak deploy "$name" --app-name "$app-$ENV" --region cn-beijing
}

deploy_agent "ocr-agent"          "invoice-ocr"
deploy_agent "translation-agent"  "invoice-translation"
deploy_agent "validation-agent"   "invoice-validation"
deploy_agent "aggregation-agent"  "invoice-aggregation"
deploy_agent "approval-agent"     "invoice-approval"

echo "==> Deployment complete: $ENV"
