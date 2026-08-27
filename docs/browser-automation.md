# Browser automation

Browser automation is optional and installed independently from Hermes:

```sh
ansible-playbook ansible/install-browser-automation.yml
```

The playbook installs:

- Debian Chromium;
- an isolated Python virtual environment at
  `/opt/hermes-browser-automation`;
- pinned Browser Use and Playwright packages;
- a deterministic Midea PortaSplit stock checker; and
- a local Browser Use MCP registration for Hermes.

## Stock checker

Run the checker on the VPS:

```sh
check-split-availability --pretty
```

It currently checks these product pages:

- <https://www.boulanger.com/ref/1216685>
- <https://www.castorama.fr/climatiseur-portasplit-midea-reversible-3500w/8431312260509_CAFR.prd>
- <https://www.leroymerlin.fr/produits/climatiseur-split-mobile-reversible-portasplit-midea-par-optimea-93857579.html>

The result is `available`, `unavailable`, `unknown`, `blocked`, or `error`. The
checker does not attempt to bypass CAPTCHA or bot protection and cannot make a
purchase. It does not require an LLM credential.

## Browser Use MCP

The playbook writes `mcp_servers.browser-use` into
`/root/.hermes/config.yaml`, adds `browser-use` to the Hermes CLI and Discord
toolsets, and restarts the gateway when it is installed.

The `/usr/local/bin/browser-use-mcp` wrapper:

- loads `/root/.hermes/.env`;
- maps `DEEPSEEK_API_KEY` to Browser Use's OpenAI-compatible MCP path when
  needed;
- selects the managed Browser Use configuration; and
- starts `browser-use --mcp` in headless mode.

The playbook edits the Hermes configuration directly instead of calling
`hermes mcp add`, because that command performs live MCP discovery and can hang
when a stdio server does not finish discovery cleanly.

After installation, test it through Discord:

```text
Use the browser-use MCP tools to open https://example.com and tell me the page heading.
```

General Browser Use agent tasks require a model credential. The wrappers can
reuse the DeepSeek key already configured for Hermes:

```python
from browser_use import Agent, ChatDeepSeek

llm = ChatDeepSeek(model="deepseek-chat")
agent = Agent(task="Your task here", llm=llm)
```

Set `BROWSER_USE_API_KEY` only when intentionally using Browser Use Cloud or
`ChatBrowserUse` instead of DeepSeek.
