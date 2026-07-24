#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

import os
import json
import hashlib
import argparse
import shutil
import stat
import subprocess
import tarfile
import tempfile
import traceback
import urllib.request
from pathlib import Path

parent_path = os.path.dirname(os.path.realpath(__file__))
FULL_ARTIFACT_FIELDS = ("full_artifact_url", "full_artifact_sha256")
FULL_BINARY = "linkease-full"
RUNTIME_BINARIES = (
    "linkease-full",
    "link-ease",
    "linkremote-agent",
    "heif-converter",
    "hostlink",
)
RUNTIME_SCRIPTS = (
    "mountremote-ctl.sh",
    "mountremote-paths.sh",
    "mountremote-watch-root.sh",
)

def md5sum(full_path):
    with open(full_path, 'rb') as rf:
        return hashlib.md5(rf.read()).hexdigest()

def file_sha256(path):
    with open(path, 'rb') as rf:
        return hashlib.sha256(rf.read()).hexdigest()

def make_executable(path):
    path = Path(path)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def compress_with_upx(path):
    mode = os.environ.get("LINKEASE_UPX", "auto").strip().lower()
    if mode in ("0", "false", "no", "skip", "disabled"):
        return False
    upx = os.environ.get("UPX", "upx")
    upx_path = shutil.which(upx)
    if not upx_path:
        if mode in ("1", "required"):
            raise FileNotFoundError("upx requested but not found: %s" % upx)
        return False
    result = subprocess.run(
        [upx_path, "--best", "--lzma", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        if mode in ("1", "required"):
            raise RuntimeError(result.stdout)
        return False
    return True

def copy_tree(src, dst):
    src = Path(src)
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)

def find_runtime_artifact_root(artifact_dir):
    artifact_dir = Path(artifact_dir)
    if (artifact_dir / "bin" / FULL_BINARY).is_file():
        return artifact_dir
    if (artifact_dir / FULL_BINARY).is_file():
        return artifact_dir
    matches = [p.parent.parent for p in artifact_dir.rglob("bin/%s" % FULL_BINARY)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError("missing full runtime binary under artifact dir: %s" % artifact_dir)
    raise ValueError("ambiguous runtime artifact roots under: %s" % artifact_dir)

def stage_runtime_metadata(runtime_root, module_dir):
    runtime_root = Path(runtime_root)
    runtime_dir = Path(module_dir) / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "checksums.txt"):
        src = runtime_root / name
        if src.is_file():
            shutil.copy2(src, runtime_dir / name)

def stage_full_artifacts(module_dir, artifact_dir):
    module_dir = Path(module_dir)
    artifact_dir = find_runtime_artifact_root(artifact_dir)
    bin_dir = module_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    runtime_bin_dir = artifact_dir / "bin"
    if runtime_bin_dir.is_dir():
        for binary in RUNTIME_BINARIES:
            src = runtime_bin_dir / binary
            if not src.is_file():
                if binary == FULL_BINARY:
                    raise FileNotFoundError("missing full runtime binary: %s" % src)
                continue
            dst = bin_dir / binary
            if src.is_symlink():
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                os.symlink(os.readlink(src), dst)
            else:
                shutil.copy2(src, dst)
                make_executable(dst)
            if binary == FULL_BINARY:
                compress_with_upx(dst)

        linkmount_src = artifact_dir / "linkmount_bin"
        if linkmount_src.is_dir():
            copy_tree(linkmount_src, module_dir / "linkmount_bin")
            linkmount_bin = module_dir / "linkmount_bin" / "linkmount_bin"
            if linkmount_bin.is_file():
                make_executable(linkmount_bin)

        script_dir = module_dir / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        for script in RUNTIME_SCRIPTS:
            src = artifact_dir / "scripts" / script
            if src.is_file():
                dst = script_dir / script
                shutil.copy2(src, dst)
                make_executable(dst)
        stage_runtime_metadata(artifact_dir, module_dir)
    else:
        src = artifact_dir / FULL_BINARY
        if not src.is_file():
            raise FileNotFoundError("missing full runtime binary: %s" % src)
        dst = bin_dir / FULL_BINARY
        shutil.copy2(src, dst)
        make_executable(dst)
        compress_with_upx(dst)

    kaiplus_dst = module_dir / "kaiplus"
    if kaiplus_dst.exists():
        shutil.rmtree(kaiplus_dst)

def remove_staged_full_artifact(module_dir):
    module_dir = Path(module_dir)
    for binary in ("linkease-full", "link-ease", "linkremote-agent", "heif-converter", "hostlink"):
        path = module_dir / "bin" / binary
        if path.exists():
            path.unlink()
    for path in (module_dir / "linkmount_bin", module_dir / "runtime"):
        if path.exists():
            shutil.rmtree(path)
    for script in RUNTIME_SCRIPTS:
        path = module_dir / "scripts" / script
        if path.exists():
            path.unlink()

def backup_path(src, dst):
    src = Path(src)
    dst = Path(dst)
    if src.is_symlink():
        os.symlink(os.readlink(src), dst)
    elif src.is_dir():
        shutil.copytree(src, dst, symlinks=True)
    elif src.exists():
        shutil.copy2(src, dst)

def restore_staged_paths(module_dir, backup_dir):
    module_dir = Path(module_dir)
    backup_dir = Path(backup_dir)
    remove_staged_full_artifact(module_dir)
    for backup in backup_dir.iterdir():
        rel = Path(*backup.name.split("__"))
        target = module_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        if backup.is_symlink():
            os.symlink(os.readlink(backup), target)
        elif backup.is_dir():
            shutil.copytree(backup, target, symlinks=True)
        else:
            shutil.copy2(backup, target)

def runtime_stage_paths(module_dir):
    module_dir = Path(module_dir)
    paths = [module_dir / "bin" / binary for binary in RUNTIME_BINARIES]
    paths.extend(module_dir / path for path in ("linkmount_bin", "runtime"))
    paths.extend(module_dir / "scripts" / script for script in RUNTIME_SCRIPTS)
    return paths

def download_file(url, dest_path):
    dest_path = Path(dest_path)
    with urllib.request.urlopen(url, timeout=120) as response:
        with open(dest_path, "wb") as output:
            shutil.copyfileobj(response, output)

def extract_full_artifact(archive_path, artifact_dir):
    archive_path = Path(archive_path)
    artifact_dir = Path(artifact_dir)
    with tarfile.open(archive_path, "r:*") as archive:
        for member in archive.getmembers():
            name = Path(member.name)
            parts = name.parts
            if not parts or parts[0] in ("", ".", "..") or any(part == ".." for part in parts):
                continue
            rel = Path(*parts[1:]) if len(parts) > 1 else Path(parts[0])
            if not rel.parts:
                continue
            allowed = (
                rel == Path(FULL_BINARY)
                or rel.name in RUNTIME_BINARIES and rel.parent == Path("bin")
                or rel.parts[0] == "linkmount_bin"
                or rel.parts[0] == "scripts" and rel.name in RUNTIME_SCRIPTS
                or rel in (Path("manifest.json"), Path("checksums.txt"))
            )
            if not allowed:
                continue
            target = artifact_dir / rel
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.issym():
                if target.exists() or target.is_symlink():
                    target.unlink()
                os.symlink(member.linkname, target)
                continue
            if not member.isfile():
                continue
            source = archive.extractfile(member)
            if source is None:
                raise FileNotFoundError("cannot extract full artifact member: %s" % member.name)
            with open(target, "wb") as output:
                shutil.copyfileobj(source, output)
            if rel.name in RUNTIME_BINARIES or rel.name in RUNTIME_SCRIPTS or rel == Path("linkmount_bin/linkmount_bin"):
                make_executable(target)
    find_runtime_artifact_root(artifact_dir)

def stage_downloaded_full_artifact(module_dir, full_artifact_url, full_artifact_sha256, root):
    full_artifact_url = str(full_artifact_url or "").strip()
    full_artifact_sha256 = str(full_artifact_sha256 or "").strip().lower()
    if not full_artifact_url:
        raise ValueError("full_artifact_url is required when --artifact-dir is not provided")
    if not full_artifact_sha256:
        raise ValueError("full_artifact_sha256 is required when --artifact-dir is not provided")

    with tempfile.TemporaryDirectory(prefix=".linkease-full-", dir=str(root)) as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / "full-artifact.tar.gz"
        artifact_dir = temp_path / "artifact"
        artifact_dir.mkdir()
        download_file(full_artifact_url, archive_path)
        actual_sha256 = file_sha256(archive_path)
        if actual_sha256.lower() != full_artifact_sha256:
            raise ValueError(
                "full artifact sha256 mismatch: expected %s, got %s"
                % (full_artifact_sha256, actual_sha256)
            )
        extract_full_artifact(archive_path, artifact_dir)
        stage_full_artifacts(module_dir, artifact_dir)

def validate_module_name(module):
    module = str(module or "").strip()
    if (
        not module
        or module in (".", "..")
        or "/" in module
        or "\\" in module
        or Path(module).is_absolute()
        or Path(module).name != module
    ):
        raise ValueError("module must be a simple directory name")
    return module

def get_or_create(root=None):
    root = Path(root or parent_path)
    conf_path = root / "config.json.js"
    conf = {}
    if not conf_path.is_file():
        print("config.json.js not found，build.py is root path. auto write config.json.js")
        module_name = root.name
        conf["module"] = module_name
        conf["version"] = "0.0.1"
        conf["home_url"] = ("Module_%s.asp" % module_name)
        conf["title"] = "title of " + module_name
        conf["description"] = "description of " + module_name
    else:
        with open(conf_path, "r", encoding="utf-8") as fc:
            conf = json.loads(fc.read())
    return conf

def build_module(root=None, artifact_dir=None, full_artifact_url=None, full_artifact_sha256=None, skip_download=False):
    root = Path(root or parent_path)
    try:
        conf = get_or_create(root)
    except json.JSONDecodeError:
        print("config.json.js file format is incorrect")
        traceback.print_exc()
        raise
    if "module" not in conf:
        raise ValueError("module is not in config.json.js")
    module = validate_module_name(conf["module"])
    conf["module"] = module
    if full_artifact_url:
        conf["full_artifact_url"] = full_artifact_url
    if full_artifact_sha256:
        conf["full_artifact_sha256"] = full_artifact_sha256
    module_path = root / module
    if not module_path.is_dir():
        raise FileNotFoundError("not found %s dir，check config.json.js is module ?" % module_path)
    install_path = module_path / "install.sh"
    if not install_path.is_file():
        raise FileNotFoundError("not found %s file，check install.sh file" % install_path)
    print("build...")

    with tempfile.TemporaryDirectory(prefix=".linkease-stage-backup-", dir=str(root)) as backup_root:
        backup_dir = Path(backup_root)
        for path in runtime_stage_paths(module_path):
            if path.exists() or path.is_symlink():
                rel = path.relative_to(module_path)
                backup_path(path, backup_dir / "__".join(rel.parts))
        if artifact_dir:
            stage_full_artifacts(module_path, artifact_dir)
        elif not skip_download:
            stage_downloaded_full_artifact(
                module_path,
                conf.get("full_artifact_url"),
                conf.get("full_artifact_sha256"),
                root,
            )

        with open(module_path / "version", "w", encoding="utf-8") as fw:
            fw.write(conf["version"] + "\n")

        tar_path = root / (module + ".tar.gz")
        if tar_path.exists():
            tar_path.unlink()
        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(module_path, arcname=module)
        restore_staged_paths(module_path, backup_dir)
    conf["md5"] = md5sum(tar_path)
    conf_path = root / "config.json.js"
    with open(conf_path, "w", encoding="utf-8") as fw:
        json.dump(conf, fw, sort_keys = True, indent = 4, ensure_ascii=False)
        fw.write("\n")
    print("build done", module + ".tar.gz")
    #hook_path = os.path.join(parent_path, "backup.sh")
    #if os.path.isfile(hook_path):
    #    os.system(hook_path)
    return conf

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", help="Directory containing linkease-full")
    parser.add_argument("--full-artifact-url", help="Release artifact URL recorded into config metadata")
    parser.add_argument("--full-artifact-sha256", help="Release artifact sha256 recorded into config metadata")
    parser.add_argument("--skip-download", action="store_true", help="Skip release artifact download; useful for tests")
    args = parser.parse_args()

    build_module(
        artifact_dir=args.artifact_dir,
        full_artifact_url=args.full_artifact_url,
        full_artifact_sha256=args.full_artifact_sha256,
        skip_download=args.skip_download,
    )

if __name__ == "__main__":
    main()
