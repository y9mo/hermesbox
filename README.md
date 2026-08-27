# Hetzner Hermes VPS

This repo provisions and configures a single Hetzner Cloud VPS named
`hermesbox`.

Terraform owns the Hetzner infrastructure. Ansible owns operating-system setup,
Tailscale enrollment, and Hermes configuration. Keep secrets in your local shell
or CI secret store, not in Terraform variables or state.

## Prerequisites

- Hetzner Cloud API token exported as `HCLOUD_TOKEN`
- SSH key at `~/.ssh/hetznercloud` with public key at
  `~/.ssh/hetznercloud.pub`
- Ansible collections `hetzner.hcloud` and `community.general`
- Tailscale OAuth client secret with `Auth Keys: Write` and an allowed tag of
  `tag:hermes`

```sh
export HCLOUD_TOKEN=...
ansible-galaxy collection install hetzner.hcloud community.general
```

## Provision the VPS

```sh
terraform init
terraform apply
```

The Ansible inventory in `ansible/hcloud.yml` discovers the server from the
Hetzner API, so it continues to work after Terraform recreates the VPS with a
new public IP.

## Get Tailscale OAuth Credentials

Use an OAuth client instead of a long-lived auth key. Tailscale auth keys expire
after at most 90 days, while an OAuth client can create short-lived registration
credentials when automation runs.

1. Open the Tailscale admin console.
2. Open the **Trust credentials** page, or go directly to
   <https://login.tailscale.com/admin/settings/oauth>.
3. Select **Credential**.
4. Select **OAuth**.
5. In the operations/scopes list, grant **Auth Keys: Write**. Read-only is not
   enough because the VPS must be able to register itself.
6. For the scope tags, allow `tag:hermes`.
7. Generate the credential and copy both values. The secret is shown once.

If `tag:hermes` is not available in the OAuth client form, add it to the
tailnet policy first. A minimal tag-owner entry is:

```json
{
  "tagOwners": {
    "tag:hermes": ["autogroup:admin"]
  }
}
```

Export the values locally:

```sh
export TS_API_CLIENT_ID=...
export TS_API_CLIENT_SECRET=...
```

The playbook uses `TS_API_CLIENT_SECRET` directly with `tailscale up`. Keep
`TS_API_CLIENT_ID` as documentation and for testing the OAuth credential.

Optional credential smoke test:

```sh
curl -d "client_id=${TS_API_CLIENT_ID}" \
  -d "client_secret=${TS_API_CLIENT_SECRET}" \
  https://api.tailscale.com/api/v2/oauth/token
```

## Configure the VPS

Bootstrap the base OS:

```sh
ansible-playbook ansible/bootstrap.yml
```

Install Tailscale and register the VPS as `hermesbox` with `tag:hermes`:

```sh
ansible-playbook ansible/install-tailscale.yml
```

The Tailscale playbook:

- installs the official Debian 13 Tailscale apt repository
- installs and starts `tailscaled`
- joins the tailnet using `TS_API_CLIENT_SECRET`
- advertises `tag:hermes`
- enables Tailscale SSH
- allows UDP `41641` through UFW for better direct connectivity

You can override defaults when running the playbook:

```sh
ansible-playbook ansible/install-tailscale.yml \
  -e tailscale_hostname=hermesbox \
  -e tailscale_tag=tag:hermes \
  -e tailscale_enable_ssh=true
```

If you prefer a manually generated Tailscale auth key, export it as
`TAILSCALE_AUTH_KEY`; the playbook will use that before `TS_API_CLIENT_SECRET`.

## SSH Troubleshooting

If Ansible fails with `Permission denied (publickey,password)`, first confirm
plain SSH works with the same key:

```sh
ssh -i ~/.ssh/hetznercloud root@46.62.201.244
```

The configured private key is passphrase-protected. Load it into your SSH agent
before running Ansible:

```sh
ssh-add ~/.ssh/hetznercloud
```

On macOS, store the passphrase in Keychain:

```sh
ssh-add --apple-use-keychain ~/.ssh/hetznercloud
```

Then retry the Ansible connection check:

```sh
ansible hcloud_server_hermesbox -m ping
```

## Hermes

After networking is configured, continue with the Hermes playbooks documented in
`ansible/README.md`.

## Browser Automation

Install the optional browser automation layer:

```sh
ansible-playbook ansible/install-browser-automation.yml
```

This installs Chromium, an isolated Python virtualenv, pinned `browser-use` and
Playwright packages, and a deterministic stock checker for the Midea Portasplit:

```sh
check-split-availability --pretty
```

The checker currently covers:

- <https://www.boulanger.com/ref/1216685>
- <https://www.castorama.fr/climatiseur-portasplit-midea-reversible-3500w/8431312260509_CAFR.prd>
- <https://www.leroymerlin.fr/produits/climatiseur-split-mobile-reversible-portasplit-midea-par-optimea-93857579.html>

It reports `available`, `unavailable`, `unknown`, `blocked`, or `error`. It does
not attempt to bypass CAPTCHA / bot protection or make a purchase.

The playbook also registers Browser Use as a local Hermes MCP server by writing
`mcp_servers.browser-use` directly into `/root/.hermes/config.yaml`.

The wrapper at `/usr/local/bin/browser-use-mcp` sources `/root/.hermes/.env`,
maps `DEEPSEEK_API_KEY` to Browser Use's OpenAI-compatible MCP path, and runs:

```sh
browser-use --mcp
```

The playbook adds `browser-use` to `platform_toolsets.cli` and
`platform_toolsets.discord`, then restarts the Hermes gateway if that service is
installed. This avoids `hermes mcp add` because that command performs live MCP
discovery and can hang if the stdio server does not finish discovery cleanly.
After the playbook runs, ask the Discord agent:

```text
Use the browser-use MCP tools to open https://example.com and tell me the page heading.
```

The deterministic checker does not need an LLM key. General Browser Use agent
tasks do, because the open-source package still needs a model to decide browser
actions.

This repo already configures Hermes with DeepSeek by writing `DEEPSEEK_API_KEY`
to `/root/.hermes/.env`. The browser wrappers source that file, so Browser Use
can reuse the same DeepSeek key:

```python
from browser_use import Agent, ChatDeepSeek

llm = ChatDeepSeek(model="deepseek-chat")
agent = Agent(task="Your task here", llm=llm)
```

Use `BROWSER_USE_API_KEY` only if you intentionally choose Browser Use Cloud or
`ChatBrowserUse` instead of DeepSeek:

```sh
BROWSER_USE_API_KEY=...
```
