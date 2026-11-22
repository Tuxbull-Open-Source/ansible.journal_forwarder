#!/usr/bin/env python3
"""Exercise the real dispatcher without installing packages or using real hosts."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="journal-dispatch-", dir=os.environ.get("TMPDIR"))
        self.root = pathlib.Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.role = self.root / "roles" / "tuxbull.journal_forwarder"
        self.role.parent.mkdir()
        shutil.copytree(ROOT, self.role, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        # Keep the actual dispatcher and optional task implementations. Replace
        # other numbered tasks so this test cannot install or reconfigure anything.
        for file in (self.role / "tasks").glob("*/[0-9][0-9]_*.yml"):
            if file.name != "40_k3s_event_exporter.yml":
                file.write_text("---\n- name: Safe dispatcher stub\n  ansible.builtin.debug:\n    msg: stub\n")
        (self.role / "handlers" / "main.yml").write_text(
            "---\n- name: restart fluent-bit\n  ansible.builtin.debug:\n    msg: handler-stub\n"
        )
        (self.root / "fluent-bit.conf").write_text("[OUTPUT]\n    Name stdout\n")
        exporter = self.role / "tasks" / "rhelAll" / "40_k3s_event_exporter.yml"
        exporter.write_text(exporter.read_text().replace(
            "/etc/fluent-bit/fluent-bit.conf", str(self.root / "fluent-bit.conf")))
        self.env = os.environ.copy()
        self.env.update({"ANSIBLE_ROLES_PATH": str(self.root / "roles"),
                         "ANSIBLE_LOCAL_TEMP": str(self.root / "ansible-local"),
                         "ANSIBLE_NOCOLOR": "1", "PWD": str(self.root)})

    def run_case(self, distribution, family, enabled):
        vars_ = {"ansible_facts": {"hostname": "fixture-host"},
                 "ansible_distribution": distribution,
                 "ansible_distribution_version": "22.04" if distribution == "Ubuntu" else "9.5",
                 "ansible_distribution_major_version": "22" if distribution == "Ubuntu" else "9",
                 "ansible_os_family": family,
                 "ansible_python_interpreter": shutil.which("python3"),
                 "journal_forwarder_k3s_event_exporter_enabled": enabled,
                 "journal_forwarder_k3s_event_exporter_manifest_path": str(self.root / "event.yml"),
                 "journal_forwarder_k3s_event_exporter_log_path": str(self.root / "events.log"),
                 "journal_forwarder_k3s_event_exporter_lua_path": str(self.root / "filter.lua"),
                 "journal_forwarder_storage_path": str(self.root),
                 "graylog_gelf_host": "graylog.example.com"}
        play = [{"hosts": "localhost", "connection": "local", "gather_facts": False,
                 "become": False, "vars": vars_,
                 "roles": [{"role": "tuxbull.journal_forwarder"}]}]
        path = self.root / "case.yml"
        path.write_text(yaml.safe_dump(play, sort_keys=False))
        return subprocess.run(["ansible-playbook", "--check", "-i", "localhost,",
                                       "-e", "ansible_python_interpreter=" + shutil.which("python3"), str(path)],
                              cwd=self.root, env=self.env, capture_output=True, text=True, timeout=120)

    def test_ubuntu_disabled_reports_and_succeeds(self):
        result = self.run_case("Ubuntu", "Debian", False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not supported by this role on this platform", result.stdout)
        self.assertIn("shared/40_k3s_event_exporter.yml", result.stdout)

    def test_ubuntu_enabled_fails_clearly(self):
        result = self.run_case("Ubuntu", "Debian", True)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("not supported by this role on this platform", result.stdout)
        self.assertIn("journal_forwarder_k3s_event_exporter_enabled", result.stdout)

    def test_rocky_disabled_selects_specific_file(self):
        result = self.run_case("Rocky", "RedHat", False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("rhelAll/40_k3s_event_exporter.yml", result.stdout)
        self.assertNotIn("shared/40_k3s_event_exporter.yml", result.stdout)

    def test_rocky_enabled_selects_specific_file(self):
        result = self.run_case("Rocky", "RedHat", True)
        # Real exporter tasks run only in check mode with a temporary config path.
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("rhelAll/40_k3s_event_exporter.yml", result.stdout)
        self.assertIn("Validate optional k3s Event exporter settings", result.stdout)
        self.assertNotIn("shared/40_k3s_event_exporter.yml", result.stdout)
        self.assertNotIn("No file was found when using first_found", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
