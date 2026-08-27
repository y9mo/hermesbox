# Hermes

## Install Hermes

```sh
ansible-playbook ansible/install-hermes.yml
```

The playbook installs the Hermes CLI non-interactively. Browser tooling is
deliberately separate; install it later through the
[browser automation playbook](browser-automation.md).

## Configure a model provider

Provider setup reads an API key from the local operator environment and writes
it to `/root/.hermes/.env` on the VPS with restricted permissions.

DeepSeek is the default:

```sh
export DEEPSEEK_API_KEY=...
ansible-playbook ansible/configure-hermes-provider.yml
```

The fully explicit form is:

```sh
ansible-playbook ansible/configure-hermes-provider.yml \
  -e hermes_provider=deepseek \
  -e hermes_model=deepseek-chat \
  -e hermes_api_key_env=DEEPSEEK_API_KEY \
  -e hermes_base_url=https://api.deepseek.com/v1
```

For another OpenAI-compatible endpoint:

```sh
export OPENAI_API_KEY=...
ansible-playbook ansible/configure-hermes-provider.yml \
  -e hermes_provider=custom \
  -e hermes_model=my-model \
  -e hermes_api_key_env=OPENAI_API_KEY \
  -e hermes_base_url=https://example.com/v1
```

## Smoke test

```sh
ansible-playbook ansible/test-hermes.yml
```

Override the prompt when needed:

```sh
ansible-playbook ansible/test-hermes.yml \
  -e 'hermes_test_prompt=Reply with exactly: Hermes is configured.'
```

## Configure Discord

Create a Discord application and bot in the Discord Developer Portal. Enable
the Server Members Intent and Message Content Intent, invite the bot, and copy
the bot token and your Discord user ID.

A minimum recommended invite URL has this form:

```text
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=274878286912
```

Configure the gateway:

```sh
export DISCORD_BOT_TOKEN=...
export DISCORD_ALLOWED_USERS=...
ansible-playbook ansible/configure-hermes-discord.yml
```

Install and restart Hermes as a system service:

```sh
ansible-playbook ansible/configure-hermes-discord.yml \
  -e hermes_install_gateway_service=true
```

Optional behavior settings include:

```sh
ansible-playbook ansible/configure-hermes-discord.yml \
  -e discord_free_response_channels=123456789012345678 \
  -e discord_require_mention=false
```

The repository defaults currently restrict Discord handling to the configured
`browse`, `market-briefings`, and `wizard-home` channels. Only
`market-briefings` is configured for free responses. The unused WhatsApp
integration is explicitly disabled.

Discord IDs are deployment-specific. Review the defaults in
`ansible/configure-hermes-discord.yml` before using the playbook for another
server.
