"""vpnctl — operator CLI for a self-hosted, DPI-resistant VPN.

Layers (see ARCHITECTURE.md):
  provision  -> Terraform (infra/)      : create/converge the VPS
  deploy     -> Ansible (ansible/)      : harden OS + Marzban + AmneziaWG
  configure  -> reality/awg generators  : push protocol configs
  users/...  -> Marzban REST API        : day-2 operations
"""

__version__ = "0.1.0"
