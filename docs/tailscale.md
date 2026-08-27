# Tailscale

The VPS joins the tailnet as `hermesbox`, advertises `tag:hermes`, enables
Tailscale SSH, and permits UDP port `41641` through UFW for direct connections.

## Create an OAuth credential

Use a Tailscale OAuth client instead of a long-lived auth key. The OAuth client
creates short-lived registration credentials when automation runs.

1. Open the Tailscale admin console's **Trust credentials** page.
2. Create an OAuth credential.
3. Grant **Auth Keys: Write**. Read-only access is insufficient.
4. Allow the scope tag `tag:hermes`.
5. Copy the client ID and secret; the secret is shown once.

If `tag:hermes` is unavailable in the credential form, add a tag owner to the
tailnet policy first:

```json
{
  "tagOwners": {
    "tag:hermes": ["autogroup:admin"]
  }
}
```

Export the OAuth values on the Ansible controller:

```sh
export TS_API_CLIENT_ID=...
export TS_API_CLIENT_SECRET=...
```

`TS_API_CLIENT_ID` is useful for credential testing. The playbook supplies the
client secret to `tailscale up`, which can use an OAuth client secret as auth
material.

Optional OAuth smoke test:

```sh
curl -d "client_id=${TS_API_CLIENT_ID}" \
  -d "client_secret=${TS_API_CLIENT_SECRET}" \
  https://api.tailscale.com/api/v2/oauth/token
```

## Install and enroll

```sh
ansible-playbook ansible/install-tailscale.yml
```

Override defaults when necessary:

```sh
ansible-playbook ansible/install-tailscale.yml \
  -e tailscale_hostname=hermesbox \
  -e tailscale_tag=tag:hermes \
  -e tailscale_enable_ssh=true
```

If a manually generated auth key is preferred, export it as
`TAILSCALE_AUTH_KEY`. The playbook uses that value before
`TS_API_CLIENT_SECRET`.

Continue with [Hermes installation](hermes.md).
