# Code Agent Worker Plan

Status: first implementation selected; not yet implemented.

## Objective

Run a bounded software-development worker on `hermesbox` that turns an approved
GitHub issue into a reviewed pull request.

The worker will use different agents for implementation and review:

- OpenCode with an Ollama Cloud coding model implements the issue.
- Codex independently reviews the implementation.
- A small deterministic controller owns the lifecycle, GitHub state, retries,
  timeouts, Git operations, and durable run records.
- Hermes remains the human-facing supervisor for status, manual triggers,
  retries, and cancellation. It is not part of the inner coding loop.

The central design rule is that agents operate inside bounded stages. They do
not decide how long the workflow runs, which issue to claim, whether to push,
or whether to open a pull request.

## First implementation

The first version will be a small Python controller installed and configured by
Ansible. A systemd timer will invoke it periodically. Each invocation will claim
at most one issue and run at most one workflow at a time.

```text
GitHub issue labeled agent-ready
                 |
                 v
       deterministic controller
                 |
       claim issue and persist state
                 |
       fetch repository and create
       an isolated Git worktree
                 |
                 v
     OpenCode + Ollama Cloud model
                 |
          controller runs tests
                 |
                 v
           Codex CLI review
          /                \
     approved          findings
         |                 |
         |       findings return to OpenCode
         |          (maximum 2 rounds)
         |                 |
         +-----------------+
                 |
          push branch and open PR
```

Initial defaults:

- One configured GitHub repository.
- One active issue at a time.
- Polling with a systemd timer instead of a webhook listener.
- Two implementation/review rounds at most.
- Branches named `agent/issue-<number>`.
- Worktrees isolated by repository and issue number.
- Tests supplied explicitly in configuration rather than guessed by the
  controller.
- A draft pull request when review findings remain after the final round.
- No automatic merge.

These constraints make the first deployment observable and recoverable. They
can be relaxed after successful live runs.

## Responsibilities

### Controller

The controller is the authority for workflow state. It will:

1. Query the configured repository for the oldest open issue labeled
   `agent-ready`.
2. Claim it by changing labels and recording the issue identity locally.
3. Fetch the base branch, create a branch, and create an isolated worktree.
4. Build the implementation prompt from the issue and repository instructions.
5. Invoke OpenCode with a fixed model, timeout, and working directory.
6. Run the configured verification commands itself and capture their output.
7. Commit a successful implementation before invoking Codex review.
8. Capture the review as plain text and validate an explicit verdict marker.
9. Return findings to OpenCode for a bounded correction round when necessary.
10. Push through the GitHub credential held by the controller and open the pull
    request.
11. Update labels and preserve enough state to diagnose or resume failures.

Agent processes will receive a sanitized environment. In particular, OpenCode
will not inherit the GitHub token; only the controller can mutate GitHub state
or push a branch.

### Implementer

OpenCode may inspect and edit only the assigned worktree. Its prompt will
include:

- the issue title, body, and acceptance criteria;
- repository-local agent instructions;
- the configured verification commands;
- independent review findings on correction rounds; and
- a requirement to explain blockers rather than invent missing requirements.

The initial model will be an Ollama Cloud Qwen or GLM coding model selected in
configuration. The exact model identifier will be verified during deployment
instead of being embedded in controller code.

### Reviewer

Codex will review the branch against the configured base branch. Review output
will be stored as text. The review prompt will require exactly one terminal
verdict:

```text
VERDICT: APPROVE
```

or:

```text
VERDICT: CHANGES_REQUESTED
```

An absent or malformed verdict is a workflow error, not an approval. Controller
logic will not equate the Codex process exit code with review approval.

### Hermes

Hermes will remain outside the implementation/review loop. It can eventually
invoke a small administrative CLI to:

- show current and recent runs;
- trigger a poll;
- retry a blocked issue;
- cancel future rounds for an active issue; and
- report the branch or pull-request URL.

Hermes must not bypass the repository allowlist, maximum-round limit, or
controller state transitions.

## State model

GitHub labels provide visible coarse-grained state:

| Label | Meaning |
| --- | --- |
| `agent-ready` | A maintainer has authorized the worker to claim the issue. |
| `agent-working` | The issue is claimed and implementation is running. |
| `agent-review` | Tests passed and Codex review is running. |
| `agent-blocked` | The workflow needs human attention or exhausted its rounds. |
| `agent-done` | The worker opened a pull request for the issue. |

Detailed state will be persisted under `/opt/code-agent/runs/<run-id>/state.json`.
State writes will use a temporary file followed by an atomic rename. Each run
will also retain:

```text
issue.json
implementation-1.log
tests-1.log
review-1.txt
implementation-2.log
tests-2.log
review-2.txt
state.json
```

Expected states are:

```text
claimed -> preparing -> implementing -> testing -> reviewing
                                          ^             |
                                          +-- revising <-+

reviewing -> publishing -> completed
any state -> blocked
```

The controller will take an exclusive host lock before claiming work. A second
timer invocation will exit successfully while another run holds the lock.

## Failure behavior

- A failed tool invocation, timeout, malformed reviewer verdict, or failed test
  blocks publication and records the error.
- Test failures are returned to the implementer when a correction round remains.
- Unresolved review findings after the final round produce a pushed branch and
  draft pull request clearly marked as needing human attention.
- A failure before useful commits exist leaves the branch unpushed and labels
  the issue `agent-blocked`.
- Re-running the controller must not create a second branch, worktree, or pull
  request for the same recorded run.
- Cleanup removes worktrees only after their branch and logs are safely
  preserved. Failed-run logs remain available for diagnosis.

## Security boundaries

- Run the worker as a dedicated `code-agent` Unix user, not as root or the
  Hermes service identity.
- Process issues only from an explicit owner/repository allowlist.
- Require the `agent-ready` label to be applied by a trusted maintainer.
- Use a fine-grained GitHub credential limited to repository metadata, issues,
  contents, and pull requests. Do not grant administration or deletion rights.
- Store worker secrets in `/etc/code-agent/worker.env`, owned by root and
  readable by the worker group only. Never place them in Git or run logs.
- Give the implementer a sanitized environment without the GitHub token,
  Hermes secrets, Tailscale credentials, or unrelated VPS credentials.
- Apply timeouts and output-size limits to every agent and test subprocess.
- Treat issue text, repository contents, test output, and reviewer text as
  untrusted input.
- Do not automatically merge or deploy pull requests.

## Planned server layout

```text
/opt/code-agent/
|-- repos/
|   `-- <owner>--<repo>.git
|-- worktrees/
|   `-- <owner>--<repo>--issue-<number>/
|-- runs/
|   `-- <run-id>/
`-- app/
    |-- code_agent.py
    `-- prompts/

/etc/code-agent/
|-- config.toml
`-- worker.env
```

The repository implementation is expected to add:

```text
ansible/install-code-agent.yml
ansible/test-code-agent.yml
ansible/files/code-agent/code_agent.py
ansible/files/code-agent/prompts/implement.md
ansible/files/code-agent/prompts/revise.md
ansible/files/code-agent/prompts/review.md
ansible/templates/code-agent-config.toml.j2
ansible/templates/code-agent.service.j2
ansible/templates/code-agent.timer.j2
```

The systemd service will be a oneshot job. The timer will provide periodic
polling, while the same service can be started manually by Hermes or an
operator.

## Configuration

The non-secret configuration will include:

- GitHub repository and base branch;
- required issue label and state labels;
- local mirror, worktree, and run paths;
- implementer model and command;
- reviewer command;
- ordered verification commands;
- maximum rounds;
- per-stage timeouts; and
- whether unresolved final findings may create a draft pull request.

Secrets will be supplied to Ansible from the operator environment and written
only to the protected server environment file. At minimum, the first live run
needs GitHub authentication, Ollama Cloud authentication, and Codex
authentication.

## Acceptance criteria for the first live trial

1. Applying the Ansible playbook twice is safe and leaves the service healthy.
2. Labeling one test issue `agent-ready` causes exactly one run to claim it.
3. The run uses a unique branch and worktree and does not modify the base clone.
4. OpenCode edits the assigned worktree using the configured Ollama Cloud model.
5. The controller runs every configured verification command and stores logs.
6. Codex reviews the complete branch diff independently of the implementer.
7. Findings result in no more than one correction round in the initial setup.
8. Approval creates a non-draft pull request linked to the issue.
9. Exhausted findings create a draft pull request and mark the issue blocked.
10. A restart during a run can recover or block it without duplicating GitHub
    artifacts.
11. Agent logs and process environments do not expose configured secrets.
12. Hermes can report the run status without owning the workflow itself.

## Deferred options

The first implementation deliberately defers:

- concurrent issue processing;
- webhook ingestion;
- automatic merging or deployment;
- a web dashboard;
- multi-repository discovery;
- Temporal, Prefect, or another workflow platform;
- Pi as an embedded agent harness;
- GitHub Agentic Workflows as the control plane; and
- unrestricted Hermes-driven workflow decisions.

After several successful trials, the run data should tell us whether the small
controller remains sufficient or whether moving to Pi, `gh-aw`, or a durable
workflow engine would remove meaningful operational pain.

## Implementation order

1. Add the dedicated user, directories, protected configuration, administrative
   CLI entry point, and systemd units through Ansible.
2. Implement and test the state machine with fake GitHub, implementer, reviewer,
   and test subprocesses.
3. Add real `gh`, OpenCode, and Codex adapters while retaining dry-run mode.
4. Deploy with the timer disabled and complete one manually triggered test
   issue.
5. Enable polling only after the manual trial creates the expected pull request
   and preserves complete logs.
6. Add read-only Hermes status and trigger commands after the worker is stable.
