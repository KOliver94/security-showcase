# Vulnerability catalogue & fixes

The defensive counterpart to [walkthrough.md](walkthrough.md). Every planted weakness, where it lives, why it's wrong, and how you'd fix it in real code. This is the material for the ADR discussion — the walkthrough shows *that* it breaks; this shows *why* and *what good looks like*.

Severity is "in-context" (how much it contributes to the chain), not CVSS.

| # | Weakness | Location | CWE | In-context severity |
|---|----------|----------|-----|:-------------------:|
| 1 | Stored XSS via blacklist sanitiser + `\| safe` | news-feed | [CWE-79](https://cwe.mitre.org/data/definitions/79.html) | High |
| 2 | Session cookie not `HttpOnly` | news-feed | [CWE-1004](https://cwe.mitre.org/data/definitions/1004.html) | High |
| 3 | SQL injection via f-string | news-feed | [CWE-89](https://cwe.mitre.org/data/definitions/89.html) | Critical |
| 4 | Weak password hashing (unsalted MD5) | news-feed | [CWE-916](https://cwe.mitre.org/data/definitions/916.html) | High |
| 5 | Credential reuse across apps | news-feed + file-browser | [CWE-521](https://cwe.mitre.org/data/definitions/521.html) | High |
| 6 | Path traversal / LFI via broken check | file-browser | [CWE-22](https://cwe.mitre.org/data/definitions/22.html) | Critical |
| 7 | Secret in shell history | setup/bash_history | [CWE-532](https://cwe.mitre.org/data/definitions/532.html) | High |
| 8 | Unpatched kernel (CVE-2024-1086) | host | [CWE-416](https://cwe.mitre.org/data/definitions/416.html) | Critical |
| 9 | Missing security headers / weak session config | both apps | [CWE-693](https://cwe.mitre.org/data/definitions/693.html) | Low |

---

## 1 — Stored XSS: blacklist sanitiser + `| safe`

**Where:** [`news-feed/app.py:43`](../challenges/news-feed/app.py#L43) and [`news-feed/templates/index.html:63`](../challenges/news-feed/templates/index.html#L63).

```python
def sanitize_body(content):
    sanitized = content.replace("<script>", "")
    sanitized = sanitized.replace("</script>", "")
    return sanitized
```

**Root cause:** a deny-list that removes one exact substring, combined with `{{ post['body'] | safe }}` which turns *off* Jinja's auto-escaping. `onerror`, `onload`, `<svg>`, `<iframe srcdoc>`, mixed case, nesting (`<scr<script>ipt>`) — all bypass it.

**Fix:**
- Don't disable auto-escaping. Delete `| safe`; let Jinja escape by default.
- If you genuinely must allow *some* HTML, use a vetted allow-list sanitiser (e.g. `bleach` / `nh3`) with an explicit tag/attribute allow-list — never a hand-rolled deny-list.
- Add a `Content-Security-Policy` (e.g. `default-src 'self'; script-src 'self'`) as defence-in-depth so inline/exfiltrating scripts don't run.

---

## 2 — Session cookie readable by JavaScript

**Where:** [`news-feed/app.py:11`](../challenges/news-feed/app.py#L11).

```python
app.config['SESSION_COOKIE_HTTPONLY'] = False  # TODO: Remove this workaround
```

**Root cause:** `HttpOnly` disabled, so `document.cookie` exposes the session token to any XSS. (The `# TODO` is the tell — temporary workarounds that ship.)

**Fix:** remove the line (Flask defaults `HttpOnly` to `True`). Also set `SESSION_COOKIE_SECURE = True` (HTTPS-only) and `SESSION_COOKIE_SAMESITE = 'Lax'`. An attacker who finds XSS still shouldn't walk away with a reusable session.

---

## 3 — SQL injection via f-string

**Where:** [`news-feed/app.py:189`](../challenges/news-feed/app.py#L189) (`edit_news`) and [`:232`](../challenges/news-feed/app.py#L232) (`delete_news`).

```python
query = f"... WHERE p.id = {news_id}"
post = db.execute(query).fetchone()
```

**Root cause:** the route parameter is string-formatted into SQL. The same file uses parameterised queries correctly elsewhere (login, register, create) — this is a localized regression, which is exactly how injection sneaks past review.

**Fix:** always bind parameters:

```python
post = db.execute(
    "SELECT ... FROM posts p JOIN users u ON p.user_id = u.id WHERE p.id = ?",
    (news_id,),
).fetchone()
```

Also declare the route converter as `<int:news_id>` so non-numeric ids are rejected before they reach the DB, and keep `delete` behind POST + CSRF, not GET.

---

## 4 — Unsalted MD5 password hashing

**Where:** [`news-feed/app.py:38`](../challenges/news-feed/app.py#L38) + [`news-feed/schema.sql`](../challenges/news-feed/schema.sql).

```python
def md5_hash(password):
    return hashlib.md5(password.encode()).hexdigest()
```

**Root cause:** MD5 is fast and unsalted — billions of guesses/sec, and identical passwords share a hash. Half the dumped hashes crack from a plain lookup table.

**Fix:** use a memory-hard, salted KDF — `scrypt`, `bcrypt`, or `argon2`. The file-browser app already does the right thing (`werkzeug.security.generate_password_hash` → scrypt); the news feed should use the same `generate_password_hash` / `check_password_hash` pair.

---

## 5 — Credential reuse across applications

**Where:** `admin` = `*M0nK3y*` in **both** [news-feed](../challenges/news-feed/schema.sql) and [file-browser](../challenges/file-browser/schema.sql).

**Root cause:** the file-browser's strong scrypt hashing is completely bypassed because the same password exists, weakly hashed, on the news feed. **A shared password is only as safe as the weakest place it's stored.**

**Fix:** unique credentials per system; central identity (SSO/OIDC) instead of per-app password tables; detect reuse; enforce MFA on admin surfaces.

---

## 6 — Path traversal / LFI via broken `is_safe_path`

**Where:** [`file-browser/app.py:57`](../challenges/file-browser/app.py#L57), used by `/view` ([:141](../challenges/file-browser/app.py#L141)) and `/download` ([:168](../challenges/file-browser/app.py#L168)).

```python
def is_safe_path(path):
    return path.startswith(BASE_DIR) or os.path.abspath(path).startswith(BASE_DIR)
```

**Root cause:** the first clause validates the **raw, un-normalised** string, so `"/var/www/file-browser/files/../../../../etc/passwd"` passes (it *starts with* `BASE_DIR`) and then `open()` resolves the `../`. Validating before normalising is the classic traversal mistake.

**Fix:** normalise **first**, then contain, and compare path-wise (not by string prefix, which also allows sibling dirs like `/var/www/file-browser/files_secret`):

```python
def is_safe_path(path):
    base = os.path.realpath(BASE_DIR)
    target = os.path.realpath(path)
    return os.path.commonpath([base, target]) == base
```

Better still: never accept absolute paths from the user. Take a filename relative to `BASE_DIR`, reject separators and `..`, and resolve inside the base.

---

## 7 — Secret written to shell history

**Where:** [`setup/bash_history`](../setup/bash_history) (planted as `/home/bob/.bash_history`).

```
sduo -s
letmein
```

**Root cause:** a mistyped `sudo` followed by the password typed at what the user assumed was a prompt — now persisted in plaintext history. Readable by anything running as that user (and in this lab, via the file-browser LFI).

**Fix:** don't type secrets as commands; prefix sensitive commands with a space when `HISTCONTROL=ignorespace`; scrub history; and don't let a web service run as a human user whose dotfiles contain secrets. Treat dotfiles, `.env`, and history as secret material in reviews.

---

## 8 — Unpatched kernel (CVE-2024-1086)

**Where:** the Debian **12.4.0** base box ([Vagrantfile](../Vagrantfile), [provision.sh](../setup/provision.sh)).

**Root cause:** the shipped kernel has the netfilter `nf_tables` use-after-free (local privilege escalation). Any local user → root.

**Fix:** patch promptly (the fix is in later kernels); where unused, disable unprivileged user namespaces (`kernel.unprivileged_userns_clone=0`) and restrict `nf_tables`; keep base images current.

---

## 9 — Missing security headers / weak session hygiene

**Where:** both Flask apps.

**Root cause:** no CSP, no `X-Content-Type-Options`, no `Secure`/`SameSite` cookies, `send_file` with attacker-controlled paths, GET used for a destructive delete, and no CSRF protection on state-changing forms.

**Fix:** add security headers (via `flask-talisman` or an explicit `after_request`), set the cookie flags from #2, move all mutations to POST with CSRF tokens.
