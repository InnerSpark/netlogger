#!/usr/bin/env bash
# Fails if any tracked file looks like it holds a real secret.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail=0
# Files that should never be tracked at all.
if git ls-files | grep -Ei '(^|/)(\.env(\..*)?|deploy\.env|.*\.pem|.*\.p12|.*\.p8|.*\.key|id_(rsa|ed25519))$' | grep -v '\.env\.example$'; then
  echo "secret-scan: secret-type file is tracked (above)"; fail=1
fi

# Strings that look like real keys. Lines marked as examples are skipped.
patterns=(
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  'ptl[ac]_[A-Za-z0-9]{30,}'          # Pelican API keys
  'AKIA[0-9A-Z]{16}'                  # AWS
  'gh[pousr]_[A-Za-z0-9]{36,}'        # GitHub
  'xox[abpr]-[A-Za-z0-9-]{10,}'       # Slack
  'sk-[A-Za-z0-9_-]{32,}'             # OpenAI/Anthropic style
  'tskey-[A-Za-z0-9-]{20,}'           # Tailscale auth keys
)
for p in "${patterns[@]}"; do
  if git grep -nIE -e "$p" -- ':!scripts/secret-scan.sh' | grep -viE 'example|placeholder|xxxxx'; then
    echo "secret-scan: possible secret matching /$p/ (above)"; fail=1
  fi
done

[ "$fail" = 0 ] && echo "secret-scan: clean"
exit "$fail"
