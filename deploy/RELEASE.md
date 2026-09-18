# Release checklist — deploying to the RNK box

One page, top to bottom. Every step has an expected result; stop at the
first red one. Total time: ~10 minutes plus the monitoring wait.

## 0. What's shipping

The most recent commits on `main` — commit any local work first; `git
status` must be empty before you start. As of this writing that's:

- **Release sweep** (`099e151d`) — concurrency cap now counts requests in
  flight, not connections, so idle browser keep-alive connections can no
  longer 503 everyone; favicon on every page; `/LICENSE` displays instead
  of downloading; stale license references fixed.
- **Chunked streaming** — files stream to the client in 256 KB chunks
  instead of being read whole into memory; RSS is flat regardless of file
  size, so the `MemoryMax=512M` ceiling is safe under any burst.

## 1. Pre-flight (from your checkout)

```bash
git status --short                 # → empty (nothing uncommitted)
git log --oneline -3               # → streaming commit on top of 099e151d
python3 -m unittest test_server    # → Ran 19 tests ... OK
git push origin main               # → pushed
```

Then check GitHub Actions (the `test` workflow) is green on the push —
that's the same suite running in CI.

## 2. Deploy on the box (192.168.1.202)

```bash
ssh <you>@192.168.1.202
cd /opt/rnk/the-gift
git pull --ff-only origin main     # → Fast-forward, no conflicts
git log --oneline -3               # → same SHAs as your checkout
./deploy/deploy.sh                 # → "the-gift: landing page OK"
systemctl is-active the-gift       # → active
```

`deploy.sh` restarts the service and smoke-checks the landing page. If it
prints anything else, go to the rollback (§6) before debugging live.

## 3. Verify on the box (LAN door)

```bash
curl -s http://127.0.0.1:8770/healthz
# → {"ok": true}

curl -s http://127.0.0.1:8770/ | grep -oE '140 translations|228 folders|15,672|20 SWORD modules'
# → all four lines (the counts are computed from disk, so this also
#   proves the library tree is intact after the pull; "15,672" alone
#   because the page wraps that number onto its own line)

curl -s -o /dev/null -w '%{http_code} %{size_download}\n' \
  http://127.0.0.1:8770/Bibles/formats/text/BurJudson.txt
# → 200 11965562  (the 12 MB file through the new chunked path)

curl -sI http://127.0.0.1:8770/LICENSE | grep -i content-type
# → text/plain; charset=utf-8  (not octet-stream)

curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8770/favicon.ico
# → 200

systemctl show the-gift -p MemoryCurrent
# → low tens of MB — nowhere near the 512M ceiling
```

## 4. Verify from outside (public door, through the tunnel)

From any machine **not** on the LAN:

```bash
curl -s https://gift.rnkstudios.uk/healthz
# → {"ok": true}

curl -sI https://gift.rnkstudios.uk/ | head -3
# → HTTP/2 200, server: cloudflare

curl -s -o /dev/null -w '%{http_code} %{size_download}\n' \
  https://gift.rnkstudios.uk/Bibles/formats/text/BurJudson.txt
# → 200 11965562

curl -sI https://gift.rnkstudios.uk/LICENSE | grep -i content-type
# → text/plain; charset=utf-8
```

Browser pass: open <https://gift.rnkstudios.uk/>, check the favicon in
the tab, walk one door (Bibles → text → any file), confirm it renders as
text in-browser rather than downloading.

## 5. Monitoring stays quiet

The atlas cron hits the public door every 5 minutes. Within ~10 minutes
of the restart:

```bash
# on atlas:
tail -3 /home/rnk/gift-health.log   # → "ok" lines, no DOWN after the restart
tail -3 /home/rnk/deadman.log       # → nothing new (no STALE)
```

One `DOWN`→`recovered` pair around the restart window is expected (the
service is down for the seconds of the restart); anything still down 10
minutes later is a real problem.

## 6. Rollback

The library content is identical in both versions — only `server.py`
behavior changed — so rolling back the code is safe and fast:

```bash
cd /opt/rnk/the-gift
sudo git reset --hard b9316cce     # the pre-sweep commit
./deploy/deploy.sh
curl -s http://127.0.0.1:8770/healthz   # → {"ok": true}
```

This leaves the box behind origin; when you're ready to try again,
`git pull --ff-only origin main` re-advances it (it will fast-forward,
not conflict).

## Sign-off

- [ ] CI green on the pushed commit
- [ ] LAN door: healthz, counts, 12 MB file, LICENSE content-type, favicon
- [ ] Public door: healthz, 200 through the edge, big file, LICENSE
- [ ] Browser: favicon renders, .txt displays in-browser
- [ ] gift-health.log shows `ok`, deadman quiet
