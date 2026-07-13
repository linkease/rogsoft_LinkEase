import importlib.util
import json
import py_compile
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BuildScriptTest(unittest.TestCase):
    def load_build_module(self):
        spec = importlib.util.spec_from_file_location("linkease_build", ROOT / "build.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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

    def test_build_stages_full_binaries_without_kaiplus(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / "linkease", root / "linkease")
            shutil.copy2(ROOT / "config.json.js", root / "config.json.js")
            artifact = root / "artifact"
            artifact.mkdir()
            for name in ("linkease-desktop", "apptunnel-client"):
                path = artifact / name
                path.write_text("#!/bin/sh\n", encoding="utf-8")
                path.chmod(0o755)
            kaiplus = artifact / "kaiplus"
            kaiplus.mkdir()
            (kaiplus / "marker").write_text("must not be staged\n", encoding="utf-8")

            conf = module.build_module(root=root, artifact_dir=artifact)

            self.assertEqual(conf["module"], "linkease")
            self.assertTrue((root / "linkease.tar.gz").is_file())
            self.assertTrue((root / "linkease" / "bin" / "linkease-desktop").is_file())
            self.assertTrue((root / "linkease" / "bin" / "apptunnel-client").is_file())
            self.assertFalse((root / "linkease" / "kaiplus").exists())
            with tarfile.open(root / "linkease.tar.gz", "r:gz") as archive:
                members = archive.getnames()
            self.assertFalse(
                any(
                    name == "linkease/kaiplus"
                    or name.startswith("linkease/kaiplus/")
                    for name in members
                )
            )

    def test_build_module_rejects_path_traversal_module_name(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp) / "repo"
            temp_root.mkdir()
            (temp_root / "config.json.js").write_text(
                json.dumps({"module": "../escape", "version": "1.0.0"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "module must be a simple directory name"):
                module.build_module(root=temp_root, skip_download=True)

            self.assertFalse((Path(temp) / "escape.tar.gz").exists())
            self.assertFalse((temp_root / "../escape.tar.gz").resolve().exists())

    def test_build_module_raises_when_config_lacks_module(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            (temp_root / "config.json.js").write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "module"):
                module.build_module(root=temp_root, skip_download=True)

    def test_build_module_raises_when_module_directory_is_missing(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            (temp_root / "config.json.js").write_text(
                json.dumps({"module": "missing", "version": "1.0.0"}),
                encoding="utf-8",
            )

            with self.assertRaises(FileNotFoundError):
                module.build_module(root=temp_root, skip_download=True)


if __name__ == "__main__":
    unittest.main()
