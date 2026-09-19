#!/usr/bin/env bash
# Optional disposable Linux integration test. Requires Docker, Ansible and ssh-keygen.
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
test_dir=$(mktemp -d)
container="omp-builder-test-$$"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  rm -rf "$test_dir"
}
trap cleanup EXIT
ssh-keygen -q -t ed25519 -N '' -f "$test_dir/key"
docker run -d --name "$container" debian:trixie-slim sleep infinity >/dev/null
docker exec "$container" apt-get update -qq
docker exec "$container" apt-get install -y -qq --no-install-recommends python3 sudo
cat > "$test_dir/inventory.yml" <<EOF
all:
  children:
    omp_builder_hosts:
      hosts:
        $container:
          ansible_connection: community.docker.docker
          ansible_python_interpreter: /usr/bin/python3
EOF
for pass in 1 2; do
  ANSIBLE_LOCAL_TEMP="$test_dir/ansible" ansible-playbook \
    -i "$test_dir/inventory.yml" "$repo/ansible/install-omp-builder.yml" \
    -e "omp_builder_owner_public_key_file=$test_dir/key.pub" \
    -e omp_builder_github_token=disposable-container-test \
    -e omp_builder_runinfra_key=disposable-container-test \
    | tee "$test_dir/pass-$pass.log"
done
if ! grep -Eq 'changed=0 .*failed=0' "$test_dir/pass-2.log"; then
  echo 'Second apply was not idempotent.' >&2
  exit 1
fi
docker exec --user omp-builder "$container" /var/lib/omp-builder/.local/bin/omp --version
docker exec --user omp-builder "$container" /var/lib/omp-builder/.local/bin/herdr integration status
# Dummy key: this checks catalog/config loading only, never live inference.
docker exec --user omp-builder --workdir /opt/omp-builder/workspace "$container" \
  /usr/local/bin/omp-builder-launch config get modelRoles --json
