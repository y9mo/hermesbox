"""Behavioral tests for generated OMP Builder configuration and its launcher."""
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROLE = Path(__file__).resolve().parents[1] / "ansible/roles/omp_builder"


class Helpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "home with spaces"
        self.config = self.base / "config with spaces"
        self.root = self.base / "workspace"
        for p in (self.home / ".local/bin", self.config, self.root / "workspace"):
            p.mkdir(parents=True)
        self.env = Environment(undefined=StrictUndefined)
        self.env.filters.update(quote=shlex.quote, to_json=json.dumps)
        self.values = dict(omp_builder_home=str(self.home),
                           omp_builder_config_dir=str(self.config),
                           omp_builder_root=str(self.root))

    def render(self, name, destination=None, **extra):
        text = self.env.from_string((ROLE / "templates" / (name + ".j2")).read_text()).render(
            **(self.values | extra))
        dest = destination or self.base / name
        dest.write_text(text)
        dest.chmod(0o700)
        return dest

    def stub_omp(self):
        stub = self.home / ".local/bin/omp"
        stub.write_text("#!/usr/bin/env python3\nimport json,os,sys\n"
                        "print(json.dumps([sys.argv[1:],os.environ['GH_TOKEN'],"
                        "os.environ['RUNINFRA_GATEWAY_KEY'],"
                        "os.environ['PI_CONFIG_FILES']]))\n")
        stub.chmod(0o700)

    def test_missing_or_empty_secret_fails_without_starting_omp(self):
        self.stub_omp()
        launcher = self.render("omp-builder-launch")
        for content in (None,
                        "export GH_TOKEN=''\nexport RUNINFRA_GATEWAY_KEY='runinfra'\n",
                        "export GH_TOKEN='github'\nexport RUNINFRA_GATEWAY_KEY=''\n"):
            if content is not None:
                (self.config / "credentials.env").write_text(content)
            result = subprocess.run([launcher], capture_output=True, text=True)
            self.assertEqual(result.returncode, 78)
            self.assertEqual(result.stdout, "")

    def test_secret_quoting_and_exact_argument_forwarding(self):
        self.stub_omp()
        marker = self.base / "must-not-exist"
        github_token = "github spaces ' quotes $HOME `touch " + str(marker) + "` $(false)"
        runinfra_key = "runinfra spaces ' quotes $HOME `touch " + str(marker) + "` $(false)"
        self.render("credentials.env", self.config / "credentials.env",
                    omp_builder_github_token=github_token,
                    omp_builder_runinfra_key=runinfra_key)
        launcher = self.render("omp-builder-launch")
        args = ["models", "find", "a model", "--json"]
        result = subprocess.run(["bash", "-x", launcher, *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         [args, github_token, runinfra_key, str(self.config / "config.yml")])
        self.assertNotIn(github_token, result.stderr)
        self.assertNotIn(runinfra_key, result.stderr)
        self.assertFalse(marker.exists())

    def test_role_aliases_resolve_through_managed_config(self):
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        self.assertEqual(defaults["omp_builder_github_token_passwordstore_entry"],
                         "y9mo/github/pat/hermesbox")
        self.assertEqual(defaults["omp_builder_runinfra_key_passwordstore_entry"],
                         "y9mo/runinfra/apikey")
        self.values.update(defaults)
        config = yaml.safe_load(self.render("config.yml").read_text())
        for file in (ROLE / "files/agents").glob("*.md"):
            frontmatter = yaml.safe_load(file.read_text().split("---")[1])
            alias = frontmatter["model"].removeprefix("@")
            self.assertIn(alias, config["modelRoles"])
            self.assertEqual(config["task"]["agentModelOverrides"][frontmatter["name"]], "@" + alias)
            self.assertTrue(frontmatter["blocking"])
        self.assertFalse(config["async"]["enabled"])
        self.assertEqual(config["task"]["maxConcurrency"], 2)
        self.assertTrue(config["modelRoles"]["architect"].endswith(":low"))
        self.assertTrue(config["modelRoles"]["reviewer"].endswith(":low"))
        for role in ("implementer", "acceptance", "task", "smol"):
            self.assertTrue(config["modelRoles"][role].endswith(":max"))

    def test_herdr_uses_persistent_worktree_directory(self):
        config = self.render("herdr.toml").read_text()
        expected = str(self.root / "worktrees")
        self.assertIn(f'directory = "{expected}"', config)

if __name__ == "__main__":
    unittest.main()
