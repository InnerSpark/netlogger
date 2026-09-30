# Running on your AllStar server

If you run your own AllStar node (ASL3 on Debian, a VPS or a Pi), install Net Logger right on it. Audio and node control stay on the same box, the dashboard gets a subdomain with HTTPS, and the logger can link to **any public node** through your server.

The installer **doesn't edit your existing node settings**. It adds one `#tryinclude` line to `rpt.conf` and `manager.conf`, keeps its own config in `/etc/asterisk/netlogger/`, and backs up every file it touches.

## Is the server big enough?

Speech to text needs real CPU. Check with `nproc; free -h`.

| Server | Model the installer picks |
|---|---|
| 4+ vCPU and 4 GB free | `small.en` (best) |
| 2 vCPU and 2 GB free | `base.en` |
| Smaller | `tiny.en`, rough transcripts. Consider running Net Logger on another computer ([allstar-setup.md](allstar-setup.md)). |

Net Logger runs at lower priority than Asterisk and leaves a core free, so the node keeps first claim on the CPU.

## 1. Install

```
cd /opt
sudo git clone https://github.com/InnerSpark/netlogger.git
cd netlogger
sudo ./install.sh
```

It will:

1. Back up `rpt.conf`, `manager.conf` and `modules.conf`.
2. Add private node **1999** (monitor-only, audio to Net Logger on `127.0.0.1`). Use `--node 1998` if 1999 is taken.
3. Add an AMI user `netlogger` with a random secret, allowed from `127.0.0.1` only, `command` rights only.
4. Make sure `chan_usrp` loads.
5. Install Net Logger in `/opt/netlogger` with its own Python environment, running as the `netlogger` user under systemd.
6. Pick a Whisper model for your CPU and RAM, and write settings to `/etc/netlogger/netlogger.env`.
7. **Ask before restarting Asterisk.** Adding a node needs a restart, which drops links for a few seconds. Say no to do it later when the node is quiet.

Running it again is safe. It only changes what's missing.

**Dashboard files:** the installer uses the prebuilt dashboard from the latest GitHub release. If that isn't available, it builds it, which needs Node 20+: `sudo apt install -y nodejs npm`, then run the installer again.

Options: `sudo ./install.sh --help`

## 2. Subdomain with HTTPS

The dashboard listens on `127.0.0.1:8080` only. Point a DNS record (for example `netlog.example.com`) at the server, then add it to the web server you already run.

### Apache (common with Supermon)

**Check this first, or you can knock Supermon offline.** See which sites Apache already has:

```
sudo apache2ctl -S
```

If it shows **no** sites for `*:80` (Apache serves everything from its main config), then the first site you add takes over **all** traffic on port 80, Supermon included. Give your existing site its own named entry first, then add the logger.

**Supermon-NG** ships an Apache file at `/etc/apache2/sites-available/supermon-ng.conf` that's often never turned on (you'll see an "Index of /" page at your domain). Turn it on as the default site:

```
sudo cp /etc/apache2/sites-available/supermon-ng.conf /etc/apache2/sites-available/010-supermon-ng.conf
sudo sed -i '0,/<VirtualHost \*:80>/s//<VirtualHost *:80>\n    ServerName node.example.com/' /etc/apache2/sites-available/010-supermon-ng.conf
sudo a2enmod rewrite proxy proxy_http proxy_wstunnel headers
sudo a2ensite 010-supermon-ng
```

Optional: send the bare domain to Supermon and stop Apache listing your files:

```
sudo tee /etc/apache2/conf-available/supermon-home.conf >/dev/null <<'EOF2'
RedirectMatch 302 ^/$ /supermon-ng/
<Directory /var/www/html>
    Options -Indexes
</Directory>
EOF2
sudo a2enconf supermon-home
```

Now add the logger. The `020-` name keeps it after your default site:

```
sudo tee /etc/apache2/sites-available/020-netlog.conf >/dev/null <<'EOF2'
<VirtualHost *:80>
    ServerName netlog.example.com
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/
    RequestHeader set X-Forwarded-Proto "https"
</VirtualHost>
EOF2
sudo a2ensite 020-netlog
sudo apache2ctl configtest && sudo systemctl reload apache2
sudo apache2ctl -S
```

`-S` should list your main site as the **default server** and the logger as a **namevhost**.

**HTTPS:**
- **Behind Cloudflare** (orange cloud): Cloudflare handles HTTPS. Add a proxied A record for the subdomain. With **Flexible** mode, Cloudflare talks to Apache on port 80, which is what the site above listens on. Also set `CLIENT_IP_HEADER=CF-Connecting-IP` in `/etc/netlogger/netlogger.env` and restart, so login throttling sees each visitor instead of Cloudflare.
- **Without Cloudflare:** `sudo apt install -y certbot python3-certbot-apache && sudo certbot --apache -d netlog.example.com`

### nginx

```
server {
    server_name netlog.example.com;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then `sudo certbot --nginx -d netlog.example.com`.

### Caddy

```
netlog.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

## 3. First login

Open `https://netlog.example.com` and **create the admin account right away**. Until you do, anyone who finds the page could. Use a strong password: the login page is on the public internet.

Logins only work over HTTPS in this setup (`COOKIE_SECURE=1`). To try it before the subdomain is ready, use an SSH tunnel: `ssh -L 8080:127.0.0.1:8080 you@server`, then open `http://localhost:8080`.

The **Health** page then shows a live health check. **Audio from AllStar** turns to Done the first time the logger node hears a transmission.

## Day to day

```
journalctl -u netlogger -f          # watch what it hears
sudo systemctl restart netlogger    # after changing /etc/netlogger/netlogger.env
```

## Updating

```
cd /opt/netlogger
sudo git pull
sudo ./install.sh
```

## Uninstalling

```
sudo /opt/netlogger/uninstall.sh            # keeps net logs in /var/lib/netlogger
sudo /opt/netlogger/uninstall.sh --purge    # deletes them too
```

It removes the include lines, puts back anything it commented out, deletes `/etc/asterisk/netlogger/`, and asks before restarting Asterisk. Backups of each file are left next to it.
