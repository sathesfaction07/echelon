#!/usr/bin/env bash
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${BLUE}==>${NC} $1"; }
ok()    { echo -e "${GREEN} ok ${NC} $1"; }
warn()  { echo -e "${YELLOW}warn${NC} $1"; }
fail()  { echo -e "${RED}fail${NC} $1"; exit 1; }

# ---------------------------------------------------------------------------
# 1. Python version check
# ---------------------------------------------------------------------------
info "Checking Python"
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 was not found. Install it first:"
    echo "  macOS:         brew install python@3.12"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "  RHEL/Fedora:   sudo dnf install python3"
    fail "python3 missing"
fi

PY_OK=$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 11) else 0)')
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [ "$PY_OK" != "1" ]; then
    echo "Python 3.11 or newer is required. Found $PY_VER."
    echo "  macOS:         brew install python@3.12"
    echo "  Ubuntu/Debian: sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.12 python3.12-venv"
    fail "python $PY_VER too old"
fi
ok "Python $PY_VER"

# ---------------------------------------------------------------------------
# 2. Virtual environment
# ---------------------------------------------------------------------------
info "Creating virtual environment"
if [ ! -d .venv ]; then
    python3 -m venv .venv || fail "could not create .venv (on Debian/Ubuntu you may need: sudo apt install python3-venv)"
fi
ok ".venv ready"

# ---------------------------------------------------------------------------
# 3. Install dev dependencies
# ---------------------------------------------------------------------------
info "Installing dependencies [dev]"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e ".[dev]" || fail "pip install failed"
ok "dependencies installed"

# ---------------------------------------------------------------------------
# 4. Verify core imports
# ---------------------------------------------------------------------------
info "Verifying imports"
.venv/bin/python - <<'PYCHECK' || fail "core imports failed"
import delegate_chain                                               # noqa: F401
from delegate_chain.core.schemas import LEVEL_ORDER, Task, Artifact     # noqa: F401
from delegate_chain.core.schemas import SubTask, ReviewVerdict          # noqa: F401
from delegate_chain.core.schemas import level_index, next_down          # noqa: F401
PYCHECK
ok "imports resolve"

# ---------------------------------------------------------------------------
# 5. Verify schema logic
# ---------------------------------------------------------------------------
info "Verifying schema logic"
.venv/bin/python - <<'PYCHECK' || fail "schema verification failed"
from delegate_chain.core.schemas import LEVEL_ORDER, Task, level_index, next_down, clamp_below

assert LEVEL_ORDER == ["engineer", "senior", "staff", "principal", "distinguished"], \
    f"unexpected LEVEL_ORDER: {LEVEL_ORDER}"

assert level_index("engineer") == 0
assert level_index("distinguished") == 4

assert next_down("senior") == "engineer"
assert next_down("engineer") is None, "engineer has no level below"

assert clamp_below("staff", "engineer") == "engineer"
assert clamp_below("staff", "distinguished") == "senior", \
    "clamp_below must return a level strictly below staff"

t = Task(description="Add OAuth2 support", scope="component")
assert t.description == "Add OAuth2 support"
assert t.feedback is None

print("     LEVEL_ORDER has 5 levels; Task, SubTask, clamp_below all correct")
PYCHECK
ok "schema logic verified"

# ---------------------------------------------------------------------------
# 6. AWS credentials check (warn only — boto3 is a hard dependency)
# ---------------------------------------------------------------------------
info "Checking AWS credentials (required for Bedrock LLM calls)"
if .venv/bin/python -c "import boto3; boto3.client('sts').get_caller_identity()" >/dev/null 2>&1; then
    ok "AWS credentials resolve"
else
    warn "No usable AWS credentials found."
    warn "  Configure with: aws configure   (or set AWS_PROFILE / AWS_ACCESS_KEY_ID)"
    warn "  Bedrock LLM calls and KB ingestion will fail without valid credentials."
    warn "  Schema logic, unit tests, and offline orchestration work without AWS."
fi

# ---------------------------------------------------------------------------
# 7. Run the test suite
# ---------------------------------------------------------------------------
info "Running the test suite"
.venv/bin/python -m pytest -q || fail "tests failed"
ok "tests pass"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
cat <<'DONE'

Setup complete.

  source .venv/bin/activate

  delegate-chain --help                          # show CLI commands

  # Run a delegation chain from the principal level down:
  #   from delegate_chain.schemas import Task
  #   from delegate_chain.agents.level_agent import LevelAgent
  #   task = Task(description="Design caching layer", scope="component")

AWS credentials are needed for:
  • Bedrock LLM calls (us-east-1 by default)
  • S3 / DynamoDB knowledge-base persistence
DONE
