variable "account_id" {
  description = "Cloudflare account containing the existing Zero Trust organization."
  type        = string
  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.account_id))
    error_message = "Use the 32-character Cloudflare account ID."
  }
}

variable "zone_id" {
  description = "Cloudflare DNS zone ID for the SSH hostname."
  type        = string
  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.zone_id))
    error_message = "Use the 32-character Cloudflare zone ID."
  }
}

variable "ssh_hostname" {
  description = "Dedicated SSH hostname in the selected Cloudflare zone."
  type        = string
  validation {
    condition     = length(var.ssh_hostname) <= 253 && can(regex("^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$", var.ssh_hostname))
    error_message = "Use a lowercase DNS hostname such as ssh.example.com."
  }
}

variable "access_email" {
  description = "The single personal email permitted to authenticate."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$", var.access_email))
    error_message = "Provide one email address, not a domain or wildcard."
  }
}

variable "ssh_user" {
  description = "Existing VPS account. The current repo installs Hermes under root."
  type        = string
  default     = "root"
  validation {
    condition     = can(regex("^[a-z_][a-z0-9_-]*$", var.ssh_user))
    error_message = "Use an existing Unix account name."
  }
}
