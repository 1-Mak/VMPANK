# Uniform provider interface (matches infra/providers/upcloud).
variable "region" {
  description = "Scaleway zone, e.g. nl-ams-1, fr-par-1"
  type        = string
  default     = "nl-ams-1"
}

variable "plan" {
  description = "Scaleway instance type, e.g. DEV1-S, PLAY2-NANO"
  type        = string
  default     = "DEV1-S"
}

variable "image" {
  description = "OS image label (Ubuntu 22.04/24.04)"
  type        = string
  default     = "ubuntu_noble"
}

variable "ssh_public_key" {
  description = "Operator SSH public key"
  type        = string
}

variable "hostname" {
  description = "Server hostname"
  type        = string
  default     = "vpn-selfhost"
}
