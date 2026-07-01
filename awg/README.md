# awg/ — AmneziaWG (backup protocol, FR-5)

Server and client configs are **generated**, not hand-written, so the
obfuscation params (Jc/Jmin/Jmax/S1/S2/H1..H4) always match on both ends:

- Server config: `cli/vpnctl/configure.py::generate_awg_config` → `.build/awg0.conf`,
  deployed by `ansible/roles/awg`.
- Client config/QR: `cli/vpnctl/awg.py::add_peer` + `ServerConfig.render_client`
  (Amnezia/AWG compatible, FR-5.4).

Deployment modes (FR-5.3), set via `AWG_DEPLOY_MODE`:

- `same-host` — AWG runs on the Reality VPS (one IP). Simple; a ban of that IP
  takes both protocols down.
- `separate-host` — AWG on a second VPS/IP (`AWG_SEPARATE_HOST`). Recommended:
  a ban of the Reality IP leaves the backup reachable (ARCHITECTURE.md).
