# Route: Self-host

Takes a **fresh Linux VM** (Ubuntu/Debian, root or sudo SSH) to a **running, HTTPS,
production n8n** via Docker Compose behind **Caddy** (automatic Let's Encrypt TLS).

This is for **self-hosted n8n on Docker** — not n8n Cloud, and not for building workflows.
You drive it end to end over SSH: preflight → install Docker → lay down the project →
generate secrets → launch → verify TLS → hand off.

Templates live in this skill's `assets/`. Per-mode and security depth are in the deep files
named below.

## Rule 0 — choose the mode (ask the user)

Do not guess. Ask, then commit.

| | **Single / regular** | **Queue** |
|---|---|---|
| Processes | one n8n | main + N workers |
| Extra services | none (SQLite) | Redis (queue) + Postgres (DB) |
| Executes workflows | in the main process | on workers, in parallel |
| Good for | 1 user, light/moderate load, simplest ops | high volume, heavy/long executions, horizontal scale |
| Compose | `assets/docker-compose.single.yml` | `assets/docker-compose.queue.yml` |
| Depth | [deep/self-host/SINGLE_MODE.md](deep/self-host/SINGLE_MODE.md) | [deep/self-host/QUEUE_MODE.md](deep/self-host/QUEUE_MODE.md) |

If unsure, start **single** — the simplest correct thing, and it covers most needs. Moving to
queue later means swapping the compose file and migrating SQLite → Postgres, so if the user
already expects real volume, start **queue**.

## Rule 1 — secret hygiene (non-negotiable)

A misstep here leaks client credentials.

1. **Generate every secret fresh, on the target box.** Never copy an encryption key, DB
   password or `.env` from another n8n instance into this one.
2. **Secrets live only in `.env`** (mode 600), referenced by the compose as `${VAR}`. Never
   inline a secret into `docker-compose.yml`, the Caddyfile, or anything you commit.
3. **The `N8N_ENCRYPTION_KEY` is sacred.** It encrypts every stored credential. If it is lost
   or changes, all saved credentials become undecryptable. Set it explicitly and tell the
   user to back it up **off the box**.
4. **Never expose internal services.** Only Caddy (80/443) is public. n8n (5678), Postgres
   (5432) and Redis (6379) stay on the private Docker network — the templates already omit
   their host port mappings. Do not add them.
5. **`.env` and Caddy's `caddy_data` volume** (issued certs plus the ACME account key) are
   not artifacts to share. If you are inside a git repo, confirm `.env` is git-ignored before
   any commit.

## Inputs to collect up front

- **SSH target** — `user@host`, and how you authenticate. Root or a sudo user.
- **Domain** — the full hostname, e.g. `n8n.example.com` (→ `SUBDOMAIN=n8n`,
  `DOMAIN_NAME=example.com`). The user must control its DNS.
- **TLS email** — for Let's Encrypt (`SSL_EMAIL`).
- **Timezone** — IANA name for Schedule/Cron nodes (e.g. `Europe/Warsaw`), else `Etc/UTC`.
- **Mode** — single or queue. Queue → confirm the box has enough RAM (rough floor ~4 GB;
  each worker wants ~1–2 GB).
- **Optional modules** — some features (currently **Agents**) are backend modules that stay
  off unless listed in `N8N_ENABLED_MODULES`. Ask only if the user raises one; if they do,
  read the modules section of [deep/self-host/QUEUE_MODE.md](deep/self-host/QUEUE_MODE.md)
  first, because in queue mode it must reach the workers too.

## The deploy flow

### 1. Preflight — the cheapest failure is the one you catch here

- SSH in; confirm the OS is Debian/Ubuntu-like (`. /etc/os-release`).
- **DNS must already point at the box.** Compare the public IP (`curl -s ifconfig.me`) with
  `dig +short <fqdn>`. If they do not match, **stop** — Caddy's ACME challenge will fail.
  Have the user create the A record, wait for propagation, then continue.
- **Ports 80 and 443 must be reachable from the internet.** Check the host firewall **and**
  any cloud security group or network firewall (Hetzner Cloud, AWS SG, …) — these are
  outside the box and a common silent blocker.

### 2. Install Docker if absent

Check `docker --version` and `docker compose version`. If missing, install Docker Engine plus
the Compose plugin. Re-check `docker compose version` before proceeding.

### 3. Lay down the project

- Pick `DATA_FOLDER` — an **absolute path**, e.g. `/opt/n8n`. The `DATA_FOLDER` value in
  `.env` **must equal this exact directory** (the compose mounts
  `${DATA_FOLDER}/caddy_config/Caddyfile`, and `init-data.sh` is mounted via a relative
  `./` path), so always run `docker compose` from here. Create it, plus `caddy_config/` and
  `local_files/` inside.
- **Get the template files onto the box.** They live in this skill's `assets/` on *your*
  machine, not on the server. Either `scp` them up, or write each file over SSH:
  `ssh <target> 'cat > <DATA_FOLDER>/docker-compose.yml' < assets/docker-compose.single.yml`.
  Land them with these exact names:
  - the chosen compose → `<DATA_FOLDER>/docker-compose.yml` (rename to exactly this)
  - `Caddyfile` → `<DATA_FOLDER>/caddy_config/Caddyfile`
  - **queue only:** `init-data.sh` → `<DATA_FOLDER>/init-data.sh`, then `chmod +x`
  - the matching `.env.*.example` → `<DATA_FOLDER>/.env`

### 4. Fill `.env` and generate secrets

- Set `DATA_FOLDER`, `DOMAIN_NAME`, `SUBDOMAIN`, `SSL_EMAIL`, `GENERIC_TIMEZONE`.
- Generate each secret **on the box** with `openssl` and write it into `.env`, replacing the
  matching `REPLACE_WITH_…` placeholder: `N8N_ENCRYPTION_KEY`; queue also
  `POSTGRES_PASSWORD` and `POSTGRES_NON_ROOT_PASSWORD`. Commands:
  [deep/self-host/SECURITY.md](deep/self-host/SECURITY.md).
- **Before launching, confirm none are left unset:** `grep REPLACE_WITH_ .env` must return
  nothing — a leftover placeholder becomes the literal password and Postgres/n8n fail to
  connect.
- `chmod 600 .env`. Record the encryption key so the user can back it up off-box.

### 5. Firewall

`ufw`: allow OpenSSH, 80 and 443, then enable. Do **not** open 5678, 5432 or 6379.

### 6. Launch

`cd <DATA_FOLDER> && docker compose up -d`. Queue mode brings up Redis + Postgres + main +
workers. To add capacity: `docker compose up -d --scale n8n-worker=N`.

### 7. Verify — do not declare success without this

- `docker compose ps` — every service `Up`/healthy (queue: postgres and redis `healthy`
  first).
- **n8n itself up, internally:**
  `docker compose exec n8n wget -qO- http://localhost:5678/healthz` → `{"status":"ok"}`.
  This separates "n8n is running" from "TLS is not ready yet".
- **Cert issued:** `docker compose logs caddy | grep -i 'certificate obtained'`. First-boot
  ACME can take a minute or two; until it finishes a public `https://` request fails TLS —
  that means the cert is pending, **not** that n8n is down.
- **Public reachability, with retry:**
  `curl -fsS --retry 5 --retry-delay 10 https://<fqdn>/healthz` → `{"status":"ok"}`.
  (`/healthz/readiness` additionally confirms the DB is connected and migrated — use it when
  debugging a boot loop.)
- **Queue mode — main and workers must agree.** Diff their environments:
  `diff <(docker compose exec -T n8n env | sort) <(docker compose exec -T --index 1 n8n-worker env | sort)`.
  Only the public-URL/proxy vars should differ. Anything else means a behavioural setting
  reached the main but not the workers — and workers execute the workflows, so it fails at
  runtime in one node rather than at boot.
- Open `https://<fqdn>` → the **owner setup** screen. **Whoever completes that signup form
  first claims the instance** — an exposed un-owned instance is a race, so create the owner
  account immediately, before sharing the URL. Enable 2FA.

### 8. Hand off

Give the user: the URL, where the project lives, the encryption key to store safely, and the
Day-2 basics from [deep/self-host/DAY2.md](deep/self-host/DAY2.md).

## What NOT to do

- **Don't skip the DNS/ports preflight.** A wrong A record or a closed cloud firewall is the
  #1 reason Caddy cannot get a cert and n8n looks "broken".
- **Don't publish 5678/5432/6379** to the host.
- **Don't reuse another instance's encryption key or `.env`.**
- **Don't run queue mode on SQLite.** Queue requires Postgres.
- **Don't put secrets in `docker-compose.yml` or the Caddyfile.** `.env` only.
- **Don't add a behavioural env var to the main only (queue mode).** Modules, DB, queue,
  binary-data and encryption settings belong in the shared `x-n8n-env` anchor so workers get
  them too; only public-URL/proxy vars are main-only.
- **Don't use `:latest` blindly.** Pin `N8N_IMAGE_TAG` and update deliberately.

## Deeper references

| Read when | File |
|---|---|
| Single-mode specifics, SQLite vs Postgres, when to graduate | [deep/self-host/SINGLE_MODE.md](deep/self-host/SINGLE_MODE.md) |
| Queue architecture, workers, scaling, the env-parity rule, modules | [deep/self-host/QUEUE_MODE.md](deep/self-host/QUEUE_MODE.md) |
| Generating secrets, the full hardening checklist | [deep/self-host/SECURITY.md](deep/self-host/SECURITY.md) |
| Managed OAuth so users never see a client secret | [deep/self-host/CREDENTIAL_OVERWRITES.md](deep/self-host/CREDENTIAL_OVERWRITES.md) |
| Changing a setting, updating, backing up, restoring | [deep/self-host/DAY2.md](deep/self-host/DAY2.md) |

Authoritative upstream reference: <https://docs.n8n.io/deploy/host-n8n>. The env-var index is
at
<https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables>.
When this route and the live docs disagree, trust the docs and tell the user.
