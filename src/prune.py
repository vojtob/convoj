"""
prune: zmaze z imgdestdir vystupy, ku ktorym uz neexistuje zdroj.

Mapovanie zdroj -> vystup sa neurcuje natvrdo, ale z tabulky convert.STEPS:
- kroky, ktore citaju z imgsourcedir, mapuju existujuce zdroje na vystupy,
- kroky, ktore citaju z imgdestdir (svg -> png pri plantuml / umlet / archi),
  sa aplikuju na uz ocakavane vystupy, kym pribudaju nove (medzivystupy).
Vystup je osireny, ked ho neocakava ziadny krok, nezavisle od toho,
aky typ sa potom generuje.
"""
import logging
import os
from pathlib import Path

import convert

logger = logging.getLogger(__name__)


def _roots(paths):
    """Resolvnute adresare vsetkych krokov: meno atributu v `paths` -> Path."""
    names = {s.src for s in convert.STEPS} | {s.dst for s in convert.STEPS}
    return {name: Path(getattr(paths, name)).resolve() for name in names}


def expected_outputs(paths):
    """Mnozina vystupov (resolvnute cesty), ktore by convoj zo sucasnych zdrojov vytvoril."""
    roots = _roots(paths)
    out_roots = {roots[s.dst] for s in convert.STEPS}
    primary = [s for s in convert.STEPS if roots[s.src] not in out_roots]
    chained = [s for s in convert.STEPS if roots[s.src] in out_roots]

    expected = set()

    # zdroje v imgsourcedir
    for step in primary:
        src_root, dst_root = roots[step.src], roots[step.dst]
        if not src_root.is_dir():
            continue
        for dirpath, filenames in convert.walk_sources(src_root):
            for f in filenames:
                if convert.is_source_name(f, step.src_ext):
                    expected.add(Path(convert.dest_path(
                        os.path.join(dirpath, f), src_root, dst_root, step.src_ext, step.dst_ext)))

    # kroky nad vystupmi (medzivystupy), kym nieco pribuda
    changed = True
    while changed:
        changed = False
        for step in chained:
            src_root, dst_root = roots[step.src], roots[step.dst]
            for f in list(expected):
                if (f.is_relative_to(src_root)
                        and convert.is_source_name(f.name, step.src_ext)
                        and not convert.is_skipped_dir(f.parent)):
                    out = Path(convert.dest_path(f, src_root, dst_root, step.src_ext, step.dst_ext))
                    if out not in expected:
                        expected.add(out)
                        changed = True

    return expected


def _check_dirs(sourcedir, destdir):
    """Vrati chybovu hlasku, ak by prune mohol zasiahnut zdroje, inak None."""
    if destdir == sourcedir:
        return f'imgdestdir {destdir} is the same as imgsourcedir, refusing to prune'
    if destdir.is_relative_to(sourcedir):
        return f'imgdestdir {destdir} is inside imgsourcedir {sourcedir}, refusing to prune'
    if sourcedir.is_relative_to(destdir):
        return f'imgsourcedir {sourcedir} is inside imgdestdir {destdir}, refusing to prune'
    return None


def run_prune(paths, args):
    """
    Zmaze osirele vystupy a prazdne podadresare v imgdestdir.
    Vrati False, ak prune odmietol bezat (nic sa nezmazalo).
    """
    dry_run = getattr(args, 'dry_run', False)
    prefix = '[dry-run] ' if dry_run else ''

    sourcedir = Path(paths.sourcedir).resolve()
    destdir = Path(paths.destdir).resolve()

    error = _check_dirs(sourcedir, destdir)
    if error:
        logger.error(error)
        return False
    if not destdir.is_dir():
        logger.info(f'directory {destdir} does not exist, nothing to prune')
        return True

    expected = expected_outputs(paths)
    out_exts = {s.dst_ext for s in convert.STEPS}
    pattern = convert.file_pattern(sourcedir, getattr(args, 'file', None))
    if pattern:
        logger.info(f'Must match file path {pattern}')

    removed = set()
    nfiles = ndirs = 0

    # zdola nahor, aby sa po zmazani suborov dali zmazat aj prazdne adresare;
    # os.walk symlinky na adresare neprechadza
    for dirpath, _, filenames in os.walk(destdir, topdown=False):
        d = Path(dirpath)
        rel_dir = d.relative_to(destdir)

        for name in filenames:
            p = d / name
            if p.is_symlink():
                logger.debug(f'skip symlink {p}')
                continue
            if name.startswith('.') or not any(name.endswith(e) for e in out_exts):
                logger.debug(f'skip unknown file {p}')
                continue
            if not convert.matches_file_pattern(pattern, (sourcedir / rel_dir / name).with_suffix('')):
                continue
            if p in expected:
                continue
            if not p.resolve().is_relative_to(destdir):
                logger.warning(f'skip {p}, resolves outside of {destdir}')
                continue
            logger.info(f'{prefix}remove orphan {p}')
            if not dry_run:
                p.unlink()
            removed.add(p)
            nfiles += 1

        # prazdny podadresar (nie samotny imgdestdir), ku ktoremu uz neexistuje zdrojovy adresar
        if d == destdir or d.is_symlink():
            continue
        source_dir = sourcedir / rel_dir
        if source_dir.is_dir() and not convert.is_skipped_dir(source_dir):
            continue  # konverzia by ho aj tak znovu vytvorila
        if not convert.matches_file_pattern(pattern, source_dir):
            continue
        if any(d / e not in removed for e in os.listdir(d)):
            continue
        logger.info(f'{prefix}remove empty dir {d}')
        if not dry_run:
            d.rmdir()
        removed.add(d)
        ndirs += 1

    logger.info(f'{prefix}pruned {nfiles} files, {ndirs} dirs')
    return True
