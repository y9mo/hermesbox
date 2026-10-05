#!/usr/bin/env python3
"""Pass Terraform's sensitive outputs to Ansible without printing them."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Run Ansible in check mode")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["rtk", "proxy", "terraform", "-chdir=terraform/cloudflare", "output", "-json", "ansible_vars"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    variables = json.loads(result.stdout)
    # NamedTemporaryFile uses mode 0600; the context removes it on completion.
    with tempfile.NamedTemporaryFile(mode="w", prefix="hermesbox-cloudflare-", suffix=".json") as extra_vars:
        json.dump(variables, extra_vars)
        extra_vars.flush()
        command = [
            "rtk", "proxy", "ansible-playbook", "ansible/install-cloudflare-access.yml",
            "--extra-vars", f"@{extra_vars.name}",
        ]
        if args.check:
            command.append("--check")
        subprocess.run(command, cwd=repo, check=True)


if __name__ == "__main__":
    main()
