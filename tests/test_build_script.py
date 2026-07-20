import importlib.util
import json
import py_compile
import shutil
import tarfile
import tempfile
import unittest
import hashlib
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
        self.assertRegex(config["version"], r"^\d+\.\d+\.\d+$")
        self.assertTrue(config["full_artifact_url"].strip())
        self.assertRegex(config["full_artifact_sha256"], r"^[0-9a-f]{64}$")

    def test_build_stages_full_binary_without_kaiplus(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / "linkease", root / "linkease")
            shutil.copy2(ROOT / "config.json.js", root / "config.json.js")
            artifact = root / "artifact"
            artifact.mkdir()
            path = artifact / "linkease-full"
            path.write_text("#!/bin/sh\n", encoding="utf-8")
            path.chmod(0o755)
            kaiplus = artifact / "kaiplus"
            kaiplus.mkdir()
            (kaiplus / "marker").write_text("must not be staged\n", encoding="utf-8")

            conf = module.build_module(root=root, artifact_dir=artifact)

            self.assertEqual(conf["module"], "linkease")
            self.assertTrue((root / "linkease.tar.gz").is_file())
            self.assertTrue((root / "linkease" / "bin" / "linkease-full").is_file())
            self.assertFalse((root / "linkease" / "bin" / "linkease-desktop").exists())
            self.assertFalse((root / "linkease" / "bin" / "apptunnel-client").exists())
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

    def test_build_downloads_full_artifact_from_config_url(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / "linkease", root / "linkease")
            artifact_root = root / "artifact-src"
            (artifact_root / "bundle" / "bin").mkdir(parents=True)
            (artifact_root / "bundle" / "kaiplus").mkdir()
            path = artifact_root / "bundle" / "bin" / "linkease-full"
            path.write_text("#!/bin/sh\n", encoding="utf-8")
            path.chmod(0o755)
            (artifact_root / "bundle" / "kaiplus" / "marker").write_text("ignored\n", encoding="utf-8")
            archive_path = root / "full-artifact.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                archive.add(artifact_root / "bundle", arcname="bundle")
            sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            (root / "config.json.js").write_text(
                json.dumps(
                    {
                        "module": "linkease",
                        "version": "1.0.0",
                        "home_url": "Module_linkease.asp",
                        "title": "易有云",
                        "description": "test",
                        "full_artifact_url": archive_path.as_uri(),
                        "full_artifact_sha256": sha256,
                    }
                ),
                encoding="utf-8",
            )

            conf = module.build_module(root=root)

            self.assertEqual(conf["md5"], module.md5sum(root / "linkease.tar.gz"))
            with tarfile.open(root / "linkease.tar.gz", "r:gz") as archive:
                members = archive.getnames()
            self.assertIn("linkease/bin/linkease-full", members)
            self.assertNotIn("linkease/bin/linkease-desktop", members)
            self.assertNotIn("linkease/bin/apptunnel-client", members)
            self.assertFalse(any(name.startswith("linkease/kaiplus/") for name in members))

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
