import importlib.util
import json
import py_compile
import shutil
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BuildScriptTest(unittest.TestCase):
    def test_build_script_compiles_with_python3(self):
        py_compile.compile(str(ROOT / "build.py"), doraise=True)

    def test_config_keeps_linkease_identity_and_declares_full_artifacts(self):
        config = json.loads((ROOT / "config.json.js").read_text(encoding="utf-8"))

        self.assertEqual(config["module"], "linkease")
        self.assertEqual(config["home_url"], "Module_linkease.asp")
        self.assertEqual(
            config["full_artifact_url"],
            "https://github.com/linkease/linkease-desktop/releases/download/prebuild/linkease-asus-full-arm64-v3.0.0.tar.gz",
        )
        self.assertEqual(
            config["full_artifact_sha256"],
            "6ae7ddbe28ca07e9e2a51476b0ae7ffdef1d1fa3d4f9b48260be700c1fff0833",
        )

    def test_build_module_can_stage_full_artifacts_from_directory(self):
        spec = importlib.util.spec_from_file_location("linkease_build", ROOT / "build.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp) / "repo"
            artifact_dir = Path(temp) / "artifact"
            temp_root.mkdir()
            artifact_dir.mkdir()

            shutil.copy2(ROOT / "config.json.js", temp_root / "config.json.js")
            shutil.copytree(
                ROOT / "linkease",
                temp_root / "linkease",
                ignore=shutil.ignore_patterns("bin", "kaiplus"),
            )
            (temp_root / "linkease" / "bin").mkdir()

            (artifact_dir / "linkease-desktop").write_text("desktop", encoding="utf-8")
            (artifact_dir / "apptunnel-client").write_text("apptunnel", encoding="utf-8")
            script_dir = artifact_dir / "kaiplus" / "defaults" / "router" / "scripts"
            script_dir.mkdir(parents=True)
            (script_dir / "start.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (artifact_dir / "kaiplus" / "bin").mkdir()
            (artifact_dir / "kaiplus" / "bin" / "kaiplus_bin").write_text("kai", encoding="utf-8")

            conf = module.build_module(root=temp_root, artifact_dir=artifact_dir, skip_download=True)

            self.assertEqual(conf["module"], "linkease")
            for binary in ("linkease-desktop", "apptunnel-client"):
                staged = temp_root / "linkease" / "bin" / binary
                self.assertTrue(staged.is_file())
                self.assertTrue(staged.stat().st_mode & stat.S_IXUSR)
            self.assertTrue((temp_root / "linkease" / "kaiplus" / "bin" / "kaiplus_bin").is_file())
            self.assertTrue(
                (temp_root / "linkease" / "kaiplus" / "defaults" / "router" / "scripts" / "start.sh").stat().st_mode
                & stat.S_IXUSR
            )

            with tarfile.open(temp_root / "linkease.tar.gz", "r:gz") as tf:
                names = set(tf.getnames())

            self.assertIn("linkease/bin/linkease-desktop", names)
            self.assertIn("linkease/bin/apptunnel-client", names)
            self.assertIn("linkease/kaiplus/bin/kaiplus_bin", names)
            self.assertIn("linkease/kaiplus/defaults/router/scripts/start.sh", names)


if __name__ == "__main__":
    unittest.main()
