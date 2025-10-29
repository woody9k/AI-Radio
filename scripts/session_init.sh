#!/bin/bash
set -e

ROOT_DIR=$(cd "$(dirname "$0")"/.. && pwd)
cd "$ROOT_DIR"

echo "📘 AI-Radio Session Init"
echo "Repo: $ROOT_DIR"

# Docs quick links
echo "🔗 Docs:"
echo "- Style: docs/STYLE_GUIDE.md"
echo "- Standards: docs/CODING_STANDARDS.md"
echo "- API: docs/API.md (OpenAPI: docs/openapi.yaml)"
echo "- Architecture: docs/ARCHITECTURE.md"

auto_fix=false
no_start=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --fix) auto_fix=true; shift ;;
    --no-start) no_start=true; shift ;;
    *) shift ;;
  esac
done

# Ensure prerequisites
if ! command -v python3 >/dev/null 2>&1; then echo "❌ python3 not found"; exit 1; fi
if ! command -v node >/dev/null 2>&1; then echo "⚠️  node not found (frontend dev)"; fi
if ! command -v npm >/dev/null 2>&1; then echo "⚠️  npm not found (frontend dev)"; fi

# Python venv
if [ ! -d venv ]; then
  echo "🔧 Creating venv..."; python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1 || true
# Ensure dev tools exist
pip install black ruff mypy >/dev/null 2>&1 || true

# Frontend deps if missing
if [ ! -d frontend/node_modules ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "📦 Installing frontend deps..."
    (cd frontend && npm install --no-audit --no-fund >/dev/null 2>&1 || true)
  fi
fi

# Conformance checks
echo "🧪 Running conformance checks..."
py_fail=0; js_fail=0

# Ruff
if ! ruff --version >/dev/null 2>&1; then pip install ruff >/dev/null 2>&1; fi
ruff . || py_fail=1

# Black (check)
if ! black --version >/dev/null 2>&1; then pip install black >/dev/null 2>&1; fi
if $auto_fix; then
  black . || true
else
  black --check . || py_fail=1
fi

# MyPy (best-effort)
if mypy --version >/dev/null 2>&1; then
  mypy backend || true
fi

# ESLint
if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm run lint) || js_fail=1
fi

if [ $py_fail -ne 0 ] || [ $js_fail -ne 0 ]; then
  echo "❌ Conformance failed: py=$py_fail js=$js_fail"
  echo "   Try: scripts/session_init.sh --fix"
  exit 1
fi

echo "✅ Conformance OK"

if $no_start; then
  echo "⏭️  Skipping service start (--no-start)"
  exit 0
fi

# Optional device and AI tests (best-effort)
if [ -x ./test_rtlsdr.sh ]; then ./test_rtlsdr.sh --clean || true; fi
if [ -x ./test_ai.sh ]; then ./test_ai.sh || true; fi

# Start services
./start.sh
