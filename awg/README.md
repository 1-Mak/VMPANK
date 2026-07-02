# awg/ — AmneziaWG (резервный протокол, FR-5)

Серверный и клиентские конфиги **генерируются**, а не пишутся руками — чтобы
параметры обфускации (Jc/Jmin/Jmax/S1/S2/H1..H4) всегда совпадали на обоих концах:

- Серверный конфиг: `cli/vpnctl/configure.py::generate_awg_config` → `.build/awg0.conf`,
  выкатывается ролью `ansible/roles/awg`.
- Клиентский конфиг/QR: `cli/vpnctl/awg.py::add_peer` + `ServerConfig.render_client`
  (совместимо с Amnezia/AWG, FR-5.4).

Режимы развёртывания (FR-5.3), задаются через `AWG_DEPLOY_MODE`:

- `same-host` — AWG на том же VPS с Reality (один IP). Просто; бан этого IP
  роняет оба протокола.
- `separate-host` — AWG на втором VPS/IP (`AWG_SEPARATE_HOST`). Рекомендуется:
  бан IP с Reality оставляет резерв доступным (ARCHITECTURE.md).
