# vpn-selfhost — единая точка входа (FR-10.1)
# Тонкие обёртки над CLI vpnctl, чтобы частые сценарии были одной командой.
.DEFAULT_GOAL := help
SHELL := /bin/bash
VPNCTL := python -m vpnctl

.PHONY: help install provision deploy configure up status backup restore rotate-ip destroy bootstrap test lint fmt

help: ## Показать эту справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Установить CLI и dev-зависимости
	pip install -e ".[dev]"

provision: ## Создать/привести VPS в нужное состояние через Terraform (FR-1)
	$(VPNCTL) provision

deploy: ## Харденинг + Marzban + AWG через Ansible (FR-2,3,5)
	$(VPNCTL) deploy

configure: ## Сгенерировать и выкатить конфиги Reality/Xray + AWG (FR-4,5)
	$(VPNCTL) configure

up: ## provision + deploy + configure
	$(VPNCTL) up

status: ## Здоровье всех слоёв (FR-7.3, NFR-5)
	$(VPNCTL) status

backup: ## Бэкап БД + конфигов + секретов (FR-8.1)
	$(VPNCTL) backup

restore: ## Восстановить из архива бэкапа (FR-8.2) — использование: make restore ARCHIVE=path
	$(VPNCTL) restore $(ARCHIVE)

rotate-ip: ## Ротация на новый IP, миграция юзеров, переключение subscription (FR-8.3)
	$(VPNCTL) rotate-ip

destroy: ## Снести VPS и его ресурсы (FR-1.5)
	$(VPNCTL) destroy

bootstrap: ## Сквозной сценарий: от API-ключа до первого рабочего юзера (Ц-1, FR-10.2)
	$(VPNCTL) bootstrap

test: ## Прогнать юнит/интеграционные тесты
	pytest -q

lint: ## ruff + mypy
	ruff check cli tests
	mypy

fmt: ## Автоформатирование
	ruff check --fix cli tests
	ruff format cli tests
