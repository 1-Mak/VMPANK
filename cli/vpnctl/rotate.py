"""Оркестрация ротации IP (FR-8.3).

Последовательность: поднять свежий VPS -> восстановить состояние -> мигрировать
пользователей -> переключить subscription, чтобы клиенты сами подтянули новый
сервер -> погасить старый VPS.

Непрерывность subscription (чтобы клиентам не переустанавливать) требует
*стабильного* URL subscription. Значит, панель фронтится стабильным доменом
(MARZBAN_PANEL_DOMAIN), а ротация перенаправляет DNS этого домена на новый IP.
Без домена subscription-ссылки привязаны к IP, и клиентам придётся переимпортировать.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("vpnctl.rotate")


@dataclass
class RotationPlan:
    old_ip: str
    new_ip: str
    users_migrated: int
    subscription_switched: bool


def rotate(
    *,
    provision_new: Callable[[], str],
    export_current_users: Callable[[], list[Any]],
    deploy_and_configure: Callable[[str], None],
    import_users: Callable[[str, list[Any]], None],
    switch_subscription: Callable[[str], bool],
    destroy_old: Callable[[str], None],
    old_ip: str,
) -> RotationPlan:
    """Выполнить ротацию через внедрённые строительные блоки (для тестируемости)."""
    log.info("rotation: exporting users from %s", old_ip)
    users = export_current_users()

    log.info("rotation: provisioning new VPS")
    new_ip = provision_new()

    log.info("rotation: deploy + configure %s", new_ip)
    deploy_and_configure(new_ip)

    log.info("rotation: importing %d users", len(users))
    import_users(new_ip, users)

    switched = switch_subscription(new_ip)
    if not switched:
        log.warning(
            "subscription not auto-switched (no stable domain?) — clients must reimport"
        )

    log.info("rotation: destroying old VPS %s", old_ip)
    destroy_old(old_ip)

    return RotationPlan(
        old_ip=old_ip,
        new_ip=new_ip,
        users_migrated=len(users),
        subscription_switched=switched,
    )
