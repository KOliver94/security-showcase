# Hints

A tiered ladder. Each stage starts gentle and ends just short of the full answer. **Open one hint at a time** — give yourself a chance to find the next step before reading the one after it. Full commands and payloads live in [walkthrough.md](walkthrough.md); the credentials are in [passwords.md](passwords.md).

The [`solution/`](../solution) directory ships ready-made helpers (e.g. a cookie collector for the XSS step). Use them if you like — or build your own.

Goal: **recover the password of the system user `frank`.**

---

## Stage 0 — Recon

<details><summary>Hint 0.1</summary>

You have a target VM and a Kali VM on the same network, but you aren't told the target's IP (it's from DHCP). Find your own subnet first (`ip addr`), ping-sweep it to locate the target, then run a full port + service scan against it. (Shortcut: both VMs are yours — the host's `vagrant ssh debian_vm -c "hostname -I"` hands you the IP.)
</details>

<details><summary>Hint 0.2</summary>

You should find SSH plus **two** web applications on non-standard ports. They look similar (same "Vulnera" branding) but do very different things. Catalogue both before touching either.
</details>

---

## Stage 1 — News Feed: become an admin

<details><summary>Hint 1.1</summary>

The news feed lets anyone register. Admins get Edit/Delete — and Post — buttons you don't. You need an admin session, but you don't have an admin password yet. What if someone else also reads these posts?
</details>

<details><summary>Hint 1.2</summary>

Suppose an admin reads the feed from time to time. If your post could run code in *their* browser when they view it, what could you take from them? (Be patient — you may have to wait for them to look.)
</details>

<details><summary>Hint 1.3</summary>

As a normal user there's no "Post News" button — but is the create route actually protected, or just hidden from the menu? Try requesting the posting path directly.
</details>

<details><summary>Hint 1.4</summary>

There is a body "sanitizer." Read exactly what it strips — it only removes one specific tag, as a literal substring. Plenty of ways to run JavaScript don't use that tag at all. And check the session cookie's flags: is it actually protected from JavaScript?
</details>

<details><summary>Hint 1.5</summary>

Stored XSS via e.g. an `onerror` handler → exfiltrate `document.cookie` to a listener you control. There is a ready-made collector in [`solution/xss-exploit/`](../solution/xss-exploit). Wait for an admin to load the page, then import the stolen `session` cookie into your own browser.
</details>

---

## Stage 2 — News Feed: dump and crack credentials

<details><summary>Hint 2.1</summary>

Now that you're an admin, the Edit and Delete routes are reachable. One of them takes an id straight from the URL. How is that id put into the SQL query, compared to how login/register build theirs?
</details>

<details><summary>Hint 2.2</summary>

The id is string-formatted directly into the query — injectable. Point an automated tool at the edit endpoint (don't forget the admin cookie) and pull the `users` table.
</details>

<details><summary>Hint 2.3</summary>

The dumped hashes are unsalted MD5. Most are trivially crackable. You don't need *every* password — you need the one that gets reused somewhere else.
</details>

---

## Stage 3 — File Browser: read what you shouldn't

<details><summary>Hint 3.1</summary>

The second app authenticates differently (strong hashing), so you can't crack its admin out of thin air. But did you just crack an `admin` password on the *first* app? Try it here.
</details>

<details><summary>Hint 3.2</summary>

The browser claims it restricts you to its own directory. Read the "is this path safe?" check very literally. What happens if your path *starts with* the allowed directory but then climbs back out?
</details>

<details><summary>Hint 3.3</summary>

Prefix the allowed base directory, then `../../../..` your way to anywhere the service user can read. The service runs as `bob`. What interesting, bob-owned file records everything bob has typed?
</details>

<details><summary>Hint 3.4</summary>

Read `bob`'s shell history. There's a fumble in it — a mistyped command followed by a line that was meant to be a password prompt. That line is bob's password. (Careful: the app also has a user named `bob` with a *different* password — that one is a decoy for SSH.)
</details>

---

## Stage 4 — Foothold

<details><summary>Hint 4.1</summary>

You now have a real system password for `bob`. SSH is open.
</details>

---

## Stage 5 — Become root

<details><summary>Hint 5.1</summary>

`bob` is not in `sudo` — only `frank` is, and frank's hash is in a file you can't read yet. You need a local privilege escalation that doesn't depend on sudo. Check the kernel version against known local-root bugs.
</details>

<details><summary>Hint 5.2</summary>

The box's kernel (Debian 12) is vulnerable to **CVE-2024-1086** (nf_tables use-after-free, local root). Notselwyn publishes a prebuilt exploit binary on the project's Releases page — grab that and run it as `bob` (there's no compiler on the target).
</details>

---

## Stage 6 — The goal

<details><summary>Hint 6.1</summary>

As root you can finally read `/etc/shadow`. `frank`'s entry is a `$6$` (sha512crypt) hash.
</details>

<details><summary>Hint 6.2</summary>

`unshadow` + John the Ripper (or hashcat mode 1800). frank's password is a classic — it's in `rockyou.txt`. Crack it and you've met the goal.
</details>
