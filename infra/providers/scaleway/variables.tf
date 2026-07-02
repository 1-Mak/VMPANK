# Единый интерфейс провайдера (совпадает с infra/providers/upcloud).
variable "region" {
  description = "Зона Scaleway, напр. nl-ams-1, fr-par-1"
  type        = string
  default     = "nl-ams-1"
}

variable "plan" {
  description = "Тип инстанса Scaleway, напр. DEV1-S, PLAY2-NANO"
  type        = string
  default     = "DEV1-S"
}

variable "image" {
  description = "Метка образа ОС (Ubuntu 22.04/24.04)"
  type        = string
  default     = "ubuntu_noble"
}

variable "ssh_public_key" {
  description = "Публичный SSH-ключ оператора"
  type        = string
}

variable "hostname" {
  description = "Имя хоста сервера"
  type        = string
  default     = "vpn-selfhost"
}
