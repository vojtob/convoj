"""
Testy prikazu prune. Spustenie z koreňa projektu:

    python3 -m unittest discover -s tests -v

convoj sa spusta ako CLI (subprocess), drawio a magick nahradza tests/fake_tool.py.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONVOJ = ROOT / 'src' / 'convoj.py'
FAKE_TOOL = f'{sys.executable} {Path(__file__).resolve().parent / "fake_tool.py"}'


class PruneTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.work = Path(self._tmp.name)
        self.src = self.work / 'docs' / 'img'
        self.dst = self.work / 'build' / 'img-docs'
        self.src.mkdir(parents=True)
        self.dst.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    # --- pomocne funkcie ---------------------------------------------------

    def touch(self, path, text='x'):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def convoj(self, *args, src='docs/img', dst='build/img-docs'):
        env = dict(os.environ, CONVOJ_DRAWIO_CMD=FAKE_TOOL, CONVOJ_MAGICK_CMD=FAKE_TOOL)
        return subprocess.run(
            [sys.executable, str(CONVOJ), *args[:-1], src, dst, args[-1]],
            cwd=self.work, env=env, capture_output=True, text=True)

    def prune(self, *opts, **kw):
        r = self.convoj(*opts, 'prune', **kw)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def snapshot(self, root):
        """Vsetky subory a adresare pod root s mtime (ns)."""
        return {p.relative_to(root): p.stat().st_mtime_ns for p in sorted(root.rglob('*'))}

    # --- poziadavky zo zadania -----------------------------------------------

    def test_deleted_source_removes_output_and_keeps_others_untouched(self):
        self.touch(self.src / 'a.drawio')
        self.touch(self.src / 'b.drawio')
        self.touch(self.dst / 'a.png')
        self.touch(self.dst / 'b.png')
        self.touch(self.dst / 'sub' / 'c.png')
        self.touch(self.src / 'sub' / 'c.svg')
        os.utime(self.dst / 'a.png', ns=(1_000_000_000, 1_000_000_000))
        (self.src / 'b.drawio').unlink()
        before = self.snapshot(self.dst)

        r = self.prune()

        self.assertFalse((self.dst / 'b.png').exists())
        after = self.snapshot(self.dst)
        del before[Path('b.png')]
        self.assertEqual(after, before)  # ostatne bez zmeny, vratane mtime
        self.assertIn(f'remove orphan {self.dst / "b.png"}', r.stderr)
        self.assertIn('pruned 1 files, 0 dirs', r.stderr)

    def test_renamed_source_removes_old_output_and_generation_creates_new(self):
        self.touch(self.src / 'old_name.drawio')
        r = self.convoj('drawio')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.dst / 'old_name.png').exists())

        (self.src / 'old_name.drawio').rename(self.src / 'new_name.drawio')
        self.prune()
        self.assertFalse((self.dst / 'old_name.png').exists())

        r = self.convoj('drawio')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.dst / 'new_name.png').exists())

    def test_same_name_two_source_types_one_deleted_keeps_output(self):
        for deleted, kept in (('a.drawio', 'a.svg'), ('a.svg', 'a.drawio')):
            with self.subTest(deleted=deleted):
                self.touch(self.src / kept)
                self.touch(self.dst / 'a.png')
                (self.src / deleted).unlink(missing_ok=True)
                self.prune()
                self.assertTrue((self.dst / 'a.png').exists())
                (self.src / kept).unlink()

    def test_whole_source_subdir_removed_deletes_file_and_dir(self):
        self.touch(self.dst / 'gone' / 'deeper' / 'x.png')
        self.touch(self.dst / 'gone' / 'y.png')
        r = self.prune()
        self.assertFalse((self.dst / 'gone').exists())
        self.assertTrue(self.dst.is_dir())  # samotny imgdestdir ostava
        self.assertIn('pruned 2 files, 2 dirs', r.stderr)

    def test_unknown_file_is_kept(self):
        self.touch(self.dst / 'notes.txt')
        self.touch(self.dst / 'gone' / 'readme.md')
        r = self.prune('-l', 'debug')
        self.assertTrue((self.dst / 'notes.txt').exists())
        self.assertTrue((self.dst / 'gone' / 'readme.md').exists())
        self.assertIn(f'skip unknown file {self.dst / "notes.txt"}', r.stderr)

    def test_refuses_when_dest_equals_or_is_inside_source(self):
        self.touch(self.src / 'a.png')
        self.touch(self.src / 'sub' / 'b.png')
        before = self.snapshot(self.src)
        for dst in ('docs/img', 'docs/img/sub', 'docs/img/out'):
            with self.subTest(dst=dst):
                r = self.convoj('prune', dst=dst)
                self.assertEqual(r.returncode, 1)
                self.assertIn('refusing to prune', r.stderr)
                self.assertEqual(self.snapshot(self.src), before)

    def test_refuses_when_source_is_inside_dest(self):
        self.touch(self.work / 'stale.png')
        r = self.convoj('prune', dst='.')
        self.assertEqual(r.returncode, 1)
        self.assertIn('refusing to prune', r.stderr)
        self.assertTrue((self.work / 'stale.png').exists())

    def test_dry_run_deletes_nothing(self):
        self.touch(self.dst / 'a.png')
        self.touch(self.dst / 'gone' / 'b.png')
        before = self.snapshot(self.dst)
        for opt in ('-n', '--dry-run'):
            with self.subTest(opt=opt):
                r = self.prune(opt)
                self.assertEqual(self.snapshot(self.dst), before)
                self.assertIn(f'[dry-run] remove orphan {self.dst / "a.png"}', r.stderr)
                self.assertIn(f'[dry-run] remove empty dir {self.dst / "gone"}', r.stderr)
                self.assertIn('[dry-run] pruned 2 files, 1 dirs', r.stderr)

    # --- pripady overene v kode ----------------------------------------------

    def test_intermediate_svg_is_output_of_plantuml_and_umlet(self):
        self.touch(self.src / 'seq.puml')
        self.touch(self.src / 'cls.uxf')
        for name in ('seq', 'cls', 'gone_puml'):
            self.touch(self.dst / f'{name}.svg')
            self.touch(self.dst / f'{name}.png')
        self.prune()
        for name in ('seq', 'cls'):
            self.assertTrue((self.dst / f'{name}.svg').exists())
            self.assertTrue((self.dst / f'{name}.png').exists())
        self.assertFalse((self.dst / 'gone_puml.svg').exists())
        self.assertFalse((self.dst / 'gone_puml.png').exists())

    def test_copy_type(self):
        self.touch(self.src / 'logo.png')
        self.touch(self.src / 'icon.ico')
        for name in ('logo.png', 'icon.ico', 'photo.webp', 'favicon.ico'):
            self.touch(self.dst / name)
        self.prune()
        self.assertTrue((self.dst / 'logo.png').exists())
        self.assertTrue((self.dst / 'icon.ico').exists())
        self.assertFalse((self.dst / 'photo.webp').exists())
        self.assertFalse((self.dst / 'favicon.ico').exists())

    def test_backup_and_hidden_files_are_not_sources(self):
        self.touch(self.src / '.$a.drawio.bkp')
        self.touch(self.src / 'b.drawio.bkp')
        self.touch(self.src / '.c.drawio')
        self.touch(self.dst / 'a.png')
        self.touch(self.dst / 'b.png')
        self.prune()
        self.assertFalse((self.dst / 'a.png').exists())
        self.assertFalse((self.dst / 'b.png').exists())
        # generovanie skryte zdroje tiez ignoruje
        r = self.convoj('drawio')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(list(self.dst.rglob('*.png')), [])

    def test_empty_dir_with_existing_source_dir_is_kept(self):
        (self.src / 'empty').mkdir()
        (self.dst / 'empty').mkdir()
        self.touch(self.src / 'sub' / 'x.txt')
        self.touch(self.dst / 'sub' / 'old.png')
        self.prune()
        self.assertTrue((self.dst / 'empty').is_dir())
        self.assertTrue((self.dst / 'sub').is_dir())
        self.assertFalse((self.dst / 'sub' / 'old.png').exists())

    def test_file_option_limits_prune(self):
        self.touch(self.dst / 'a.png')
        self.touch(self.dst / 'b.png')
        self.touch(self.dst / 'sub' / 'c.png')
        self.touch(self.dst / 'other' / 'd.png')
        self.prune('-f', 'a')
        self.assertFalse((self.dst / 'a.png').exists())
        self.assertTrue((self.dst / 'b.png').exists())
        self.prune('-f', 'sub')
        self.assertFalse((self.dst / 'sub').exists())
        self.assertTrue((self.dst / 'other' / 'd.png').exists())

    def test_symlinks_are_not_followed_or_removed(self):
        outside = self.work / 'outside'
        self.touch(outside / 'keep.png')
        (self.dst / 'link.png').symlink_to(outside / 'keep.png')
        (self.dst / 'linkdir').symlink_to(outside, target_is_directory=True)
        self.prune()
        self.assertTrue((self.dst / 'link.png').is_symlink())
        self.assertTrue((self.dst / 'linkdir').is_symlink())
        self.assertTrue((outside / 'keep.png').exists())

    def test_generation_keeps_subdir_structure(self):
        self.touch(self.src / 'sub' / 'deep' / 'diag.drawio')
        self.touch(self.src / 'pic.svg')
        r = self.convoj('all')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.dst / 'sub' / 'deep' / 'diag.png').exists())
        self.assertTrue((self.dst / 'pic.png').exists())
        r = self.prune()
        self.assertIn('pruned 0 files, 0 dirs', r.stderr)


if __name__ == '__main__':
    unittest.main()
