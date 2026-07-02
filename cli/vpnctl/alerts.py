"""Telegram-алерты оператору (FR-7.4, SHOULD).

Никогда не логирует токен бота. Отсутствующий токен мягко отключает алертинг,
чтобы остальной мониторинг продолжал работать.
"""

from __future__ import annotations

import logging

import httpx

log = logging.getLogger("vpnctl.alerts")


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, timeout: float = 10.0):
        self._token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._chat_id)

    def send(self, text: str) -> bool:
        """Отправить сообщение. True при успехе, False если отключено/сбой."""
        if not self.enabled:
            log.warning("Telegram not configured; alert suppressed: %s", text)
            return False
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        try:
            resp = httpx.post(
                url,
                json={"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            log.error("Telegram send failed: %s", exc)  # exc никогда не содержит токен
            return False
