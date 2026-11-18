#!/usr/bin/env bash
# Release gate. Nothing ships unless this passes. See docs/pentest.md.
# Usage: scripts/release-check.sh <part>
#   <part> is a folder in the repo ("." for a single-package repo).
#   Node parts need "test" and "pentest" npm scripts.
#   Swift parts need a Package.swift (attack cases live in its tests).
# Override the version with VERSION=x.y.z if it can't be found.
set -euo pipefail
part="${1:-}"
[ -n "$part" ] || { echo "usage: $0 <part>" >&2; exit 2; }
root="$(git rev-parse --show-toplevel)"
cd "$root"
[ -d "$part" ] || { echo "no folder: $part" >&2; exit 2; }
name="$([ "$part" = . ] && basename "$root" || basename "$part")"

step() { printf '\n== %s\n' "$1"; }
die()  { printf '\nRELEASE BLOCKED (%s): %s\n' "$name" "$1" >&2; exit 1; }

if [ -f "$part/package.json" ]; then
  version="${VERSION:-$(node -p "require('./$part/package.json').version")}"
  step "1. Unit tests and build"
  (cd "$part" && npm test) || die "unit tests failed"
  if node -e "process.exit(require('./$part/package.json').scripts?.build ? 0 : 1)"; then
    (cd "$part" && npm run build) || die "build failed"
  fi
  step "2. Attack suite"
  (cd "$part" && npm run pentest) || die "attack suite failed (add a \"pentest\" script)"
  step "3. Dependency audit (shipped packages, high and critical)"
  (cd "$part" && npm audit --omit=dev --audit-level=high) || die "vulnerable dependency"
elif [ -f "$part/pyproject.toml" ]; then
  # Python server, plus its React dashboard in web/ (Net Logger)
  version="${VERSION:-$(sed -nE 's/^__version__ = "(.*)"/\1/p' "$part"/*/__init__.py | head -1)}"
  [ -n "$version" ] || die "version not found: set VERSION=x.y.z"
  step "1. Unit tests and dashboard build"
  (cd "$part" && python3 -m pytest -q) || die "unit tests failed"
  if [ -f "$part/web/package.json" ]; then
    (cd "$part/web" && npm ci --silent && npm run build) || die "dashboard build failed"
  fi
  step "2. Attack suite"
  (cd "$part" && python3 -m pytest -q tests/test_pentest.py) || die "attack suite failed"
  step "3. Dependency audit (shipped packages, high and critical)"
  command -v pip-audit >/dev/null || die "pip-audit not found: pip install pip-audit"
  (cd "$part" && pip-audit -r requirements.txt --progress-spinner off) || die "vulnerable Python dependency"
  if [ -f "$part/web/package.json" ]; then
    (cd "$part/web" && npm audit --omit=dev --audit-level=high) || die "vulnerable npm dependency"
  fi
elif pkg="$(find "$part" -maxdepth 3 -name Package.swift -not -path '*/.build/*' | head -1)" && [ -n "$pkg" ]; then
  yml="$(find "$part" -maxdepth 1 -name project.yml | head -1)"
  version="${VERSION:-$( [ -n "$yml" ] && grep -m1 -E '^\s*MARKETING_VERSION:' "$yml" | sed -E 's/.*: *"?([^"]+)"?/\1/' || true)}"
  [ -n "$version" ] || die "version not found: set VERSION=x.y.z"
  step "1+2. Swift tests (unit and attack cases)"
  command -v swift >/dev/null || die "swift not found: run this on a Mac with Xcode"
  (cd "$(dirname "$pkg")" && swift test) || die "Swift tests failed"
  step "3. Dependency audit"
  echo "Review Package.resolved by hand: list every package in licensing.md and check its advisories."
else
  die "no package.json, pyproject.toml or Package.swift in $part"
fi

step "4. Secret scan"
scripts/secret-scan.sh || die "secret scan failed"

step "5. Pen test report"
report="$(ls docs/pentests/*-"$name"-"$version".md 2>/dev/null | tail -1 || true)"
[ -n "$report" ] || die "no report: docs/pentests/YYYY-MM-DD-$name-$version.md"
grep -qE '^[-* ]*\**Result:\**[[:space:]]*Pass[[:space:]]*$' "$report" || die "$report does not say Result: Pass"
echo "found $report"

printf '\nRELEASE OK: %s %s\n' "$name" "$version"
