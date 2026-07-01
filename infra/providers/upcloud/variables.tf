# Uniform provider interface (shared by every infra/providers/* module).
variable "region" {
  description = "UpCloud zone, e.g. fi-hel1, nl-ams1, de-fra1, se-sto1"
  type        = string
  default     = "fi-hel1"
}

variable "plan" {
  description = "UpCloud plan id, e.g. 1xCPU-2GB"
  type        = string
  default     = "1xCPU-2GB"
}

variable "image" {
  description = "OS template title (Ubuntu 22.04/24.04 LTS)"
  type        = string
  default     = "Ubuntu Server 24.04 LTS (Noble Numbat)"
}

variable "ssh_public_key" {
  description = "Operator SSH public key (authorized for root on first boot)"
  type        = string
}

variable "hostname" {
  description = "Server hostname"
  type        = string
  default     = "vpn-selfhost"
}
