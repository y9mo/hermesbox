# OMP Builder on Hermesbox

This provisions a reusable OMP and Herdr environment on
`hermesbox.tail85f0d.ts.net`. It installs the agent runtime and development tools;
it does not start paid agents, clone a project, or approve, implement, review, or
accept any project change. OMP supplies the native role and collaboration system.
Account shells and the launcher load protected GitHub and RunInfra credentials.

## Install from this computer

Use the existing `~/.ssh/hetznercloud` SSH key and Tailscale connection. The static
inventory targets the existing box; **HCLOUD_TOKEN is not required**. It does not
change nginx, firewall rules or the Tailscale configuration.

Unlock the local password store, then run from this repository's root:

```bash
ansible-galaxy collection install community.general
ansible-playbook -i ansible/inventory/omp-builder-host-tailscale.yml \
  ansible/install-omp-builder.yml --syntax-check
ansible-playbook -i ansible/inventory/omp-builder-host-tailscale.yml \
  ansible/install-omp-builder.yml
```

The default public key is `~/.ssh/hetznercloud.pub`. If only the private key exists,
derive its public half with `ssh-keygen -y -f ~/.ssh/hetznercloud > ~/.ssh/hetznercloud.pub`.
For a different public key, pass `-e omp_builder_owner_public_key_file=/absolute/path.pub`.
See [the optional public variable example](../ansible/omp-builder.example.yml)
for model mapping overrides.
Only this public key goes to the dedicated account; private SSH keys stay here.
The role manages that account's authorized_keys as a whole.

The role reads the first line of these local password-store entries on the
Ansible controller:

```bash
pass show y9mo/github/pat/hermesbox >/dev/null
pass show y9mo/runinfra/apikey >/dev/null
```

The `community.general.passwordstore` lookup fails when either entry is missing.
The secret task suppresses logs and diffs and writes root-owned
`/etc/omp-builder/credentials.env`, group `omp-builder`, mode 0640. Reapply after
changing a password-store entry to rotate the remote credential. The GitHub PAT is
exported as `GH_TOKEN`; GitHub CLI uses it directly, and Git is configured to use
`gh auth git-credential` for HTTPS remotes. The password store and GPG material
remain on the controller. New SSH and Herdr shells load both variables. After
rotating credentials or applying the role in an existing pane, start a new pane
or run `set +x; source /etc/omp-builder/credentials.env`.

Repeat the same apply to verify idempotency. The role never modifies repositories
or worktrees placed in its workspace. Ansible can validate syntax without the
host. A first `--check` run cannot fully simulate missing accounts and downloads;
it is not a deployment test. The role supports Debian Linux on x86_64 and aarch64.

## Installed layout and versions

| Path | Purpose |
|---|---|
| `/var/lib/omp-builder` | Dedicated account home, private OMP auth/sessions and Herdr state |
| `/var/lib/omp-builder/.omp/agent/agents` | Four native role definitions shared by project worktrees |
| `/etc/omp-builder/config.yml` | Central model mappings and pilot settings |
| `/etc/omp-builder/credentials.env` | Root-managed GitHub and RunInfra credentials loaded by the launcher |
| `/var/lib/omp-builder/.omp/agent/models.yml` | RunInfra provider, environment key reference only |
| `/var/lib/omp-builder/.omp/agent/APPEND_SYSTEM.md` | Scoped main-coordinator instructions |
| `/opt/omp-builder/workspace` | Persistent location for project repositories |
| `/opt/omp-builder/worktrees` | Persistent Herdr worktree location |
| `/opt/omp-builder/evidence` | Project and run-specific evidence outside Git |
| `/opt/omp-builder/tools` | Root-owned versioned tools; account-local symlinks select the version |

| Tool | Pin | Upstream |
|---|---|---|
| OMP | 18.2.5 | [Release](https://github.com/can1357/oh-my-pi/releases/tag/v18.2.5) |
| Herdr | 0.9.1 | [Release](https://github.com/herdrdev/herdr/releases/tag/v0.9.1) |
| Go | 1.26.8 | [Downloads](https://go.dev/dl/) |
| Node | 22.23.2 | [Release files](https://nodejs.org/dist/v22.23.2/) |

Both x86_64 and aarch64 downloads are SHA-256 pinned in role defaults. OMP uses
its standalone release binary. Debian supplies Chromium and build dependencies.
Update versions and matching checksums together. Existing Herdr sessions retain
their running binary until deliberately restarted; installing does not restart them.

## Connect with Herdr

Add to this computer's `~/.ssh/config`:

```sshconfig
Host hermesbox-builder
    HostName hermesbox.tail85f0d.ts.net
    User omp-builder
    IdentityFile ~/.ssh/hetznercloud
    IdentitiesOnly yes
```

Load a passphrase-protected key into your local SSH agent for background
reconnections. Verify:

```bash
ssh hermesbox-builder 'command -v herdr; herdr --version; omp --version; go version; node --version'
```

Use Herdr **0.9.1** locally to match the server (the inspected local installation
was 0.9.0). Follow the [official installation instructions](https://herdr.dev/docs/).
Then attach or save the machine:

```bash
herdr --remote hermesbox-builder --session omp-builder
# Alternatively:
herdr machine add hermesbox-builder --label Hermesbox Builder --remote-session omp-builder
herdr
```

The role installs Herdr's official OMP integration as the dedicated account. In a
remote pane run `herdr integration status`; verify OMP installed and the integration
is current. New panes load `GH_TOKEN`, so GitHub CLI and HTTPS Git use the
password-store PAT without an interactive username prompt. Clone or place a
project beneath `/opt/omp-builder/workspace`, then start from that repository root:

```bash
gh api repos/<owner>/<repository> --jq .permissions
git clone https://github.com/<owner>/<repository>.git
cd /opt/omp-builder/workspace/<project>
omp-builder-launch
```

`gh auth status` proves that the token is valid, not that a fine-grained PAT can
access a particular repository. An API `404` or Git `403` here means the PAT must
be granted that repository and the permissions required by its workflow.

OMP runs on Hermesbox, so its browser callback on `localhost:1455` is not directly
reachable from the browser on your computer. Before logging in, open a separate
terminal on your computer and keep this SSH tunnel running:

```bash
ssh -N -L 1455:localhost:1455 hermesbox-builder
```

Inside OMP use `/login`, choose `openai-codex`, then open
`http://localhost:1455/launch` in the browser on your computer and complete OpenAI
authentication. Close the tunnel with `Ctrl+C` after OMP confirms the login. Do
not paste the original `auth.openai.com/oauth/authorize` URL into OMP's code
prompt; manual recovery requires the final callback URL containing `code=`.

The login belongs to this Unix account, not root or your laptop. The two configured
password-store entries do not provide OpenAI authentication. Press `Alt+A` for
OMP's Agent Hub: model, activity, transcript and steering for each child. Herdr
owns the remote panes; task children need not have separate panes.

OMP 18.2.5 also accepts `OPENAI_API_KEY` for models under the separate `openai`
provider. That key does not authenticate the current `openai-codex/...` selectors.
Using API billing would require another protected key, exporting it as
`OPENAI_API_KEY`, and changing the architect/reviewer selectors to API model IDs
available to that OpenAI project.

Detach with `Ctrl+b q`, reconnect and verify the same work continues. A server
restart is different: pane processes end. `resume_agents_on_restore=false` keeps
recovery explicit. Inspect unfinished stages and owned project processes, then use
`omp-builder-launch --resume` and select the intended OMP session. Never rely on
an automatic restart to reload credentials or resume acceptance safely.

## Native team and configuration

| Role | Alias | Default model |
|---|---|---|
| Main / architect | default / architect | openai-codex/gpt-5.6-sol:low |
| Reviewer | reviewer | openai-codex/gpt-5.6-sol:low |
| Implementer | implementer | runinfra/zai-org/GLM-5.3-Flash:max |
| Acceptance | acceptance | runinfra/zai-org/GLM-5.3-Flash:max |

Change the four `omp_builder_*_model` variables and reapply to choose another AI.
`openai-codex/gpt-6-astra:low` is the explicit architect/reviewer alternative.
Agent definitions use aliases, not embedded model IDs. The launcher exports the
native `PI_CONFIG_FILES` overlay so settings propagate to task children; model
mappings and `task.agentModelOverrides` point to the same aliases. There is no
custom dispatcher. Settings are centrally managed by Ansible; changing an OMP
runtime setting does not change this provisioning source.

Agents are installed at native **user scope** so every durable worktree shares
them without adding deployment files to a project. OMP project agent files take
precedence: inspect any `.omp/agents` in the active repository and reconcile
same-name definitions before starting. Project config, CLI/runtime overrides and
model fallback also need live inspection. Verify the *actual* provider/model and
effort in Agent Hub, not just the requested selector. Do not proceed on a mismatch.
The coordinator append prompt scopes coordination to the main session; children
retain their specialist assignment. A project `APPEND_SYSTEM.md` can override the
user file: if present, explicitly launch with
`omp-builder-launch --append-system-prompt /var/lib/omp-builder/.omp/agent/APPEND_SYSTEM.md`.

Normal OMP collaboration and tools remain enabled. Roles express responsibilities,
not Unix isolation or a security sandbox. `blocking: true`, `async.enabled=false`
and a concurrency limit of two support sequential dependent stages and at most
two independent assignments. The coordinator makes successive native task calls:

```text
Architect -> Owner contract approval -> Implementer -> independent Reviewer
    -> readiness verification -> independent Acceptance -> Owner merge decision
Review blockers / product failures -> repair -> review new revision -> fresh acceptance
```

The coordinator follows the active repository's workflow and can run at most two
independent implementation lanes. Dependent implementation, review, and acceptance
remain sequential. Shared validation artifacts are coordinated centrally.

## Verification before the first project assignment

Complete and record these host checks; local unit/syntax tests do not establish them:

1. Apply twice and confirm the second run changes nothing. Check tool versions
   under `omp-builder` and verify non-interactive SSH PATH.
2. Provision the GitHub and RunInfra entries and complete `/login` for OpenAI Codex.
   From a project root:

   ```bash
   omp-builder-launch models find GLM-5.3-Flash --json
   omp-builder-launch models find gpt-5.6-sol --json
   omp-builder-launch config get modelRoles --json
   ```

   Catalog presence is not authentication or inference. Make a small live request
   with a harmless read/tool call on each selected provider, then dispatch all four
   named specialists on harmless assignments. Check the effective model, low
   effort for architecture/review, max effort for implementation/acceptance,
   streaming, tools, discovery, and unintended fallback. Run a synthetic
   browser/image smoke as GLM acceptance. Treat unavailable models as BLOCKED.
3. In Herdr observe a child in Agent Hub, detach/reconnect without stopping it,
   and verify explicit manual resume after a deliberate disposable-session restart.
4. Rehearse in a disposable worktree: sequential implementation, separate review,
   a routed repair and a fresh acceptance handoff. Confirm the coordinator advances
   routine stages without asking the Owner to trigger each one. Confirm it pauses
   for absent contract approval rather than fabricating it.

The role installs `git`, `gh`, and OpenSSH and provisions the dedicated GitHub PAT
from password-store. It does not install a Git identity or SSH private key. Keep
tokens out of repository URLs, prompts, logs, and Git. Limit the PAT to the minimum
repositories and permissions needed by projects assigned to this builder.

## Maintenance and local checks

The playbook does not destroy worktrees, evidence, or authentication on rerun. To
retire the setup, stop owned OMP, Herdr, and project processes, archive evidence,
and remove the account and workspace only after an explicit retention decision.
Version updates do not restart live sessions. Repair failed downloads or
authentication and reapply; never reset project work to make provisioning pass.

```bash
# Use a Python environment with PyYAML and Jinja2 (Ansible's environment has both).
python3 -m unittest discover -s tests -p 'test_omp_builder.py' -v
ansible-playbook -i ansible/inventory/omp-builder-host-tailscale.yml \
  ansible/install-omp-builder.yml --syntax-check
```

For a complete disposable Debian install and idempotency check, install
`community.docker` and run `bash tests/provision-omp-builder-container.sh`. Docker
downloads the pinned tools into an isolated container and deletes that container
on exit. It uses a dummy API key and makes no paid model requests.

The unit tests exercise missing and quoted GitHub/RunInfra credentials, exact
argument forwarding, role alias resolution, and the low/max effort mappings. They
do not make model calls or install host software.

Sources checked against the pinned OMP release: [agent roles/discovery](https://github.com/can1357/oh-my-pi/blob/v18.2.5/docs/task-agent-discovery.md),
[configuration precedence](https://github.com/can1357/oh-my-pi/blob/v18.2.5/docs/config-usage.md),
[prompt scope](https://github.com/can1357/oh-my-pi/blob/v18.2.5/docs/system-prompt-customization.md),
[browser Eval API](https://github.com/can1357/oh-my-pi/blob/v18.2.5/docs/tools/browser.md),
[OMP environment variables](https://github.com/can1357/oh-my-pi/blob/v18.2.5/docs/environment-variables.md),
[Ansible password-store lookup](https://docs.ansible.com/projects/ansible/latest/collections/community/general/passwordstore_lookup.html),
[Herdr remote sessions](https://herdr.dev/docs/persistence-remote/),
[Herdr integration](https://herdr.dev/docs/integrations/).
