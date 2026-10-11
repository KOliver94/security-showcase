# Security Showcase — "Vulnera"

A deliberately vulnerable, self-contained lab that demonstrates how a chain of **minor** oversights — a weak XSS filter, an f-string in a SQL query, a sloppy path check, a reused password, a typo in a shell history, an unpatched kernel — compound into **full root compromise and credential theft**.

Built for an internal ADR / security-awareness session. The point is not any single CVE-grade bug; it is the *chain*: every link is something that slips through code review all the time.

> ### ⚠️ Scope & ethics
> Everything here is intentionally insecure and runs **only inside local VMs** (`vagrant up`). It is for education on infrastructure you own. Do not deploy any of this, do not copy these patterns into real code, and do not point the attacker tooling at anything but your own lab VMs.

---

## The goal

> **Recover the login password of the system user `frank`.**

Reaching it requires walking the whole chain below — you cannot shortcut to `frank` because his hash lives only in root-readable `/etc/shadow`.

---

## Documentation

| Doc | What it is | Spoilers |
|-----|-----------|:--------:|
| [docs/hints.md](docs/hints.md) | A tiered hint ladder. Try to solve it yourself; open one hint at a time. | low |
| [docs/walkthrough.md](docs/walkthrough.md) | The complete step-by-step solution with commands, payloads, and *why* each step works. | full |
| [docs/vulnerabilities.md](docs/vulnerabilities.md) | Catalogue of every planted bug — `file:line`, root cause, CWE, and the fix. The ADR takeaways. | full |
| [docs/passwords.md](docs/passwords.md) | The answer key: every credential in the lab. | full |

New here and running the session? Hand the audience `docs/hints.md`, keep `docs/walkthrough.md` and `docs/vulnerabilities.md` for yourself.

---

## Architecture

```
          ┌───────────────────────── debian_vm (Debian 12) ──────────────────────────────┐
attacker  │                                                                              │
(kali_vm) │   :22  sshd                                                                  │
   │      │   :5001 news_feed      (systemd, user=bob)   Flask  — XSS + SQL injection    │
   ├──────┼─► :7002 file_browser   (systemd, user=bob)   Flask  — path traversal / LFI   │
   │      │        admin_simulator (systemd, user=bob)   Playwright bot                  │
   │      │          └─ logs into news_feed as `charlie` (admin) and refreshes every 60s │
   │      │                                                                              │
   └──────┴──────────────────────────────────────────────────────────────────────────────┘
```

| Service | Port | Runs as | Working dir | Role in the chain |
|---------|:----:|:-------:|-------------|-------------------|
| `sshd` | 22 | — | — | Foothold once `bob`'s password leaks |
| `news_feed` | 5001 | `bob` | `/var/www/news-feed` | Stored XSS → steal admin cookie → SQLi → dump/crack creds |
| `file_browser` | 7002 | `bob` | `/var/www/file-browser` | Reused admin password → path traversal → read `bob`'s history |
| `admin_simulator` | — | `bob` | `/var/www/news-feed/helpers` | Stands in for a human admin — drives a real browser that signs in and views the feed, so stored XSS fires |

The `admin_simulator` exists only because the lab has no live human: it simulates a real admin's normal behaviour — signing in as `charlie` in a real browser and revisiting the feed — which is what turns a *stored* XSS into practical cookie theft. It is not a service account or automation endpoint to attack; it is the victim you phish into running your payload.

---

## Setup

### 1. Bring up the VMs

```bash
vagrant up debian_vm
vagrant up kali_vm
```

`debian_vm` is the target; `kali_vm` is your attack box. The target is provisioned by [setup/provision.sh](setup/provision.sh): it creates the system users, drops the two web apps under `/var/www`, installs the three systemd services, and plants `bob`'s `.bash_history`.

Log in to the Kali box (GUI or SSH) with the Vagrant box default: **`vagrant` / `vagrant`** (same for `sudo`; root via `sudo su`).

### 2. (Re)initialising an app by hand

Each Flask app ships a `schema.sql` and an `init-db` command. The provision script runs these for you; to reset manually on the target:

```bash
cd /var/www/news-feed     && flask --app app init-db
cd /var/www/file-browser  && flask --app app init-db && flask --app app generate-files
```

---

## Teardown

When you're done, destroy both VMs to reclaim the disk and remove the deliberately vulnerable services:

```bash
vagrant destroy -f
```

That removes every machine defined here (`debian_vm` and `kali_vm`); add a name to target one (e.g. `vagrant destroy -f debian_vm`). To re-run the exercise clean later, `vagrant up` rebuilds from scratch. To also drop the downloaded base boxes:

```bash
vagrant box remove generic/debian12
vagrant box remove kalilinux/rolling
```

---

## Credits

Scenario, vulnerable apps, and provisioning by the repository author. Lab only.
