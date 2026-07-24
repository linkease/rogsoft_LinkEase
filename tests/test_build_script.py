import importlib.util
import json
import os
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

    def make_runtime_bundle(self, root):
        artifact = root / "artifact"
        (artifact / "bin").mkdir(parents=True)
        for name in ("linkease-full", "linkremote-agent", "heif-converter", "hostlink"):
            path = artifact / "bin" / name
            path.write_text("#!/bin/sh\n", encoding="utf-8")
            path.chmod(0o755)
        (artifact / "bin" / "link-ease").symlink_to("linkease-full")
        (artifact / "linkmount_bin" / "lib").mkdir(parents=True)
        (artifact / "linkmount_bin" / "linkmount_bin").write_text("#!/bin/sh\n", encoding="utf-8")
        (artifact / "linkmount_bin" / "linkmount_bin").chmod(0o755)
        (artifact / "linkmount_bin" / "lib" / "libexample.so").write_text("so\n", encoding="utf-8")
        (artifact / "linkmount_bin" / "lib" / "libexample.so.1").symlink_to("libexample.so")
        (artifact / "scripts").mkdir()
        for name in ("mountremote-ctl.sh", "mountremote-paths.sh", "mountremote-watch-root.sh"):
            path = artifact / "scripts" / name
            path.write_text("#!/bin/sh\n", encoding="utf-8")
            path.chmod(0o755)
        (artifact / "manifest.json").write_text("{}\n", encoding="utf-8")
        (artifact / "checksums.txt").write_text("checksums\n", encoding="utf-8")
        return artifact

    def test_build_stages_runtime_bundle_without_kaiplus(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / "linkease", root / "linkease")
            shutil.copy2(ROOT / "config.json.js", root / "config.json.js")
            artifact = self.make_runtime_bundle(root)
            kaiplus = artifact / "kaiplus"
            kaiplus.mkdir()
            (kaiplus / "marker").write_text("must not be staged\n", encoding="utf-8")

            conf = module.build_module(root=root, artifact_dir=artifact)

            self.assertEqual(conf["module"], "linkease")
            self.assertTrue((root / "linkease.tar.gz").is_file())
            self.assertFalse((root / "linkease" / "bin" / "linkease-full").exists())
            self.assertFalse((root / "linkease" / "bin" / "link-ease").exists())
            self.assertFalse((root / "linkease" / "bin" / "linkremote-agent").exists())
            self.assertFalse((root / "linkease" / "bin" / "hostlink").exists())
            self.assertFalse((root / "linkease" / "linkmount_bin").exists())
            self.assertFalse((root / "linkease" / "runtime").exists())
            self.assertFalse((root / "linkease" / "kaiplus").exists())
            with tarfile.open(root / "linkease.tar.gz", "r:gz") as archive:
                members = archive.getnames()
                self.assertIn("linkease/bin/linkease-full", members)
                self.assertIn("linkease/bin/link-ease", members)
                linkease = archive.getmember("linkease/bin/link-ease")
                self.assertTrue(linkease.issym())
                self.assertEqual(linkease.linkname, "linkease-full")
                self.assertIn("linkease/bin/linkremote-agent", members)
                self.assertIn("linkease/bin/heif-converter", members)
                self.assertIn("linkease/bin/hostlink", members)
                self.assertIn("linkease/linkmount_bin/linkmount_bin", members)
                self.assertIn("linkease/linkmount_bin/lib/libexample.so", members)
                self.assertIn("linkease/linkmount_bin/lib/libexample.so.1", members)
                symlink = archive.getmember("linkease/linkmount_bin/lib/libexample.so.1")
                self.assertTrue(symlink.issym())
                self.assertEqual(symlink.linkname, "libexample.so")
                self.assertIn("linkease/scripts/mountremote-ctl.sh", members)
                self.assertIn("linkease/runtime/manifest.json", members)
                self.assertFalse(
                    any(
                        name == "linkease/kaiplus"
                        or name.startswith("linkease/kaiplus/")
                        for name in members
                    )
                )

    def test_build_upx_compresses_full_binary_when_available(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / "linkease", root / "linkease")
            shutil.copy2(ROOT / "config.json.js", root / "config.json.js")
            artifact = root / "artifact"
            (artifact / "bin").mkdir(parents=True)
            path = artifact / "bin" / "linkease-full"
            path.write_text("#!/bin/sh\n", encoding="utf-8")
            path.chmod(0o755)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            upx = fake_bin / "upx"
            upx.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >>\"$UPX_LOG\"\n"
                "last=''\n"
                "for arg in \"$@\"; do last=\"$arg\"; done\n"
                "printf 'packed\\n' >>\"$last\"\n",
                encoding="utf-8",
            )
            upx.chmod(0o755)
            old_path = os.environ.get("PATH", "")
            old_log = os.environ.get("UPX_LOG")
            os.environ["PATH"] = f"{fake_bin}{os.pathsep}{old_path}"
            os.environ["UPX_LOG"] = str(root / "upx.log")
            try:
                module.build_module(root=root, artifact_dir=artifact)
            finally:
                os.environ["PATH"] = old_path
                if old_log is None:
                    os.environ.pop("UPX_LOG", None)
                else:
                    os.environ["UPX_LOG"] = old_log

            upx_log = root / "upx.log"
            self.assertTrue(upx_log.is_file(), "build.py should invoke upx for linkease-full")
            self.assertIn("--best --lzma", upx_log.read_text(encoding="utf-8"))
            self.assertFalse((root / "linkease" / "bin" / "linkease-full").exists())
            with tarfile.open(root / "linkease.tar.gz", "r:gz") as archive:
                full_data = archive.extractfile("linkease/bin/linkease-full").read()
            self.assertTrue(full_data.endswith(b"packed\n"))

    def test_build_downloads_full_artifact_from_config_url(self):
        module = self.load_build_module()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / "linkease", root / "linkease")
            artifact_root = root / "artifact-src"
            bundle = self.make_runtime_bundle(artifact_root / "bundle")
            (artifact_root / "bundle" / "kaiplus").mkdir()
            (artifact_root / "bundle" / "kaiplus" / "marker").write_text("ignored\n", encoding="utf-8")
            archive_path = root / "full-artifact.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                archive.add(bundle, arcname="bundle")
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
                self.assertIn("linkease/bin/link-ease", members)
                self.assertIn("linkease/linkmount_bin/linkmount_bin", members)
                self.assertIn("linkease/linkmount_bin/lib/libexample.so.1", members)
                self.assertIn("linkease/scripts/mountremote-watch-root.sh", members)
                self.assertNotIn("linkease/bin/linkease-desktop", members)
                self.assertFalse(any(name.startswith("linkease/kaiplus/") for name in members))
                member = archive.getmember("linkease/linkmount_bin/lib/libexample.so.1")
                self.assertTrue(member.issym())
                self.assertEqual(member.linkname, "libexample.so")

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
