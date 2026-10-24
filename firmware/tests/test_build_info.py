"""PC-only integration checks for Git-derived MicroPython build information."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare_firmware", ROOT / "tools/prepare_firmware.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildInfoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        (self.root / "firmware").mkdir()
        (self.root / "firmware/main.py").write_text("print('test')\n")
        (self.root / ".gitignore").write_text("/work/\n/.venv/\n")
        self.git("add", ".")
        self.git("commit", "-qm", "initial")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args],
                                       text=True, stderr=subprocess.PIPE).strip()

    def test_no_tag_and_generated_files_do_not_dirty_repository(self):
        version, sha, count, dirty = builder.metadata(self.root)
        self.assertEqual((version, count, dirty), ("0.0.0-dev", "1", False))
        self.assertEqual(sha, self.git("rev-parse", "--short=8", "HEAD"))
        output = builder.prepare(self.root)
        data = {}
        exec((output / "build_info.py").read_text(), data)
        self.assertEqual(data["BUILD_GIT_SHA"], sha)
        self.assertFalse(data["BUILD_DIRTY"])
        self.assertEqual((output / "main.py").read_text(), "print('test')\n")
        self.assertFalse(builder.metadata(self.root)[3])
        (output / "obsolete.py").write_text("pass\n")
        builder.prepare(self.root)
        self.assertFalse((output / "obsolete.py").exists())

    def test_semantic_tag_and_commits_after_release(self):
        self.git("tag", "v1.2.3")
        (self.root / "firmware/main.py").write_text("print('updated')\n")
        self.git("add", "firmware/main.py")
        self.git("commit", "-qm", "update")
        self.git("tag", "notes")  # Non-semantic tags must not hide a valid release.
        self.assertEqual(builder.metadata(self.root)[0], "1.2.3")
        self.assertEqual(builder.metadata(self.root)[2:], ("2", False))

    def test_dirty_includes_modified_and_untracked_sources(self):
        (self.root / "firmware/main.py").write_text("pass\n")
        self.assertTrue(builder.metadata(self.root)[3])
        self.git("checkout", "--", "firmware/main.py")
        (self.root / "firmware/new_driver.py").write_text("pass\n")
        self.assertTrue(builder.metadata(self.root)[3])

    def test_without_git_fails(self):
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaises(subprocess.CalledProcessError):
                builder.metadata(Path(path))


if __name__ == "__main__":
    unittest.main()
