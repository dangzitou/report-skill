#!/bin/sh
# report-skill installer: non-interactive and safe to re-run.
#
#   curl -fsSL https://raw.githubusercontent.com/dangzitou/report-skill/main/install.sh | sh
#
# Installs the CLI (via uv, pipx, or a private venv, in that order), then runs
# `report-skill setup`, which installs the agent skill into every agent found
# (Claude Code, Codex, ZCode, OpenCode, ~/.agents) and writes a minimal config.
# Last line is machine-readable: `REPORT_SKILL_OK <path>` or `REPORT_SKILL_FAIL <reason>`.
#
# Env: REPORT_SKILL_REF=v0.3.0 to pin a version (default: main).
set -eu

REF="${REPORT_SKILL_REF:-main}"
SRC="git+https://github.com/dangzitou/report-skill@${REF}"
BIN_DIR="${HOME}/.local/bin"

say() { printf '%s\n' "report-skill: $*" >&2; }
fail() { say "$1"; echo "REPORT_SKILL_FAIL $1"; exit 1; }

find_bin() {
  for c in "$(command -v report-skill 2>/dev/null || true)" "${BIN_DIR}/report-skill" \
           "${HOME}/.local/share/report-skill/venv/bin/report-skill"; do
    if [ -n "$c" ] && [ -x "$c" ]; then echo "$c"; return 0; fi
  done
  return 1
}

if command -v uv >/dev/null 2>&1; then
  say "installing with uv"
  uv tool install --force --quiet "report-skill @ ${SRC}" >&2 || fail "uv tool install failed"
elif command -v pipx >/dev/null 2>&1; then
  say "installing with pipx"
  pipx install --force "${SRC}" >&2 || fail "pipx install failed"
else
  PY="$(command -v python3 || true)"
  [ -n "$PY" ] || fail "python3 not found (need Python 3.9+); or install uv: https://docs.astral.sh/uv/"
  "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || fail "need Python 3.9+"
  VENV="${HOME}/.local/share/report-skill/venv"
  say "installing into a private venv at ${VENV}"
  "$PY" -m venv "$VENV" >&2 || fail "could not create venv"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip >&2 || true
  "$VENV/bin/python" -m pip install --quiet --upgrade "${SRC}" >&2 || fail "pip install failed (is git installed?)"
  mkdir -p "$BIN_DIR"
  ln -sf "$VENV/bin/report-skill" "$BIN_DIR/report-skill"
fi

BIN="$(find_bin)" || fail "installed, but the report-skill command was not found"
"$BIN" setup >&2 || fail "report-skill setup failed"

case ":${PATH}:" in
  *":$(dirname "$BIN"):"*) ;;
  *) say "note: $(dirname "$BIN") is not on PATH; add: export PATH=\"$(dirname "$BIN"):\$PATH\"" ;;
esac
echo "REPORT_SKILL_OK $BIN"
