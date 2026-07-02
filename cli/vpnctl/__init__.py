"""vpnctl — CLI оператора для self-hosted VPN, устойчивого к DPI.

Слои (см. ARCHITECTURE.md):
  provision  -> Terraform (infra/)      : создать/привести VPS в нужное состояние
  deploy     -> Ansible (ansible/)      : харденинг ОС + Marzban + AmneziaWG
  configure  -> генераторы reality/awg   : выкатить конфиги протоколов
  users/...  -> Marzban REST API        : эксплуатация (day-2)
"""

__version__ = "0.1.0"
