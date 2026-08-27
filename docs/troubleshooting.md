# Troubleshooting

## Ansible cannot authenticate over SSH

If Ansible reports `Permission denied (publickey,password)`, first discover the
current public address:

```sh
ansible-inventory --host hermesbox
```

Then test SSH directly with the configured key:

```sh
ssh -i ~/.ssh/hetznercloud root@<public-ip>
```

The private key may be passphrase-protected. Load it into the SSH agent before
running Ansible:

```sh
ssh-add ~/.ssh/hetznercloud
```

On macOS, retain the passphrase in Keychain:

```sh
ssh-add --apple-use-keychain ~/.ssh/hetznercloud
```

Retry the Ansible connection check:

```sh
ansible hcloud_server_hermesbox -m ping
```

## Inventory cannot find the server

Confirm `HCLOUD_TOKEN` is present in the controller environment and inspect the
dynamic inventory:

```sh
export HCLOUD_TOKEN=...
ansible-inventory --graph
```

The token must be able to read the Hetzner project containing `hermesbox`.
