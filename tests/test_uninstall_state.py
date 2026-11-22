"""Exercise uninstall state retention with real Ansible file tasks."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = "/var/lib/fluent-bit"
VARIABLE = "journal_forwarder_purge_state_on_uninstall"
FAMILIES = ("Ubuntu", "rhelAll", "rhelAll-8")


class UninstallStateTests(unittest.TestCase):
    def test_state_is_retained_by_default(self):
        defaults = yaml.safe_load((ROOT / "defaults/main.yml").read_text())
        self.assertIs(defaults[VARIABLE], False)

    def test_each_family_purges_only_with_explicit_opt_in(self):
        executable = os.environ.get("ANSIBLE_PLAYBOOK") or shutil.which("ansible-playbook")
        self.assertIsNotNone(executable, "ansible-playbook is required")
        for family in FAMILIES:
            tasks = yaml.safe_load((ROOT / "tasks" / family / "uninstall.yml").read_text())
            purge = [task for task in tasks if task.get("ansible.builtin.file", {}).get("path") == DEFAULT_PATH]
            self.assertEqual(len(purge), 1, family)
            self.assertEqual(purge[0]["ansible.builtin.file"].get("state"), "absent")
            self.assertEqual(purge[0].get("when"), VARIABLE + " | bool")
            for task in tasks:
                self.assertNotIn(DEFAULT_PATH, task.get("loop", []), family)
            for opted_in in (False, True):
                with self.subTest(family=family, purge=opted_in), tempfile.TemporaryDirectory(prefix="forwarder-uninstall-") as tmp:
                    state = Path(tmp) / "state"
                    state.mkdir()
                    marker = state / "cursor.db"
                    marker.write_text("sentinel")
                    task = dict(purge[0])
                    task["ansible.builtin.file"] = dict(task["ansible.builtin.file"], path=str(state))
                    play = [{"hosts": "localhost", "gather_facts": False, "vars": {VARIABLE: opted_in}, "tasks": [task]}]
                    playbook = Path(tmp) / "test.yml"
                    playbook.write_text(yaml.safe_dump(play))
                    env = dict(os.environ, ANSIBLE_NOCOLOR="1", ANSIBLE_LOCAL_TEMP=str(Path(tmp) / "ansible"))
                    result = subprocess.run([executable, "-i", "localhost,", "-c", "local", str(playbook)], env=env, capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(marker.exists(), not opted_in, result.stdout)


if __name__ == "__main__":
    unittest.main()
