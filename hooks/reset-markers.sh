#!/usr/bin/env bash
# Portions of this file are adapted from the n8n-io/skills plugin
# (https://github.com/n8n-io/skills), licensed under Apache License 2.0.
# See /NOTICES.
#
# SessionStart hook. Wipes the PreToolUse dedup markers on /clear and /compact,
# because the agent's memory of those reminders is gone after a context reset
# and the markers must not keep them silent.
#
# This hook deliberately emits NOTHING on stdout. Upstream injected the whole
# router skill here, which cost every session — n8n-related or not — roughly
# 700 tokens. The injection is gone; only the reset behavior is kept.
#
# Always exits 0. Never blocks session startup.

set -uo pipefail

STATE_DIR="${TMPDIR:-/tmp}/n8n-skills-state"
INPUT="$(cat)"

read_field() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "${INPUT}" | jq -r ".${1} // empty" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "${INPUT}" | python3 -c \
      "import json,sys; print(json.load(sys.stdin).get('${1}',''))" 2>/dev/null
  fi
}

SOURCE="$(read_field source)"
SESSION_ID="$(read_field session_id)"

if [[ "${SOURCE}" == "clear" || "${SOURCE}" == "compact" ]] \
   && [[ -n "${SESSION_ID}" ]]; then
  rm -f "${STATE_DIR}/${SESSION_ID}-"*.loaded 2>/dev/null || true
fi

# Garbage-collect markers from sessions that ended long ago, so $TMPDIR does
# not accumulate one file per session per marker forever.
if [[ -d "${STATE_DIR}" ]]; then
  find "${STATE_DIR}" -name '*.loaded' -type f -mtime +7 -delete 2>/dev/null || true
fi

exit 0
