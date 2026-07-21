from __future__ import annotations
import os
import shutil
import argparse
from pathlib import Path
from types import SimpleNamespace
import logging
from typing import Optional, Sequence

import convert

logger = logging.getLogger(__name__)

_MARKERS_PRIORITY: Sequence[str] = (".git", "build", "docs", "src_doc")

def _has_project_marker(directory: Path, markers: Sequence[str] = _MARKERS_PRIORITY) -> bool:
    """
    Return True if `directory` contains at least one marker subdirectory
    (e.g., ".git", "build", "docs", "src_doc").
    """
    return any((directory / name).is_dir() for name in markers)


def find_project_home(sourcedir: str | Path, markers: Sequence[str] = _MARKERS_PRIORITY) -> Optional[Path]:
    """
    Find and return the absolute path of the project home directory.

    The project home directory is the nearest ancestor of `sourcedir` (including itself)
    that contains at least one of the marker subdirectories, checked in priority order:
    ".git", "build", "docs", "src_doc".

    Args:
        sourcedir: A directory path that is either the project home or any of its subdirectories.
        markers: Marker directory names used to detect the project home.

    Returns:
        Absolute Path to the project home directory, or None if not found.

    Rationale for returning None:
        Not finding a project root can be a valid/expected outcome (e.g., running outside
        a repository). Returning None keeps the function side-effect free and makes it easy
        for callers to decide whether to raise, fallback, or handle gracefully.
    """
    start = Path(sourcedir).expanduser()

    # Resolve to an absolute path when possible; fall back gracefully if resolution fails.
    try:
        current = start.resolve()
    except OSError:
        current = start.absolute()

    # If a file path is passed by mistake, treat its parent as the starting directory.
    if current.exists() and current.is_file():
        current = current.parent

    # Walk upward including the starting directory.
    for directory in (current, *current.parents):
        if _has_project_marker(directory, markers=markers):
            return directory

    return None

def _project_paths(sourcedir):
    paths = SimpleNamespace()

    paths.sourcedir = find_project_home(sourcedir)
    if not paths.sourcedir:
        logger.error(f'Project home not found starting from {sourcedir}, using {sourcedir} as project home')
        paths.sourcedir = Path(sourcedir)

    paths.destdir = paths.sourcedir / 'build'

    paths.pngdir      = paths.destdir / 'img_png'
    paths.archidir    = paths.destdir / 'svg_archi'
    paths.plantumldir = paths.destdir / 'svg_plantuml'
    paths.umletdir    = paths.destdir / 'svg_umlet'

    if (paths.sourcedir / 'src_doc').exists():
        paths.sourcedir = paths.sourcedir / 'src_doc' / 'img'
    elif (paths.sourcedir / 'docs' / 'img').exists():
        paths.sourcedir = paths.sourcedir / 'docs' / 'img'

    return paths

def configure_parser():
    parser = argparse.ArgumentParser(
        prog='convoj',
        description='convert various diagram source files to PNG',
        formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument( # loglevel
        '-l', '--log', 
        help='set loglevel', 
        choices=['debug', 'info', 'warning', 'error', 'critical'], 
        default='info')
    parser.add_argument( # log2file ?
        '-g', '--log2file', 
        help='log to file True/False, default False', 
        action='store_true', default=False)
    parser.add_argument( # scale
        '-s', '--scale', 
        help='bigger dpi for posters, set scale e.g. 4', 
        type=float, default=2.0)
    parser.add_argument( # limit to this file only
        '-f', '--file', 
        help='process only this file / directory', 
        default=None)
    # parser.add_argument( # source directory, more for testing
    #     '--src', '--sourcedirectory', 
    #     help='source directory, default is current directory', 
    #     default=None)
    # parser.add_argument( # destination directory
    #     '--dest', 
    #     help='destination directory',
    #     default=None)
    parser.add_argument( # command
        'command', #nargs='?', default='all', -> toto by znamenalo, ze nemusi zadat command, default je all
        choices=['all', 'clean', 'svg', 'umlet', 'plantuml', 'mermaid', 'drawio', 'archi'],
        help="""
all:      convert all images
clean:    clean all generated files and folders
drawio:   convert drawio images, drawio images -> drawio -> png
umlet:    convert umlet images, umlet -> svg -> png
plantUML: convert plantUML images, plantUML images -> svg -> png
mermaid:  convert mermaid images, mermaid images -> png
svg:      convert  svg in source to png, could be used for svg images from archi
archi:    convert  svg in archi folder"""
    )
    
    return parser

def run_command(paths, args):
    if args.command in ['all', 'drawio', 'svg', 'archi', 'umlet', 'plantuml', 'mermaid']:
        convert.run_convert(paths, args)

    if args.command == 'clean':
        logger.debug('start cleaning')
        if paths.destdir.exists():
            shutil.rmtree(paths.destdir)
            logger.debug(f'delete {paths.destdir}')
        else:
            logger.debug(f'directory {paths.destdir} does not exist')
        logger.debug('done cleaning')


if __name__ == '__main__':
    parser = configure_parser()
    args = parser.parse_args()

    # if args.src:
    #     sourcedir = Path(args.src)
    # else:
    #     sourcedir = Path.cwd()
    sourcedir = Path.cwd()

    # set up logging
    log_level = getattr(logging, args.log.upper(), None)
    if args.log2file:
        logging.basicConfig(filename=str(sourcedir / 'convoj.log'), encoding='utf-8', level=log_level)
    else:
        logging.basicConfig(encoding='utf-8', level=log_level)

    logger.info('convoj started')
    paths = _project_paths(sourcedir)
    logger.debug(f'{args=}')
    logger.debug(f'{paths=}')
    
    logger.info(f'starts with the command {args.command}')
    run_command(paths, args)

    print('convoj finished')
