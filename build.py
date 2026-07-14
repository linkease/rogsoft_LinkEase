#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

import os
import json
import hashlib
import argparse
import shutil
import stat
import tarfile
import tempfile
import traceback
import urllib.request
from pathlib import Path

parent_path = os.path.dirname(os.path.realpath(__file__))
FULL_ARTIFACT_FIELDS = ("full_artifact_url", "full_artifact_sha256")
FULL_BINARY = "linkease-full"

def md5sum(full_path):
    with open(full_path, 'rb') as rf:
        return hashlib.md5(rf.read()).hexdigest()

def file_sha256(path):
    with open(path, 'rb') as rf:
        return hashlib.sha256(rf.read()).hexdigest()

def make_executable(path):
    path = Path(path)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def copy_tree(src, dst):
    src = Path(src)
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def stage_full_artifacts(module_dir, artifact_dir):
    module_dir = Path(module_dir)
    artifact_dir = Path(artifact_dir)
    bin_dir = module_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    src = artifact_dir / FULL_BINARY
    if not src.is_file():
        raise FileNotFoundError("missing full runtime binary: %s" % src)
    dst = bin_dir / FULL_BINARY
    shutil.copy2(src, dst)
    make_executable(dst)

    kaiplus_dst = module_dir / "kaiplus"
    if kaiplus_dst.exists():
        shutil.rmtree(kaiplus_dst)

def download_file(url, dest_path):
    dest_path = Path(dest_path)
    with urllib.request.urlopen(url, timeout=120) as response:
        with open(dest_path, "wb") as output:
            shutil.copyfileobj(response, output)

def extract_full_artifact(archive_path, artifact_dir):
    archive_path = Path(archive_path)
    artifact_dir = Path(artifact_dir)
    found = set()
    with tarfile.open(archive_path, "r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            binary = Path(member.name).name
            if binary != FULL_BINARY or binary in found:
                continue
            source = archive.extractfile(member)
            if source is None:
                raise FileNotFoundError("cannot extract full runtime binary: %s" % member.name)
            dst = artifact_dir / binary
            with open(dst, "wb") as output:
                shutil.copyfileobj(source, output)
            make_executable(dst)
            found.add(binary)
    if FULL_BINARY not in found:
        raise FileNotFoundError("full artifact missing runtime binary: %s" % FULL_BINARY)

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
