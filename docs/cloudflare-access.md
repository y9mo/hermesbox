# Personal SSH access alongside work Tailscale

The intended setup is:

- Mac: Herdr uses OpenSSH through Cloudflare Access, with automatically issued
  short-lived certificates. Work Tailscale stays active; WARP is not installed.
- iPhone: Termius uses the personal Tailscale network and Tailscale SSH. It does
  not need a manually managed SSH key or a Cloudflare client.

Cloudflare Access login authorizes the tunnel connection. SSH authentication is
a separate step: this configuration makes OpenSSH trust a Cloudflare certificate
authority and maps the owner's certificate principal to the selected Unix user.
The Mac generates its own temporary credentials with `cloudflared`; public keys
do not need to be copied into the VPS's `authorized_keys` for this access path.

## Status and limitation

The chosen SSH hostname is `hermesbox.oct1v.xyz`. Deployment is in progress;
Cloudflare resources may already exist after a partial Terraform apply. Rerun
`terraform apply` from the same state to complete provisioning. VPS deployment
and end-to-end access verification are still pending.

Cloudflare labels the no-WARP certificate flow **legacy** and recommends Access
for Infrastructure for new deployments. Access for Infrastructure uses the
Cloudflare One Client (WARP), which would introduce another VPN on the Mac. The
legacy flow is an explicit compatibility tradeoff for native Herdr SSH while
remaining on work Tailscale; there is no promise of indefinite support.

SSH through the published hostname runs over WebSockets. Cloudflare recommends
Client-to-Tunnel for long-lived connections. Herdr's server sessions persist
across client disconnects, but reconnection and certificate renewal must be
tested with the installed Herdr version.

See [short-lived certificates](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/non-http/short-lived-certificates-legacy/),
[connection protocols](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/protocols/),
and [Herdr's connection recovery](https://herdr.dev/docs/connecting-machines/).

## Ownership and credentials

`terraform/cloudflare/` is an independent Terraform root and state. It manages
only the tunnel, SSH DNS record, exact-email Access policy, email PIN identity
provider, Access application and certificate authority. Applying or destroying
this root does not manage the Hetzner VPS.

The Ansible playbook installs the connector from Cloudflare's apt repository,
runs it as a systemd service, and configures the certificate authority and
principal mapping. The token is stored in a root-only file and suppressed from
Ansible output. The deployment helper transfers outputs through a mode-0600
temporary file and removes it afterward. Terraform state contains the tunnel
token and must stay outside Git and shared folders.

The default SSH user is `root`, matching this repository's current Hermes
installation. Choose another **existing** account with `ssh_user` if desired;
the playbook does not migrate Hermes or Herdr between users. Existing SSH keys,
Tailscale SSH and firewall rules remain available for provisioning and recovery.
The current Ansible controller still uses its existing provisioning key; this
change removes key management from interactive Cloudflare and Tailscale access.

The playbook refuses to overwrite an unrelated SSH certificate authority or
principal-file setting. Integration with an existing certificate deployment
requires a separate change.

## One-time account setup

1. Add the chosen domain to Cloudflare and activate its DNS zone.
2. Create a Zero Trust organization and choose the **Free** plan. If one already
   exists, use it; this Terraform root does not replace account-wide settings.
3. Enable **independent MFA** in Zero Trust's Access settings. The application
   policy requires a security key as a second factor after email PIN
   login. Enroll a recovery authenticator as well.
4. Create a scoped API token for this account and DNS zone with:
   - Cloudflare Tunnel: Edit
   - Access: Apps and Policies: Edit
   - Access: Organizations, Identity Providers, and Groups: Edit
   - DNS: Edit for the selected zone
5. Make the token available as `CLOUDFLARE_API_TOKEN` in the controller's
   environment using your secret store. Never put the token in a `.tfvars` file,
   Git, chat, or a literal command that will be saved in shell history.

Account signup, plan selection, email verification and authenticator enrollment
require the owner's interaction. Infrastructure after that is managed by
Terraform and Ansible. See [independent MFA](https://developers.cloudflare.com/cloudflare-one/access-controls/access-settings/independent-mfa/)
and [Terraform tunnel deployment](https://developers.cloudflare.com/tunnel/guides/terraform/).

## Provision Cloudflare and the VPS connector

Run from the repository root:

```sh
rtk proxy cp terraform/cloudflare/terraform.tfvars.example terraform/cloudflare/terraform.tfvars
```

Edit the ignored `terraform.tfvars` with your account ID, zone ID,
`ssh_hostname = "hermesbox.oct1v.xyz"`, exact personal email and existing SSH
account. Use a lowercase email. If this file is already populated, keep it;
do not overwrite it with the example file.
Use a new hostname or import an existing DNS record before applying. Import an
existing email PIN identity provider rather than creating a duplicate if one
already exists in the account.

```sh
rtk proxy terraform -chdir=terraform/cloudflare init
rtk proxy terraform -chdir=terraform/cloudflare plan
rtk proxy terraform -chdir=terraform/cloudflare apply
rtk proxy python3 scripts/deploy-cloudflare-access.py
```

`HCLOUD_TOKEN` must also be available for Ansible's existing dynamic inventory.
The helper does not apply Terraform itself. It only deploys already-created
Cloudflare resources to Hermesbox.

## Configure the Mac and Herdr

Install the Mac connector helper:

```sh
rtk proxy brew install cloudflared
rtk proxy cloudflared access ssh-config --hostname hermesbox.oct1v.xyz --short-lived-cert
```

The second command prints an OpenSSH configuration; add it to `~/.ssh/config` and set `User root` (or your selected
`ssh_user`) in that host's configuration. Use the printed binary path: Apple
Silicon Homebrew normally installs `cloudflared` under `/opt/homebrew/bin`.
Keep the generated `Match ... exec`, `IdentityFile`, `CertificateFile` and
`ProxyCommand` directives: the proxy alone does not make SSH keyless.

Test in an interactive terminal first:

```sh
rtk proxy ssh root@hermesbox.oct1v.xyz
rtk proxy herdr machine add hermesbox.oct1v.xyz
```

The SSH command should open the Access login flow, require your email PIN and
MFA, issue a temporary certificate and connect. Herdr uses the SSH config host.
If its noninteractive connection needs authentication renewal, use:

```sh
rtk proxy herdr machine reconnect hermesbox.oct1v.xyz
```

## Configure Termius on iPhone

1. Install Tailscale and sign into the **personal** tailnet on the iPhone.
2. In Termius, use Hermesbox's Tailscale IP or full `.ts.net` hostname, port 22,
   and the existing Unix user you want to access. Leave SSH keys unset.
3. Confirm the personal tailnet's network policy permits port 22 and its SSH
   policy permits your exact personal identity to access `tag:hermes` as that
   Unix user. Enabling Tailscale SSH on the VPS does not create these permissions.
4. If Termius refuses authentication without a key or password, use a username
   such as `root+password` with any placeholder password. Tailscale documents
   this compatibility mode; authorization still comes from the Tailscale
   identity and SSH policy, not the placeholder password.
5. Connect and run `herdr` on the VPS to attach to its sessions.

Do not enable password login on the public SSH listener for this workaround.
See [Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh).

## Verification and public access

Before changing the public SSH firewall rule, verify:

- Mac SSH and Herdr connect while work Tailscale is active.
- An unrelated email cannot authenticate to the Cloudflare hostname.
- Certificate regeneration and Herdr reconnection work after login expiration.
- Termius reaches the VPS through personal Tailscale without an SSH key.
- Ansible and a recovery route still work through an approved access path.

This playbook does not close public SSH because the repo's existing Ansible
inventory uses the public IPv4 address. Closing it before migrating and testing
the controller's access path would interrupt configuration management.

## Cost

For one owner using the Free Zero Trust plan, Tunnel and Access add **$0/month**
within that plan's limits; the plan currently allows 50 users. The free plan
does not provide the paid uptime SLA and has shorter log retention. Domain
registration/renewal and the existing Hetzner VPS remain separate costs. No
additional VM is created by this configuration.

Termius Starter includes SSH and SFTP for free. Its Pro plan adds features such
as cloud vault synchronization; those are optional for this setup. Terraform,
Ansible and the connector do not require a paid tool subscription here.

See [Cloudflare pricing](https://www.cloudflare.com/plans/zero-trust-services/)
and [Termius pricing](https://www.termius.com/pricing).
