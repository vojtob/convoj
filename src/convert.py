import logging
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import re
from typing import Callable, NamedTuple

logger = logging.getLogger(__name__)

_IS_WINDOWS = (os.name == 'nt')

def _tool_cmd(env_var, default_win, default_linux):
    """
    Resolve command for an external tool.
    Priority: env variable (may contain arguments, e.g. "xvfb-run drawio"),
    otherwise the per-OS default (list of tokens).
    """
    value = os.environ.get(env_var)
    if value:
        return shlex.split(value, posix=not _IS_WINDOWS)
    return list(default_win if _IS_WINDOWS else default_linux)

def _default_magick_linux():
    if shutil.which('magick'):
        return ['magick']
    return ['convert']  # ImageMagick 6 (e.g. Ubuntu apt) has no `magick` binary

DRAWIO_CMD   = _tool_cmd('CONVOJ_DRAWIO_CMD',
                         [r"C:\Program Files\draw.io\draw.io.exe"],
                         ['drawio'])
MAGICK_CMD   = _tool_cmd('CONVOJ_MAGICK_CMD',
                         ['magick'],
                         _default_magick_linux())
UMLET_CMD    = _tool_cmd('CONVOJ_UMLET_CMD',
                         [str(Path('C:/', 'prg', 'Umlet', 'Umlet'))],
                         ['umlet'])
MMDC_CMD     = _tool_cmd('CONVOJ_MMDC_CMD',
                         [str(Path('C:/prg/node_modules/.bin/mmdc'))],
                         ['mmdc'])
PLANTUML_JAR = os.environ.get('CONVOJ_PLANTUML_JAR',
                              'C:/prg/plantuml/plantuml-mit-1.2025.2.jar' if _IS_WINDOWS
                              else '/opt/plantuml/plantuml.jar')

def _is_up_to_date(fromfile, tofile):
    """True ak cielovy subor existuje a nie je starsi ako zdroj."""
    try:
        return os.path.getmtime(tofile) >= os.path.getmtime(fromfile)
    except OSError:
        return False  # ciel neexistuje / neda sa nacitat -> konvertuj

# adresare, ktorych subory convoj preskakuje (len dany adresar, nie jeho podadresare)
SKIP_DIRS = ('old', 'build')

def is_skipped_dir(dirpath):
    """True ak convoj subory v tomto adresari nespracuva."""
    return Path(dirpath).name in SKIP_DIRS

def is_source_name(name, extension):
    """
    True ak subor s tymto menom je zdroj s danou priponou.
    Skryte subory (napr. zalohy draw.io `.$name.drawio.bkp`) sa za zdroj nepovazuju.
    """
    return name.endswith(extension) and not name.startswith('.')

def walk_sources(source_path):
    """Prejde adresare so zdrojmi presne tak, ako ich prechadza konverzia: (dirpath, filenames)."""
    for (dirpath, _, filenames) in os.walk(source_path):
        if is_skipped_dir(dirpath):
            continue
        yield dirpath, filenames

def dest_path(ffrom, source_path, destination_path, orig_extension, new_extension):
    """Cesta k vystupu pre zdrojovy subor `ffrom` (struktura podadresarov sa zachova)."""
    rel = Path(ffrom).relative_to(source_path)
    name = rel.name[:-len(orig_extension)] + new_extension
    return str(Path(destination_path, rel.parent, name))

def file_pattern(source_path, file):
    """Regex pre prepinac -f: zhoduje sa so zaciatkom cesty bez pripony."""
    if not file:
        return None
    return str(Path(source_path, file)).replace('\\', '/')

def matches_file_pattern(pattern, path_without_suffix):
    if pattern is None:
        return True
    return re.match(pattern, str(path_without_suffix).replace('\\', '/')) is not None

def _img_walk(source_path, orig_extension, destination_path, new_extension, onfile, file, scale, force=False):
    logger.info(f'convert {str(source_path)}({orig_extension}) -> {str(destination_path)}({new_extension})')

    if Path(destination_path).resolve().is_relative_to(Path(source_path).resolve()):
        logger.error("Source path is a subpath of destination path. Aborting to prevent recursion.")
        return
    pf = file_pattern(source_path, file)
    if pf:
        logger.info(f"Must match file path {pf}")

    # walk over files in from directory
    for (dirpath, filenames) in walk_sources(source_path):
        # create destination directory
        d = Path(destination_path, Path(dirpath).relative_to(source_path))
        d.mkdir(parents=True, exist_ok=True)
        # convert files with specific extension
        for f in [f for f in filenames if is_source_name(f, orig_extension)]:
            # ffrom is original full name with path and orig extension
            ffrom = os.path.join(dirpath, f)
            if pf:
                x = Path(ffrom).with_suffix('')
                logger.debug(f"pattern {pf}")
                logger.debug(f"string {x}")
                if not matches_file_pattern(pf, x):
                    # we want to process a specific file, but not this
                    continue
                logger.debug(f"FILE matched {ffrom}")
            # fto is destination full name with path and new extension
            fto = dest_path(ffrom, source_path, destination_path, orig_extension, new_extension)
            if not force and _is_up_to_date(ffrom, fto):
                logger.debug(f'skip up-to-date {fto}')
                continue
            logger.debug(f'converting {ffrom} -> {fto}')
            onfile(ffrom, orig_extension, fto, new_extension, scale)

def onfile_convert_drawio(fromfile, orig_extension, tofile, new_extension, scale):
    cmd = [
        *DRAWIO_CMD,
        "-x", "--transparent",
        "-s", str(scale),
        "-b", "10",
        "-o", str(tofile),
        str(fromfile),
    ]
    logger.debug(cmd)
    subprocess.run(cmd)

def onfile_convert_svg(fromfile, orig_extension, tofile, new_extension, scale):
    cmd = [
        *MAGICK_CMD,
        "-density", str(int(144 * scale)),
        str(fromfile),
        str(tofile),
    ]
    logger.debug(cmd)
    subprocess.run(cmd)

def onfile_convert_umlet(fromfile, orig_extension, tofile, new_extension, scale):
    cmd = [
        *UMLET_CMD,
        "-action=convert",
        "-format=svg",
        f"-filename={fromfile}",
    ]
    logger.debug(cmd)
    subprocess.run(cmd)
    # mozno viem rovno umiestnit ak vyuzijem: java -jar umlet.jar -action=convert -format=pdf -filename=palettes/*.uxf -output=.
    # alebo podobne ako pri plantuml cmd = f'cat {fromfile} | java -jar {pupath} -tsvg -pipe > {tofile}'
    while True:
        try:
            # v povodnom nazve suboru zober miesto koncovky .uxf koncovku .svg a tento subor presun do png
            os.replace(fromfile.replace(orig_extension, new_extension), tofile)
            break
        except (PermissionError, FileNotFoundError):
            pass
   
def onfile_convert_mmd(fromfile, orig_extension, tofile, new_extension, scale):
    cmd = [
        *MMDC_CMD,
        "-w", "1400",
        "-i", str(fromfile),
        "-o", str(tofile),
    ]
    logger.debug(cmd)
    subprocess.run(cmd)

def onfile_convert_plantuml(fromfile, orig_extension, tofile, new_extension, scale):
    cmd = f'cat {fromfile} | java -jar {PLANTUML_JAR} -tsvg -pipe > {tofile}'
    logger.debug(cmd)
    subprocess.run(cmd, shell=True)

def onfile_copy(fromfile, orig_extension, tofile, new_extension, scale):
    logger.debug(f'copy {fromfile} -> {tofile}')
    shutil.copy2(fromfile, tofile)

class Step(NamedTuple):
    """
    Jeden krok konverzie: subory `src_ext` z adresara `paths.<src>`
    -> subory `dst_ext` v adresari `paths.<dst>`.
    Z tejto tabulky vychadza konverzia aj prikaz prune (mapovanie zdroj -> vystup).
    """
    commands: tuple
    src: str
    src_ext: str
    dst: str
    dst_ext: str
    onfile: Callable

STEPS = (
    # hotove obrazky sa len skopiruju
    Step(('copy', 'all'),     'sourcedir',   '.png',    'pngdir',      '.png',  onfile_copy),
    Step(('copy', 'all'),     'sourcedir',   '.webp',   'pngdir',      '.webp', onfile_copy),
    Step(('copy', 'all'),     'sourcedir',   '.ico',    'pngdir',      '.ico',  onfile_copy),
    Step(('drawio', 'all'),   'sourcedir',   '.drawio', 'pngdir',      '.png',  onfile_convert_drawio),
    Step(('svg', 'all'),      'sourcedir',   '.svg',    'pngdir',      '.png',  onfile_convert_svg),
    Step(('archi', 'all'),    'archidir',    '.svg',    'pngdir',      '.png',  onfile_convert_svg),
    # plantuml a umlet idu cez medzivystup svg
    Step(('plantuml', 'all'), 'sourcedir',   '.puml',   'plantumldir', '.svg',  onfile_convert_plantuml),
    Step(('plantuml', 'all'), 'plantumldir', '.svg',    'pngdir',      '.png',  onfile_convert_svg),
    Step(('mermaid', 'all'),  'sourcedir',   '.mmd',    'pngdir',      '.png',  onfile_convert_mmd),
    Step(('umlet', 'all'),    'sourcedir',   '.uxf',    'umletdir',    '.svg',  onfile_convert_umlet),
    Step(('umlet', 'all'),    'umletdir',    '.svg',    'pngdir',      '.png',  onfile_convert_svg),
)

def run_convert(paths, args):
    for step in STEPS:
        if args.command in step.commands:
            _img_walk(
                getattr(paths, step.src), step.src_ext,
                getattr(paths, step.dst), step.dst_ext,
                step.onfile,
                getattr(args, 'file', None), args.scale,
                getattr(args, 'force', False))
