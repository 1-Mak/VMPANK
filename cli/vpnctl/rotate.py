"""IP rotation orchestration (FR-8.3).

Sequence: provision a fresh VPS -> restore state -> migrate users -> switch the
subscription so clients auto-pull the new server -> tear down the old VPS.

Subscription continuity (so clients need no reinstall) requires a *stable*
subscription URL. That means the panel is fronted by a stable domain
(MARZBAN_PANEL_DOMAIN) and rotation repoints that domain's DNS to the new IP.
Without a domain, subscription links are IP-bound and clients must reimport.
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
    """Run the rotation using injected building blocks (keeps this testable)."""
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
