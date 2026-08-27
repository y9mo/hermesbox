# Ansible for hermesbox

This directory uses the Hetzner Cloud dynamic inventory plugin from the
`hetzner.hcloud` collection. It discovers servers from the Hetzner Cloud API,
so the inventory continues to work if Terraform recreates the server with a new
IP address.

## Requirements

Set the Hetzner Cloud token in your shell:

```sh
export HCLOUD_TOKEN=...
```

The `hetzner.hcloud` and `community.general` collections must be installed:

```sh
ansible-galaxy collection install hetzner.hcloud community.general
```

## Inspect Inventory

```sh
ansible-inventory --graph
ansible-inventory --host hermesbox
```

## Check Connectivity

```sh
ssh -i ~/.ssh/hetznercloud root@46.62.201.244
ansible hcloud_server_hermesbox -m ping
```

If the SSH key is passphrase-protected, load it into your SSH agent before
running Ansible:

```sh
ssh-add ~/.ssh/hetznercloud
```

On macOS, store the passphrase in Keychain:

```sh
ssh-add --apple-use-keychain ~/.ssh/hetznercloud
```

## Bootstrap Server

```sh
ansible-playbook ansible/bootstrap.yml
```

## Install Tailscale

Use a Tailscale OAuth client with **Auth Keys: Write** and an allowed tag of
`tag:hermes`. Read-only is not enough because the VPS must be able to register
itself. Export the client secret before running the playbook:

```sh
export TS_API_CLIENT_ID=...
export TS_API_CLIENT_SECRET=...
ansible-playbook ansible/install-tailscale.yml
```

The playbook installs the official Tailscale apt repository, starts
`tailscaled`, joins the tailnet as `hermesbox`, advertises `tag:hermes`, enables
Tailscale SSH, and allows UDP `41641` through UFW. See the root `README.md` for
the OAuth client setup steps.

## Install Hermes Agent

This installs the Hermes CLI non-interactively.

```sh
ansible-playbook ansible/install-hermes.yml
```

Browser tools are intentionally skipped during the first Hermes install. Add the
reproducible browser automation layer with:

```sh
ansible-playbook ansible/install-browser-automation.yml
```

This installs Debian Chromium, a Python virtualenv at
`/opt/hermes-browser-automation`, pinned `browser-use` and Playwright packages,
two command-line tools, and a local Browser Use MCP server registration for
Hermes:

```sh
check-split-availability --pretty
browser-use --help
```

The playbook writes `mcp_servers.browser-use` directly into
`/root/.hermes/config.yaml`, adds `browser-use` to `platform_toolsets.cli` and
`platform_toolsets.discord`, and restarts the Hermes gateway if the gateway
service is installed. It intentionally avoids `hermes mcp add` because that
command performs live MCP discovery and can hang if the stdio server does not
finish discovery cleanly.

After the playbook runs, ask the Discord agent:

```text
Use the browser-use MCP tools to open https://example.com and tell me the page heading.
```

The split checker only checks availability signals. It does not attempt to buy
anything or bypass CAPTCHA / bot protection; blocked pages are reported as
`blocked`.

The deterministic checker does not need an LLM key. General Browser Use agent
tasks do, because the open-source package still needs a model to decide browser
actions. The wrappers source `/root/.hermes/.env`, so they can reuse the
`DEEPSEEK_API_KEY` written by `configure-hermes-provider.yml`.

Browser Use has a native DeepSeek setup:

```python
from browser_use import Agent, ChatDeepSeek

llm = ChatDeepSeek(model="deepseek-chat")
agent = Agent(task="Your task here", llm=llm)
```

Use `BROWSER_USE_API_KEY` only if you intentionally choose Browser Use Cloud or
`ChatBrowserUse` instead of DeepSeek.

## Configure Hermes Provider

Provider setup is a separate step. The playbook reads the API key from your
local shell and writes it to `/root/.hermes/.env` on the VPS.

DeepSeek example:

```sh
export DEEPSEEK_API_KEY=...
ansible-playbook ansible/configure-hermes-provider.yml \
  -e hermes_provider=deepseek \
  -e hermes_model=deepseek-chat \
  -e hermes_api_key_env=DEEPSEEK_API_KEY \
  -e hermes_base_url=https://api.deepseek.com/v1
```

Because DeepSeek is the default in this playbook, the short form is:

```sh
export DEEPSEEK_API_KEY=...
ansible-playbook ansible/configure-hermes-provider.yml
```

Custom OpenAI-compatible endpoint example:

```sh
export OPENAI_API_KEY=...
ansible-playbook ansible/configure-hermes-provider.yml \
  -e hermes_provider=custom \
  -e hermes_model=my-model \
  -e hermes_api_key_env=OPENAI_API_KEY \
  -e hermes_base_url=https://example.com/v1
```

## Test Hermes

Run a one-shot chat smoke test after the provider is configured:

```sh
ansible-playbook ansible/test-hermes.yml
```

Override the prompt if needed:

```sh
ansible-playbook ansible/test-hermes.yml \
  -e 'hermes_test_prompt=Reply with exactly: Hermes is configured.'
```

## Configure Discord Gateway

Create a Discord application and bot in the Discord Developer Portal first.
Enable the Server Members Intent and Message Content Intent, copy the bot token,
invite the bot to your server, and copy your Discord User ID.

Minimum recommended invite URL shape:

```text
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=274878286912
```

Configure Hermes on the VPS:

```sh
export DISCORD_BOT_TOKEN=...
export DISCORD_ALLOWED_USERS=284102345871466496
ansible-playbook ansible/configure-hermes-discord.yml
```

Install and restart the gateway as a system service:

```sh
ansible-playbook ansible/configure-hermes-discord.yml \
  -e hermes_install_gateway_service=true
```

Useful optional settings:

```sh
ansible-playbook ansible/configure-hermes-discord.yml \
  -e discord_free_response_channels=123456789012345678 \
  -e discord_require_mention=false
```

For this server, `#browse` is the browser automation channel, `#market-briefings`
is for ticker requests and scheduled briefings, and `#wizard-home` is for
gateway status and administration. Constrain Discord handling to those
channels and their threads; make only `#market-briefings` free-response so
ticker requests do not depend on mention parsing:

```sh
ansible-playbook ansible/configure-hermes-discord.yml \
  -e discord_allowed_channels=1523115051907813497,1541029550073454643,1515000720854618213 \
  -e discord_free_response_channels=1541029550073454643
```

The playbook also keeps the unused WhatsApp gateway integration disabled with
`WHATSAPP_ENABLED=false`.
