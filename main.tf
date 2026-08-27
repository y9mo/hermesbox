terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.57"
    }
  }
}

provider "hcloud" {}

resource "hcloud_ssh_key" "my_key" {
  name       = "my-ssh-key"
  public_key = file("~/.ssh/hetznercloud.pub")
}

resource "hcloud_server" "hermesbox" {
  name        = "hermesbox"
  image       = "debian-13"
  server_type = "cpx32"
  location    = "hel1"

  ssh_keys = [
    hcloud_ssh_key.my_key.name
  ]
}
