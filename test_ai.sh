#!/bin/bash
set -e

URL=${URL:-http://localhost:5000}

echo "🧪 Testing AI command endpoint (dry run)..."
if ! command -v curl >/dev/null 2>&1; then
  echo "❌ curl not found. Install with: sudo apt install curl"
  exit 1
fi

RESP=$(curl -s -X POST "$URL/api/ai/command" \
  -H 'Content-Type: application/json' \
  -d '{"text":"tune to 104.1","dry_run":true}')

echo "$RESP" | sed 's/.*/&\n/'
if echo "$RESP" | grep -q "OpenAI API key not configured"; then
  echo "ℹ️  AI endpoint reachable. Configure your OpenAI key in Settings or export OPENAI_API_KEY."
fi

echo "✅ AI test finished"


