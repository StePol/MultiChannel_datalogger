"""Prepare MicroPython files with Git metadata on the PC; never access a board."""
import argparse
import re
import shutil
import subprocess
from pathlib import Path


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True,
        stderr=subprocess.PIPE,
    ).strip()


def metadata(root):
    # Fail rather than silently associate a release with unknown Git history.
    sha = git(root, "rev-parse", "--short=8", "HEAD")
    count = git(root, "rev-list", "--count", "HEAD")
    tags = [tag for tag in git(root, "tag", "--merged", "HEAD").splitlines()
            if re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag)]
    version = "0.0.0-dev"
    if tags:
        matches = [arg for tag in tags for arg in ("--match", tag)]
        tag = git(root, "describe", "--tags", "--abbrev=0", *matches, "HEAD")
        version = tag.removeprefix("v")
    dirty = bool(git(root, "status", "--porcelain", "--untracked-files=normal"))
    return version, sha, count, dirty


def prepare(root, version_override=None):
    root = Path(root).resolve()
    version, sha, count, dirty = metadata(root)
    if version_override is not None:
        if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)-dev", version_override):
            raise ValueError("Explicit version must be X.Y.Z-dev; releases use Git tags")
        version = version_override
    sources = sorted((root / "firmware").glob("*.py"))
    sources = [p for p in sources if p.name != "build_info.py"]
    if not any(p.name == "main.py" for p in sources):
        raise RuntimeError("firmware/main.py not found")
    output = root / "work" / "firmware"
    # This dedicated generated directory must not retain files removed from sources.
    if output.is_symlink():
        raise RuntimeError("work/firmware must not be a symlink")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for source in sources:
        shutil.copy2(source, output / source.name)
    (output / "build_info.py").write_text(
        "# Generated on the PC by tools/prepare_firmware.py; do not edit.\n"
        "BUILD_VERSION = {!r}\nBUILD_GIT_SHA = {!r}\n"
        "BUILD_NUMBER = {!r}\nBUILD_DIRTY = {!r}\n".format(
            version, sha, count, dirty), encoding="utf-8",
    )
    print("[BUILD INFO] version={} git={} build={}{}".format(
        version, sha, count, " dirty" if dirty else ""))
    print("Prepared files: {}".format(output))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Explicit development version, e.g. 1.0.5-dev")
    args = parser.parse_args()
    try:
        prepare(Path(__file__).resolve().parents[1], args.version)
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as error:
        raise SystemExit("Firmware preparation failed: {}".format(error))
