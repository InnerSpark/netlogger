#!/usr/bin/env bash
# Removes Net Logger from an AllStar server and puts the Asterisk config back.
#   sudo ./uninstall.sh            # keep net logs and accounts in /var/lib/netlogger
#   sudo ./uninstall.sh --purge    # delete them too
set -euo pipefail

AST=/etc/asterisk
PURGE=0
RESTART=ask
CONFIG_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --purge) PURGE=1; shift ;;
    --yes|-y) RESTART=yes; shift ;;
    --no-restart) RESTART=no; shift ;;
    --asterisk-dir) AST="$2"; shift 2 ;;
    --config-only) CONFIG_ONLY=1; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
ok()  { printf '    %s\n' "$*"; }

if [ "$CONFIG_ONLY" = 0 ] && [ "$(id -u)" != 0 ]; then echo "Run with sudo."; exit 1; fi
STAMP="$(date +%Y%m%d-%H%M%S)"

say "Removing Asterisk config"
for f in rpt.conf manager.conf modules.conf; do
  p="$AST/$f"
  [ -f "$p" ] || continue
  if grep -qE 'added by netlogger installer|^;netlogger-disabled: ' "$p"; then
    cp -p "$p" "$p.netlogger-bak-$STAMP"
    # drop lines we added, restore lines we commented out, and the blank line before our include
    # our marker line, the line right after it, and lines we commented out
    sed -i -E '/added by netlogger installer/{N;d}; s/^;netlogger-disabled: //' "$p"
    sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$p"
    ok "cleaned $f (backup: $f.netlogger-bak-$STAMP)"
  fi
done
rm -rf "${AST:?}/netlogger"
ok "removed $AST/netlogger/"

if [ "$CONFIG_ONLY" = 1 ]; then exit 0; fi

say "Removing the service"
systemctl disable --now netlogger 2>/dev/null || true
rm -f /etc/systemd/system/netlogger.service
rm -f /usr/local/bin/netlogger
systemctl daemon-reload
rm -rf /opt/netlogger /etc/netlogger
if [ "$PURGE" = 1 ]; then
  rm -rf /var/lib/netlogger
  userdel netlogger 2>/dev/null || true
  ok "removed app, settings, data and user"
else
  ok "removed app and settings. Net logs kept in /var/lib/netlogger (use --purge to delete)"
fi

if [ "$RESTART" = yes ] || { [ "$RESTART" = ask ] && read -r -p "Restart Asterisk now to drop the logger node? [y/N] " a </dev/tty && [[ "$a" =~ ^[Yy] ]]; }; then
  systemctl restart asterisk
  ok "Asterisk restarted"
else
  ok "Restart Asterisk later to drop the logger node: sudo systemctl restart asterisk"
fi
