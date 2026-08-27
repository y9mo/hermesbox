# Provisioning

## Prerequisites

- A Hetzner Cloud API token exported as `HCLOUD_TOKEN`.
- An SSH key at `~/.ssh/hetznercloud`, with its public key at
  `~/.ssh/hetznercloud.pub`.
- Terraform.
- Ansible with the `hetzner.hcloud` and `community.general` collections.

```sh
export HCLOUD_TOKEN=...
ansible-galaxy collection install hetzner.hcloud community.general
```

## Create the VPS

Initialize Terraform and apply the configuration:

```sh
terraform init
terraform apply
```

Terraform creates a Debian 13 `cpx32` server named `hermesbox` in Hetzner's
Helsinki location and registers the configured SSH public key.

Terraform state can contain sensitive infrastructure data. It is ignored by
Git and must remain in protected local or remote state storage.

## Inspect the Ansible inventory

The inventory in `ansible/hcloud.yml` discovers the server from the Hetzner API,
so it continues working if Terraform recreates the VPS with a new public IP.

```sh
ansible-inventory --graph
ansible-inventory --host hermesbox
ansible hcloud_server_hermesbox -m ping
```

## Bootstrap Debian

```sh
ansible-playbook ansible/bootstrap.yml
```

The bootstrap playbook installs baseline administration packages, enables
automatic security updates and fail2ban, permits SSH through UFW, and enables a
deny-by-default firewall policy.

Continue with [Tailscale enrollment](tailscale.md).
