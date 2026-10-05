# LocalFi artifact publication

`ansible/publish-localfi-artifact.yml` installs nginx and publishes the first
LocalFi review artifact on `hermesbox`. The site is intended to be reached over
Tailscale only.

The controller must have `HCLOUD_TOKEN` available for the dynamic inventory and
must be able to reach the host. Prefer a Tailscale hostname by overriding
`ansible_host`; the default Hetzner inventory uses its existing public IPv4 SSH
connection. The Tailscale hostname is the browser URL, not necessarily the
Ansible transport.

The bundle must contain `index.html`, `oh-my-pi-pilot.html`,
`oh-my-pi-pilot.md`, and `manifest.json`. Releases are installed under
`/srv/localfi-artifact/releases/` and activated through the `current` symlink.

Example:

```sh
ansible-playbook ansible/publish-localfi-artifact.yml \
  -e localfi_artifact_bundle=/absolute/path/to/bundle \
  -e localfi_artifact_release_id=20260911-abc123
```

The playbook installs nginx, enables the site, allows port 80 through
`tailscale0`, validates the release, and checks the served HTML and Markdown.
It does not open public HTTP access. Set
`localfi_artifact_tailscale_address` only when overriding discovery is needed;
otherwise the playbook runs `tailscale ip -4` on the host and binds nginx to
the discovered address. The playbook refuses to publish if UFW is not active.

Rollback uses a prior release ID:

```sh
ansible-playbook ansible/publish-localfi-artifact.yml \
  -e localfi_artifact_rollback_release_id=20260911-abc123 \
  --tags rollback
```
