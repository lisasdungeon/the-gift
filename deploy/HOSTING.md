# Hosting The Gift on 192.168.1.202

The Gift is a **static library** — no build step, no packages, no database.
One stdlib-only Python process serves everything: a landing page with real
library counts, browsable listings, and the files themselves.

The server never exposes `.git`/`.claude`/`.freebuff`, the private `model/`
folder, or anything outside the library root.

## 1. Layout

```bash
sudo mkdir -p /opt/rnk
# copy or clone this folder to /opt/rnk/the-gift
# it is ~8.3 GB with .git — rsync -a (hardlink-aware) or git clone both work
```

## 2. systemd service

`/etc/systemd/system/the-gift.service`:

```ini
[Unit]
Description=The Gift (open library)
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/rnk/the-gift
Environment=GIFT_HOST=0.0.0.0
Environment=GIFT_PORT=8770
ExecStart=/usr/bin/python3 server.py
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ReadOnlyPaths=/opt/rnk/the-gift

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now the-gift
curl -s http://127.0.0.1:8770/ | grep -o '<h1>[^<]*</h1>'   # → <h1>The Gift</h1>
```

## 3. Verify from another machine

```bash
curl -s http://192.168.1.202:8770/healthz 2>/dev/null || true
curl -sI http://192.168.1.202:8770/Bibles/formats/text/AKJV.txt | head -3
# browser: http://192.168.1.202:8770/ — landing page, browse into any folder
```

If the box has a firewall, open 8770 (e.g. `sudo ufw allow 8770`).

## 4. Redeploy

```bash
./deploy/deploy.sh    # restart the service, then smoke-check the landing page
```

## 5. Public name (later)

The hub links `https://gift.rnkstudios.uk`. When you're ready:

1. DNS: `gift.rnkstudios.uk` → the box's public address.
2. TLS + reverse proxy in front (Caddy, like the Curator's deployment):

```
gift.rnkstudios.uk {
    reverse_proxy 127.0.0.1:8770
}
```

Until then the door is the LAN address. Bulk/programmatic access (the 229
per-book files, the 1.2 GB python tree) should use git or rsync — the HTTP
server reads whole files into memory and has no range/resume support, by
design.
