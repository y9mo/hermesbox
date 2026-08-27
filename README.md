# Hetzner Hermes VPS

This repository provisions and configures a single Hetzner Cloud VPS named
`hermesbox`.

Terraform owns the Hetzner infrastructure. Ansible owns operating-system setup,
Tailscale enrollment, Hermes, Discord, and optional browser automation. The
planned code-agent worker will also be installed and operated through Ansible.

## Quick start

1. [Provision the server](docs/provisioning.md).
2. [Join it to Tailscale](docs/tailscale.md).
3. [Install and configure Hermes](docs/hermes.md).
4. Optionally [install browser automation](docs/browser-automation.md).

The Ansible playbooks and their intended execution order are listed in
[`ansible/README.md`](ansible/README.md).

## Documentation

| Topic | Document |
| --- | --- |
| Hetzner prerequisites, Terraform, inventory, and base OS | [Provisioning](docs/provisioning.md) |
| Tailscale OAuth and enrollment | [Tailscale](docs/tailscale.md) |
| Hermes installation, model provider, testing, and Discord | [Hermes](docs/hermes.md) |
| Chromium, Browser Use, MCP, and stock checker | [Browser automation](docs/browser-automation.md) |
| SSH and connectivity problems | [Troubleshooting](docs/troubleshooting.md) |
| Planned GitHub issue-to-PR worker | [Code-agent worker plan](docs/code-agent-worker-plan.md) |

## Repository layout

```text
.
|-- main.tf                 # Hetzner infrastructure
|-- ansible.cfg             # Ansible controller defaults
|-- ansible/
|   |-- hcloud.yml          # Dynamic Hetzner inventory
|   |-- *.yml               # Installation and configuration playbooks
|   `-- files/              # Files deployed by playbooks
`-- docs/                   # Operator guides and design documents
```

## Secrets and generated state

Keep secrets in the local operator environment or a CI secret store. Do not put
API keys, bot tokens, private keys, `.env` files, Terraform variable files, or
Terraform state in Git.

The committed `.terraform.lock.hcl` is intentional: it pins provider selections
for reproducible Terraform runs. The `.terraform/` working directory and
Terraform state are local generated data and are ignored.
