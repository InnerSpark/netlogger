#!/usr/bin/env bash
# Net Logger installer for an AllStar (ASL3) server on Debian.
#
#   sudo ./install.sh                  # interactive
#   sudo ./install.sh --yes            # no questions, restart Asterisk when needed
#
# What it does:
#   - Installs Net Logger in /opt/netlogger with its own Python venv and a system user.
#   - Runs it as a systemd service at lower priority than Asterisk, dashboard on 127.0.0.1:8080.
#   - Adds a private logger node and an AMI user WITHOUT editing your existing node settings:
#     it adds one "#tryinclude" line to rpt.conf and manager.conf and keeps its own config in
#     /etc/asterisk/netlogger/. Every file it touches is backed up first.
#   - Safe to run again. ./uninstall.sh reverses the Asterisk changes.
set -euo pipefail

MARK="; added by netlogger installer"
APP_DIR=/opt/netlogger
DATA_DIR=/var/lib/netlogger
ETC_DIR=/etc/netlogger
ENV_FILE=$ETC_DIR/netlogger.env
UNIT=/etc/systemd/system/netlogger.service
WEB_DIST_URL="https://github.com/InnerSpark/netlogger/releases/latest/download/web-dist.tgz"

AST=/etc/asterisk
LOGGER_NODE=""
DEFAULT_NODE=""
MODEL=""
ASSUME_YES=0
RESTART=ask
CONFIG_ONLY=0   # testing: only the Asterisk config part
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: sudo ./install.sh [options]
  --node N            Logger's private node number (default: 1999, must be under 2000)
  --default-node N    Node to offer on the dashboard (default: your first node in rpt.conf)
  --model NAME        Whisper model: tiny.en, base.en, small.en, medium.en (default: picked from CPU/RAM)
  --yes               Don't ask; restart Asterisk if needed
  --no-restart        Never restart Asterisk (do it yourself later)
  --asterisk-dir DIR  Asterisk config dir (default: /etc/asterisk)
  --config-only       Only add the Asterisk config (for testing)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --node) LOGGER_NODE="$2"; shift 2 ;;
    --default-node) DEFAULT_NODE="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --yes|-y) ASSUME_YES=1; [ "$RESTART" = ask ] && RESTART=yes; shift ;;
    --no-restart) RESTART=no; shift ;;
    --asterisk-dir) AST="$2"; shift 2 ;;
    --config-only) CONFIG_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

say()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
ok()   { printf '    %s\n' "$*"; }
warn() { printf '\033[33m!!\033[0m  %s\n' "$*"; }
die()  { printf '\033[31mError:\033[0m %s\n' "$*" >&2; exit 1; }

STAMP="$(date +%Y%m%d-%H%M%S)"
backup() {  # backup FILE, once per run
  local f="$1"
  [ -f "$f" ] || return 0
  [ -f "$f.netlogger-bak-$STAMP" ] || cp -p "$f" "$f.netlogger-bak-$STAMP"
  ok "backed up $(basename "$f") -> $(basename "$f").netlogger-bak-$STAMP"
}

ask() {  # ask "question" -> 0 for yes
  [ "$ASSUME_YES" = 1 ] && return 0
  local a
  read -r -p "$1 [y/N] " a </dev/tty || return 1
  [[ "$a" =~ ^[Yy] ]]
}

# ---------------------------------------------------------------- checks
if [ "$CONFIG_ONLY" = 0 ]; then
  [ "$(id -u)" = 0 ] || die "Run with sudo."
  [ -f /etc/debian_version ] || die "This installer is for Debian (ASL3). For other systems, use Docker (see README)."
  command -v asterisk >/dev/null || die "Asterisk isn't installed. Install ASL3 first, or run Net Logger on another computer with Docker."
fi
[ -f "$AST/rpt.conf" ] || die "Can't find $AST/rpt.conf."
[ -f "$AST/manager.conf" ] || die "Can't find $AST/manager.conf."

# Values from a previous run win, so running again changes nothing
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  PREV_NODE="$(grep -E '^LOGGER_NODE=' "$ENV_FILE" | cut -d= -f2- || true)"
  PREV_SECRET="$(grep -E '^AMI_SECRET=' "$ENV_FILE" | cut -d= -f2- || true)"
  PREV_DEFAULT="$(grep -E '^DEFAULT_NODE=' "$ENV_FILE" | cut -d= -f2- || true)"
fi
LOGGER_NODE="${LOGGER_NODE:-${PREV_NODE:-1999}}"
[[ "$LOGGER_NODE" =~ ^[0-9]{3,4}$ ]] && [ "$LOGGER_NODE" -lt 2000 ] || die "--node must be a private node number under 2000."

grep -qE '^\[node-main\]\(!\)' "$AST/rpt.conf" \
  || die "rpt.conf has no [node-main](!) template (ASL3 has one). Set up the logger node by hand: docs/allstar-setup.md."

INC_DIR="$AST/netlogger"
RPT_INC="$INC_DIR/rpt.conf"
MGR_INC="$INC_DIR/manager.conf"

# Is the node number already used by something other than us?
if grep -qE "^\[$LOGGER_NODE\]" "$AST/rpt.conf" || grep -qE "^\s*$LOGGER_NODE\s*=" "$AST/rpt.conf"; then
  die "Node $LOGGER_NODE is already in rpt.conf. Pick another private number with --node."
fi

# Your node(s): numbers under [nodes] other than private ones and the logger
YOUR_NODES="$(awk '/^\[nodes\]/{f=1;next} /^\[/{f=0} f && /^[[:space:]]*[0-9]+[[:space:]]*=/{gsub(/[[:space:]]/,"");split($0,a,"=");print a[1]}' "$AST/rpt.conf" | awk '$1>=2000' | tr '\n' ' ')"
DEFAULT_NODE="${DEFAULT_NODE:-${PREV_DEFAULT:-$(echo "$YOUR_NODES" | awk '{print $1}')}}"

say "Net Logger installer"
ok "Asterisk config: $AST"
ok "Logger node: $LOGGER_NODE (private, monitor-only)"
ok "Your node(s): ${YOUR_NODES:-none found}"
ok "Default node on the dashboard: ${DEFAULT_NODE:-none}"

# ---------------------------------------------------------------- Asterisk config
say "Adding Asterisk config (your existing settings are not edited)"
mkdir -p "$INC_DIR"

# Reuse the secret from an earlier run so AMI and Net Logger stay in sync
[ -z "${PREV_SECRET:-}" ] && [ -f "$MGR_INC" ] && PREV_SECRET="$(awk -F' *= *' '/^secret/{print $2}' "$MGR_INC")"
SECRET="${PREV_SECRET:-$(head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)}"
CHANGED=0

write_if_changed() {  # write_if_changed FILE CONTENT
  if [ ! -f "$1" ] || [ "$(cat "$1")" != "$2" ]; then
    printf '%s\n' "$2" > "$1"
    CHANGED=1
    ok "wrote $1"
  else
    ok "$1 already up to date"
  fi
}

write_if_changed "$RPT_INC" "; Net Logger private node. Managed by the Net Logger installer.
; Receive-only: audio goes out to Net Logger over USRP on 127.0.0.1, nothing comes back.
[$LOGGER_NODE](node-main)
rxchannel = USRP/127.0.0.1:34001:32001
duplex = 0
telemdefault = 0

[nodes](+)
$LOGGER_NODE = radio@127.0.0.1/$LOGGER_NODE,NONE"

write_if_changed "$MGR_INC" "; Net Logger AMI user. Managed by the Net Logger installer.
; Only allowed from this machine, and only for CLI commands.
[netlogger]
secret = $SECRET
deny = 0.0.0.0/0.0.0.0
permit = 127.0.0.1/255.255.255.255
read = command
write = command"
chmod 640 "$MGR_INC"
chown root:asterisk "$MGR_INC" 2>/dev/null || true

add_include() {  # add_include FILE INCLUDE_PATH
  local f="$1" inc="$2"
  if grep -qF "#tryinclude \"$inc\"" "$f"; then
    ok "$(basename "$f") already includes $inc"
    return
  fi
  backup "$f"
  printf '\n%s\n#tryinclude "%s"\n' "$MARK" "$inc" >> "$f"
  CHANGED=1
  ok "added one include line to $(basename "$f")"
}
add_include "$AST/rpt.conf" "netlogger/rpt.conf"
add_include "$AST/manager.conf" "netlogger/manager.conf"

# AMI must be on (it usually is on ASL3, Supermon and Allmon use it)
if ! awk '/^\[general\]/{f=1;next} /^\[/{f=0} f' "$AST/manager.conf" | grep -qE '^\s*enabled\s*=\s*yes'; then
  warn "AMI looks off in manager.conf ([general] enabled = yes). Node control won't work until it's on."
fi

# chan_usrp must load
if [ -f "$AST/modules.conf" ]; then
  if grep -qE '^\s*noload\s*=>?\s*chan_usrp\.so' "$AST/modules.conf"; then
    backup "$AST/modules.conf"
    sed -i -E "s/^(\s*noload\s*=>?\s*chan_usrp\.so.*)$/;netlogger-disabled: \1/" "$AST/modules.conf"
    CHANGED=1
    ok "turned off 'noload chan_usrp.so' in modules.conf"
  fi
  if grep -qE '^\s*autoload\s*=\s*no' "$AST/modules.conf" && ! grep -qE '^\s*load\s*=>?\s*chan_usrp\.so' "$AST/modules.conf"; then
    backup "$AST/modules.conf"
    printf '%s\nload = chan_usrp.so\n' "$MARK" >> "$AST/modules.conf"
    CHANGED=1
    ok "added 'load = chan_usrp.so' to modules.conf"
  fi
fi

if [ "$CONFIG_ONLY" = 1 ]; then
  say "Config-only run done. Secret: $SECRET"
  exit 0
fi

# ---------------------------------------------------------------- app
say "Installing Net Logger to $APP_DIR"
apt-get update -qq
apt-get install -y -qq python3 python3-venv >/dev/null
id netlogger >/dev/null 2>&1 || useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin netlogger
mkdir -p "$APP_DIR" "$DATA_DIR" "$ETC_DIR"
chown netlogger:netlogger "$DATA_DIR"

if [ "$SRC_DIR" != "$APP_DIR" ]; then
  tar -C "$SRC_DIR" --exclude=.git --exclude=web/node_modules --exclude=.venv --exclude=data -cf - . | tar -C "$APP_DIR" -xf -
fi

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
ok "Python packages installed"

# Dashboard: use a prebuilt copy, build it if Node 20+ is here, or download the release build
if [ ! -f "$APP_DIR/web/dist/index.html" ]; then
  NODE_MAJOR="$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || echo 0)"
  if [ "${NODE_MAJOR:-0}" -ge 20 ]; then
    ok "building the dashboard with Node $(node -v)"
    (cd "$APP_DIR/web" && npm ci --silent && npm run build --silent) >/dev/null
  else
    ok "downloading the prebuilt dashboard"
    mkdir -p "$APP_DIR/web/dist"
    curl -fsSL "$WEB_DIST_URL" | tar -xz -C "$APP_DIR/web/dist" \
      || die "Couldn't get the dashboard. Install Node 20+ (apt install nodejs npm) and run this again."
  fi
fi
ok "dashboard ready"

# Settings: sized to this machine, kept on later runs
CORES="$(nproc)"
MEM_GB="$(awk '/MemAvailable/{printf "%d", $2/1024/1024}' /proc/meminfo)"
if [ -z "$MODEL" ]; then
  if [ "$CORES" -ge 4 ] && [ "$MEM_GB" -ge 4 ]; then MODEL=small.en
  elif [ "$CORES" -ge 2 ] && [ "$MEM_GB" -ge 2 ]; then MODEL=base.en
  else MODEL=tiny.en; warn "Only $CORES CPU / ${MEM_GB} GB free. Using tiny.en; expect rough transcripts."
  fi
fi
THREADS=$(( CORES > 1 ? CORES - 1 : 1 ))  # leave a core for Asterisk

if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<EOF
# Net Logger settings. Restart after changes: sudo systemctl restart netlogger
DATA_DIR=$DATA_DIR
HTTP_HOST=127.0.0.1
HTTP_PORT=8080
USRP_PORT=34001
WHISPER_MODEL=$MODEL
WHISPER_THREADS=$THREADS
MIN_SECONDS=0.8
CALL_LOOKUP=1
AMI_HOST=127.0.0.1
AMI_PORT=5038
AMI_USER=netlogger
AMI_SECRET=$SECRET
LOGGER_NODE=$LOGGER_NODE
DEFAULT_NODE=$DEFAULT_NODE
AUTO_CONNECT=0
# Set both to 1 once the dashboard is behind HTTPS on a subdomain
TRUST_PROXY=1
COOKIE_SECURE=1
SESSION_DAYS=30
EOF
  ok "wrote $ENV_FILE (model $MODEL, $THREADS threads)"
else
  ok "kept existing $ENV_FILE"
fi
chown root:netlogger "$ENV_FILE"
chmod 640 "$ENV_FILE"

cat > "$UNIT" <<EOF
[Unit]
Description=Net Logger (receive-only AllStar net check-in logger)
After=network-online.target asterisk.service
Wants=network-online.target

[Service]
User=netlogger
Group=netlogger
EnvironmentFile=$ENV_FILE
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -m netlogger
Restart=always
RestartSec=5
# Asterisk comes first: lower CPU priority and weight
Nice=10
CPUWeight=50
# Hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=$DATA_DIR

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now netlogger >/dev/null 2>&1
systemctl restart netlogger
ok "service running: systemctl status netlogger"

# ---------------------------------------------------------------- restart Asterisk
if [ "$CHANGED" = 1 ]; then
  say "Asterisk needs a restart to add node $LOGGER_NODE"
  ok "This drops current links for a few seconds."
  if [ "$RESTART" = yes ] || { [ "$RESTART" = ask ] && ask "Restart Asterisk now?"; }; then
    systemctl restart asterisk
    sleep 5
    ok "Asterisk restarted"
  else
    warn "Not restarted. When the node is quiet, run: sudo systemctl restart asterisk"
  fi
else
  ok "Asterisk config unchanged, no restart needed"
fi

# ---------------------------------------------------------------- check
say "Checking"
if asterisk -rx "module show like usrp" 2>/dev/null | grep -q chan_usrp; then ok "chan_usrp loaded"; else warn "chan_usrp not loaded yet (restart Asterisk)"; fi
if asterisk -rx "rpt localnodes" 2>/dev/null | grep -qw "$LOGGER_NODE"; then ok "node $LOGGER_NODE is up"; else warn "node $LOGGER_NODE not up yet (restart Asterisk)"; fi
if curl -fsS -o /dev/null http://127.0.0.1:8080/api/auth/status; then ok "dashboard answering on 127.0.0.1:8080"; else warn "dashboard not answering yet: journalctl -u netlogger -f"; fi

cat <<EOF

Done.

Next:
  1. Put the dashboard on a subdomain with HTTPS: docs/same-server.md, step 6.
  2. Open it and create the admin account right away.
  3. The Setup page shows a live status check.

Logs:       journalctl -u netlogger -f
Settings:   $ENV_FILE
Uninstall:  sudo $APP_DIR/uninstall.sh
EOF
