# Единый интерфейс провайдера (общий для всех модулей infra/providers/*).
variable "region" {
  description = "Зона UpCloud, напр. fi-hel1, nl-ams1, de-fra1, se-sto1"
  type        = string
  default     = "fi-hel1"
}

variable "plan" {
  description = "Id тарифа UpCloud, напр. 1xCPU-2GB"
  type        = string
  default     = "1xCPU-2GB"
}

variable "image" {
  description = "Название шаблона ОС (Ubuntu 22.04/24.04 LTS)"
  type        = string
  default     = "Ubuntu Server 24.04 LTS (Noble Numbat)"
}

variable "ssh_public_key" {
  description = "Публичный SSH-ключ оператора (авторизуется для root при первой загрузке)"
  type        = string
}

variable "hostname" {
  description = "Имя хоста сервера"
  type        = string
  default     = "vpn-selfhost"
}
