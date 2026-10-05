# Ansible playbooks

The dynamic inventory in `hcloud.yml` discovers `hermesbox` through the Hetzner
Cloud API. Export `HCLOUD_TOKEN` for playbooks using that dynamic inventory.
The [OMP Builder pilot](../docs/omp-builder.md) uses the explicit static Tailscale
inventory and does **not** need a Hetzner token.

Install the required collections once on the controller:

```sh
ansible-galaxy collection install hetzner.hcloud community.general
```

## Deployment order

| Order | Playbook | Purpose |
| ---: | --- | --- |
| 1 | `bootstrap.yml` | Install and secure the base Debian system. |
| 2 | `install-tailscale.yml` | Install Tailscale and join the tailnet. |
| 3 | `install-hermes.yml` | Install the Hermes CLI. |
| 4 | `configure-hermes-provider.yml` | Configure the Hermes model and API credential. |
| 5 | `test-hermes.yml` | Run a one-shot Hermes smoke test. |
| 6 | `configure-hermes-discord.yml` | Configure Discord and optionally install the gateway service. |
| 7 | `install-browser-automation.yml` | Optionally install Chromium, Browser Use, and its Hermes MCP registration. |
| 8 | `publish-localfi-artifact.yml` | Install nginx and publish the LocalFi pilot artifact over Tailscale. |

Run a playbook from the repository root:

```sh
ansible-playbook ansible/bootstrap.yml
```

## OMP Builder pilot

```sh
ansible-playbook -i ansible/inventory/omp-builder-host-tailscale.yml ansible/install-omp-builder.yml
```

See [setup, authentication and Herdr access](../docs/omp-builder.md). This separate
pilot installs native OMP roles; it does not depend on the Hermes CLI playbooks.

## Operator guides

- [Provisioning and base OS](../docs/provisioning.md)
- [Tailscale](../docs/tailscale.md)
- [Hermes and Discord](../docs/hermes.md)
- [Browser automation](../docs/browser-automation.md)
- [LocalFi artifact publication](../docs/localfi-artifact.md)
- [Troubleshooting](../docs/troubleshooting.md)

Secrets are read from the controller environment and written only to protected
files on the VPS. Never add secrets directly to a playbook or pass them as
literal command-line extra variables, which may be retained in shell history.
