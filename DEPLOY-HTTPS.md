# HTTPS Runbook — os.fadifelfelos.com

**Why this exists:** browsers block `getUserMedia()` (the microphone) on non-secure origins. On
`http://45.63.19.249:8090` the mic does not work on a phone, no matter how good the voice code is.
HTTPS is the gate for every voice feature and for installing the dashboard as a phone app (PWA).

**Domain:** `fadifelfelos.com` (Cloudflare, registered 2026-07-17) · **Subdomain:** `os.fadifelfelos.com`
**VPS:** 45.63.19.249 · **App:** `server.py` on `0.0.0.0:8090` · **Deploy:** auto-pull cron, unchanged by this.

Caddy sits in front and reverse-proxies to the app. **Your push → auto-deploy flow does not change.**

---

## A. DNS — Cloudflare (~2 min)

1. Go to **dash.cloudflare.com** → click **fadifelfelos.com**
2. Left sidebar → **DNS** → **Records** → **Add record**
3. Fill in exactly:
   - **Type:** `A`
   - **Name:** `os`   ← just "os", not the full domain; Cloudflare appends the rest
   - **IPv4 address:** `45.63.19.249`
   - **Proxy status:** click the orange cloud so it turns **grey — "DNS only"**
   - **TTL:** Auto
4. **Save**

> ### ⚠️ The grey cloud is not optional
> Orange = Cloudflare proxies the traffic and terminates TLS itself. Caddy would never see Let's
> Encrypt's HTTP-01 challenge, the certificate would fail to issue, and you'd get a redirect loop that
> looks like a broken server. **Grey cloud = traffic goes straight to the VPS.** Get this wrong and
> everything below fails in a confusing way.

**Check it worked** (from Git Bash, after ~1-2 min):
```
nslookup os.fadifelfelos.com
```
Expect `45.63.19.249`. If you get a different IP, the cloud is still orange.

---

## B. Firewall

Vultr → **Products** → your instance → **Settings** → **Firewall**.
If **no firewall group is attached**, all ports are open — nothing to do, skip to C.
If one is attached, make sure **80** and **443** are allowed (80 is required for the cert challenge).

---

## C. Install Caddy (SSH, one time)

```
ssh root@45.63.19.249
```

Then paste this whole block:

```
apt update && apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy
```

---

## D. Configure (still on the VPS)

```
cat > /etc/caddy/Caddyfile <<'EOF'
os.fadifelfelos.com {
	reverse_proxy 127.0.0.1:8090
}
EOF

systemctl reload caddy
```

That's the entire config. Caddy requests the Let's Encrypt certificate automatically on first
request, renews it forever, and redirects http → https on its own.

---

## E. Verify

```
systemctl status caddy --no-pager | head -5
curl -I https://os.fadifelfelos.com
```

Expect `HTTP/2 200`. Then open **https://os.fadifelfelos.com** in a browser — padlock, no warning.

**The real test — on your phone:** open it, go to **Chat**, and tap the mic. If the phone asks for
microphone permission, HTTPS is doing its job and the voice work is unblocked for the first time.

---

## If it doesn't work

| Symptom | Cause | Fix |
|---|---|---|
| Redirect loop, or cert never issues | Cloudflare cloud is **orange** | Turn it grey (step A3) |
| `nslookup` returns the wrong IP | DNS not propagated, or orange cloud | Wait 2 min, re-check the cloud |
| Caddy: "challenge failed" | Port 80 blocked | Open 80 in the Vultr firewall |
| 502 Bad Gateway | `server.py` isn't running | `cd /root/knowledge/life-os && nohup python3 server.py > server.log 2>&1 &` |
| Padlock fine, mic still refuses | Browser cached the http:// permission | Close the tab, reopen on https://, allow the prompt |

---

## Notes / follow-ups

- **Port 8090 stays publicly open.** `http://45.63.19.249:8090` keeps working as a fallback while you
  confirm HTTPS is stable — useful, since a broken Caddy would otherwise lock you out entirely.
  **Once HTTPS is proven,** harden it: change `server_address = ('', PORT)` (server.py ~line 5354) to
  `('127.0.0.1', PORT)` so only Caddy can reach the app. Do NOT do this before HTTPS works.
- **Next after this:** PWA manifest + service worker → "Add to Home Screen" (audit backlog 3.1), then
  browser `speechSynthesis` TTS (3.2), then the tap-to-talk loop (3.3).
- **Voice still needs Phase 2 first.** Without the tool-calling layer, talking to Hermes gets you a
  chatbot that can't add a task. Tools before voice.
