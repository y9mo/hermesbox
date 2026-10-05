terraform {
  required_version = ">= 1.5"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.24.0"
    }
  }
}

# Authentication comes from CLOUDFLARE_API_TOKEN, never a committed variable.
provider "cloudflare" {}

locals {
  ssh_principal = split("@", lower(var.access_email))[0]
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "hermesbox" {
  account_id = var.account_id
  name       = "hermesbox"
  config_src = "cloudflare"
}

resource "cloudflare_zero_trust_access_identity_provider" "email" {
  account_id = var.account_id
  name       = "Hermesbox email login"
  type       = "onetimepin"
  config     = {}
}

resource "cloudflare_zero_trust_access_policy" "owner" {
  account_id       = var.account_id
  name             = "Hermesbox personal owner"
  decision         = "allow"
  session_duration = "1h"
  include = [{
    email = { email = lower(var.access_email) }
  }]
  # Independent MFA must first be enabled in the Zero Trust organization.
  mfa_config = {
    mfa_disabled           = false
    allowed_authenticators = ["biometrics", "security_key"]
    session_duration       = "1h"
  }
}

resource "cloudflare_zero_trust_access_application" "ssh" {
  account_id                = var.account_id
  name                      = "Hermesbox SSH"
  type                      = "self_hosted"
  domain                    = var.ssh_hostname
  session_duration          = "1h"
  allowed_idps              = [cloudflare_zero_trust_access_identity_provider.email.id]
  auto_redirect_to_identity = true
  policies = [{
    id         = cloudflare_zero_trust_access_policy.owner.id
    precedence = 1
  }]
}

# This is Cloudflare's documented legacy certificate flow. It avoids WARP on
# the Mac and automatically issues short-lived certificates after Access login.
resource "cloudflare_zero_trust_access_short_lived_certificate" "ssh" {
  account_id = var.account_id
  app_id     = cloudflare_zero_trust_access_application.ssh.id
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "hermesbox" {
  account_id = var.account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.hermesbox.id
  config = {
    ingress = [
      { hostname = var.ssh_hostname, service = "ssh://localhost:22" },
      { service = "http_status:404" }
    ]
  }
  depends_on = [cloudflare_zero_trust_access_application.ssh]
}

resource "cloudflare_dns_record" "ssh" {
  zone_id = var.zone_id
  name    = var.ssh_hostname
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.hermesbox.id}.cfargotunnel.com"
  proxied = true
  ttl     = 1
  depends_on = [
    cloudflare_zero_trust_access_short_lived_certificate.ssh,
    cloudflare_zero_trust_tunnel_cloudflared_config.hermesbox
  ]
}

data "cloudflare_zero_trust_tunnel_cloudflared_token" "hermesbox" {
  account_id = var.account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.hermesbox.id
}

output "ansible_vars" {
  description = "Pass directly to the Ansible playbook using a protected JSON file."
  sensitive   = true
  value = {
    cloudflare_tunnel_token  = data.cloudflare_zero_trust_tunnel_cloudflared_token.hermesbox.token
    cloudflare_ssh_ca        = cloudflare_zero_trust_access_short_lived_certificate.ssh.public_key
    cloudflare_ssh_user      = var.ssh_user
    cloudflare_ssh_principal = local.ssh_principal
  }
}

output "ssh_hostname" {
  value = var.ssh_hostname
}
