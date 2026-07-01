# Implementation status

Honest map of what is built and verified vs. what needs a live VPS + your
provider credentials to exercise. Verified here = unit tests (40 passing) +
local CLI runs on Windows/Python 3.13; ruff and mypy clean.

## Implemented and verified locally

| Area | ТЗ | State |
|---|---|---|
| Reality key/shortId + `xray_config.json` generation, О-2/О-4 invariants | FR-4 | ✅ tested |
| SNI validator (TLS1.3 + HTTP/2 + overused denylist) | FR-4.3 | ✅ tested (probe mocked) |
| AmneziaWG keygen + obfuscation params + server/client render + NAT | FR-5 | ✅ tested |
| Marzban REST client (login, user CRUD, re-auth on 401) | FR-6.5 | ✅ tested (httpx MockTransport) |
| User mgmt: add/list/enable/disable/delete/reset + export/import | FR-6 | ✅ tested |
| Monitoring parsing: check-host results, freeze result, health report | FR-7 | ✅ tested |
| Backup/restore with encrypted secrets | FR-8.1/8.2 | ✅ tested (roundtrip + no-plaintext assert) |
| Rotation orchestration (ordering) | FR-8.3 | ✅ tested (injected building blocks) |
| Terraform provider modules (UpCloud, Scaleway), uniform interface | FR-1 | ✅ written; `terraform validate` needs terraform installed |
| Ansible hardening + Docker + Marzban + AWG roles | FR-2/3/5 | ✅ written; needs a target host to run |
| CLI wiring + Makefile + docs | FR-10, NFR-10 | ✅ |

## Requires a live VPS (not run here)

- End-to-end `bootstrap` against a real provider (Ц-1, §8 E2E).
- Actual Reality/AWG traffic and the §8 checks (`curl http://IP:8000` refused,
  `ufw status`, client import).
- `terraform validate`/`plan` and `ansible-lint`/playbook runs (Terraform &
  Ansible aren't installed on this machine — Д-2 assumes they're on the
  operator's).
- Live `check-host.net` availability + real freeze download through a tunnel
  (the parsing/logic is tested; the network path is not).

## Deliberately deferred (ТЗ MoSCoW COULD / WON'T)

- Prometheus/node_exporter dashboard (COULD).
- VLESS-over-WS + Cloudflare CDN masquerade mode (COULD) — hooks noted in RUNBOOK.
- Web UI, billing, custom clients, multi-region balancing (WON'T, §12).

## Suggested next steps to reach Definition of Done (§15)

1. Install Terraform + Ansible; `terraform -chdir=infra/providers/<p> validate`
   and `ansible-lint ansible/`.
2. Run `make bootstrap` against a throwaway VPS; walk the §8 acceptance checks.
3. CI is wired in `.github/workflows/ci.yml` (T-6/T-7): the `python` and
   `xray-config` jobs gate; `terraform` and `ansible` jobs are advisory
   (`continue-on-error`) until their first real run confirms formatting/lint —
   promote them to gating once green.
