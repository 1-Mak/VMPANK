# vpn-selfhost — single entry point (FR-10.1)
# Thin wrappers around the vpnctl CLI so common flows are one command.
.DEFAULT_GOAL := help
SHELL := /bin/bash
VPNCTL := python -m vpnctl

.PHONY: help install provision deploy configure up status backup restore rotate-ip destroy bootstrap test lint fmt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install the CLI and dev deps
	pip install -e ".[dev]"

provision: ## Create/converge the VPS via Terraform (FR-1)
	$(VPNCTL) provision

deploy: ## Run hardening + Marzban + AWG via Ansible (FR-2,3,5)
	$(VPNCTL) deploy

configure: ## Generate & push Reality/Xray + AWG configs (FR-4,5)
	$(VPNCTL) configure

up: ## provision + deploy + configure
	$(VPNCTL) up

status: ## Health of all layers (FR-7.3, NFR-5)
	$(VPNCTL) status

backup: ## Backup DB + configs + secrets (FR-8.1)
	$(VPNCTL) backup

restore: ## Restore from a backup archive (FR-8.2) — usage: make restore ARCHIVE=path
	$(VPNCTL) restore $(ARCHIVE)

rotate-ip: ## Rotate to a fresh IP, migrate users, switch subs (FR-8.3)
	$(VPNCTL) rotate-ip

destroy: ## Destroy the VPS and its resources (FR-1.5)
	$(VPNCTL) destroy

bootstrap: ## End-to-end: from API key to first working user (Ц-1, FR-10.2)
	$(VPNCTL) bootstrap

test: ## Run unit/integration tests
	pytest -q

lint: ## ruff + mypy
	ruff check cli tests
	mypy

fmt: ## Auto-format
	ruff check --fix cli tests
	ruff format cli tests
