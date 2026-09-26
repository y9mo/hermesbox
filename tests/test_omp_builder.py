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
                        "os.environ['DEEPSEEK_API_KEY'],"
                        "os.environ['MISTRAL_API_KEY'],"
                        "os.environ['PI_CONFIG_FILES']]))\n")
        stub.chmod(0o700)

    def test_missing_or_empty_secret_fails_without_starting_omp(self):
        self.stub_omp()
        launcher = self.render("omp-builder-launch")
        for content in (None,
                        "export GH_TOKEN=''\nexport RUNINFRA_GATEWAY_KEY='runinfra'\nexport DEEPSEEK_API_KEY='deepseek'\nexport MISTRAL_API_KEY='mistral'\n",
                        "export GH_TOKEN='github'\nexport RUNINFRA_GATEWAY_KEY=''\nexport DEEPSEEK_API_KEY='deepseek'\nexport MISTRAL_API_KEY='mistral'\n",
                        "export GH_TOKEN='github'\nexport RUNINFRA_GATEWAY_KEY='runinfra'\nexport DEEPSEEK_API_KEY=''\nexport MISTRAL_API_KEY='mistral'\n",
                        "export GH_TOKEN='github'\nexport RUNINFRA_GATEWAY_KEY='runinfra'\nexport DEEPSEEK_API_KEY='deepseek'\nexport MISTRAL_API_KEY=''\n"):
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
        deepseek_key = "deepseek spaces ' quotes $HOME `touch " + str(marker) + "` $(false)"
        mistral_key = "mistral spaces ' quotes $HOME `touch " + str(marker) + "` $(false)"
        self.render("credentials.env", self.config / "credentials.env",
                    omp_builder_github_token=github_token,
                    omp_builder_runinfra_key=runinfra_key,
                    omp_builder_deepseek_key=deepseek_key,
                    omp_builder_mistral_key=mistral_key)
        launcher = self.render("omp-builder-launch")
        args = ["models", "find", "a model", "--json"]
        result = subprocess.run(["bash", "-x", launcher, *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         [args, github_token, runinfra_key, deepseek_key, mistral_key,
                          str(self.config / "config.yml")])
        self.assertNotIn(github_token, result.stderr)
        self.assertNotIn(runinfra_key, result.stderr)
        self.assertNotIn(deepseek_key, result.stderr)
        self.assertNotIn(mistral_key, result.stderr)
        self.assertFalse(marker.exists())

    def test_role_aliases_resolve_through_managed_config(self):
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        self.assertEqual(defaults["omp_builder_github_token_passwordstore_entry"],
                         "y9mo/github/pat/hermesbox")
        self.assertEqual(defaults["omp_builder_runinfra_key_passwordstore_entry"],
                         "y9mo/runinfra/apikey")
        self.assertEqual(defaults["omp_builder_deepseek_key_passwordstore_entry"],
                         "y9mo/deepseek/hermes")
        self.assertEqual(defaults["omp_builder_mistral_key_passwordstore_entry"],
                         "y9mo/mistral/hermes")
        self.values.update(defaults)
        config = yaml.safe_load(self.render("config.yml").read_text())
        agents = {file.stem: file.read_text() for file in (ROLE / "files/agents").glob("*.md")}
        variants = (("implementer", "openai", "implementer"),
                    ("implementer", "runinfra", "implementer_runinfra"),
                    ("implementer", "mistral", "implementer_mistral"),
                    ("acceptance", "deepseek", "acceptance"),
                    ("acceptance", "runinfra", "acceptance_runinfra"))
        for kind, provider, role in variants:
            name = f"{kind}-{provider}"
            agents[name] = self.render(f"{kind}-agent.md", **{
                "omp_builder_agent_name": name,
                "omp_builder_agent_provider": provider,
                "omp_builder_agent_role": role,
            }).read_text()
        for content in agents.values():
            frontmatter = yaml.safe_load(content.split("---")[1])
            alias = frontmatter["model"].removeprefix("@")
            self.assertIn(alias, config["modelRoles"])
            self.assertEqual(config["task"]["agentModelOverrides"][frontmatter["name"]], "@" + alias)
            self.assertTrue(frontmatter["blocking"])
        acceptance_deepseek = agents["acceptance-deepseek"].split("---", 2)[2]
        acceptance_runinfra = agents["acceptance-runinfra"].split("---", 2)[2]
        self.assertEqual(acceptance_deepseek, acceptance_runinfra)
        self.assertEqual(agents["implementer-openai"].split("---", 2)[2],
                         agents["implementer-mistral"].split("---", 2)[2])
        self.assertFalse(config["async"]["enabled"])
        self.assertEqual(config["task"]["maxConcurrency"], 2)
        for role in ("default", "plan"):
            self.assertEqual(config["modelRoles"][role], "openai-codex/gpt-6-luna:low")
        for role in ("architect", "reviewer"):
            self.assertEqual(config["modelRoles"][role],
                             "openai-codex/gpt-6-sol:medium")
        self.assertEqual(config["modelRoles"]["designer"],
                         "openai-codex/gpt-6-astra:low")
        self.assertEqual(config["modelRoles"]["implementer"], "openai-codex/gpt-6-luna:low")
        self.assertEqual(config["modelRoles"]["acceptance"], "deepseek/deepseek-flash:max")
        for role in ("task", "smol"):
            self.assertEqual(config["modelRoles"][role], "openai-codex/gpt-6-luna:low")
        for role in ("implementer_runinfra", "acceptance_runinfra"):
            self.assertEqual(config["modelRoles"][role], "runinfra/zai-org/GLM-5.3-Flash:max")
        self.assertEqual(config["modelRoles"]["implementer_mistral"],
                         "mistral/zai-glm-5-3:medium")
        models = yaml.safe_load(self.render("models.yml").read_text())
        deepseek = models["providers"]["deepseek"]
        self.assertEqual(deepseek["apiKey"], "DEEPSEEK_API_KEY")
        self.assertEqual(deepseek["models"][0]["id"], "deepseek-flash")
        self.assertEqual(deepseek["models"][0]["thinking"]["maxLevel"], "max")
        self.assertIn("image", deepseek["models"][0]["input"])
        mistral = models["providers"]["mistral"]
        self.assertEqual(mistral["apiKey"], "MISTRAL_API_KEY")
        self.assertEqual(mistral["models"][0]["id"], "zai-glm-5-3")
        self.assertEqual(mistral["models"][0]["input"], ["text"])

    def test_herdr_uses_persistent_worktree_directory(self):
        config = self.render("herdr.toml").read_text()
        expected = str(self.root / "worktrees")
        self.assertIn(f'directory = "{expected}"', config)

if __name__ == "__main__":
    unittest.main()
