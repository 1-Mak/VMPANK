# infra/ — Terraform provisioning (FR-1)

One self-contained module per provider under `providers/<name>`, each exposing
the **same interface** so `vpnctl` can drive any of them (NFR-6):

| variable          | meaning                                   |
|-------------------|-------------------------------------------|
| `region`          | provider zone (Finland/NL/DE/SE preferred)|
| `plan`            | instance size (default ~1 vCPU / 2 GB)    |
| `image`           | Ubuntu 22.04/24.04 LTS                     |
| `ssh_public_key`  | operator key authorized for root          |
| `hostname`        | server hostname                           |

Every module outputs `ipv4`, which `vpnctl provision` reads and stores.

## Why these providers

The ТЗ (§3.3, FR-1.2) warns that the big "засвеченные" clouds (Hetzner, DO,
OVH, Vultr, AWS, GCP) have IP ranges that land on RU block-lists fast. The two
bundled adapters — **UpCloud** (Finland) and **Scaleway** (NL/FR) — are EU hosts
with cleaner reputation *and* first-class Terraform providers. IP reputation
still changes constantly (Д-3), so `vpnctl monitor ru` + fast rotation
(`vpnctl rotate-ip`) are the real mitigation.

## Adding a provider

Create `providers/<name>/` with `versions.tf`, `variables.tf` (the interface
above), `main.tf`, `outputs.tf` (`ipv4`), then add `<name>` to
`SUPPORTED_PROVIDERS` in `cli/vpnctl/provision.py` and map its credential env
vars in `_pass_provider_credentials`.

Credentials are never written to disk — `vpnctl` exports them as the provider's
env vars for the Terraform run only (FR-9).
