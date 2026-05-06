import logging
import os
from pathlib import Path
import subprocess
import re

logger = logging.getLogger(__name__)

# global_destination_path = None

def _img_walk(source_path, orig_extension, destination_path, new_extension, onfile, file, poster_scale):
    # global global_destination_path
    logger.info(f'convert {str(source_path)}({orig_extension}) -> {str(destination_path)}({new_extension})')

    if Path(destination_path).resolve().is_relative_to(Path(source_path).resolve()):
        logger.error("Source path is a subpath of destination path. Aborting to prevent recursion.")
        return
    if(file):
        processedFile = False
        pf = Path(source_path, file)
        pf = str(pf).replace('\\', '/')
        logger.debug(f"match file path {pf}")

    # walk over files in from directory
    for (dirpath, _, filenames) in os.walk(source_path):
        p = Path(dirpath)
        (_, tail) = os.path.split(p)
        if str(tail) == 'old':
            continue
        # create destination directory
        d = Path(dirpath.replace(str(source_path), str(destination_path)))       
        d.mkdir(parents=True, exist_ok=True)
        # convert files with specific extension
        for f in [f for f in filenames if f.endswith(orig_extension)]:          
            # ffrom is original full name with path and orig extension
            ffrom = os.path.join(dirpath, f)
            if(file):
                # if Path(ffrom).with_suffix('') != pf:
                x = str(Path(ffrom).with_suffix('')).replace('\\', '/')
                logger.debug(f"pattern {pf}")
                logger.debug(f"string {x}")
                if not re.match(pf, x):
                    # we want to process a specific file, but not this
                    # print('skip file ', imgdef['fileName'], args.file)
                    # continue
                    continue
            # fto is destination full name with path and new extension
            fto = ffrom.replace(str(source_path), str(destination_path)).replace(orig_extension, new_extension)
            onfile(ffrom, orig_extension, fto, new_extension, poster_scale)

def onfile_convert_drawio(fromfile, orig_extension, tofile, new_extension, poster_scale):
#     cmd = f'"C:\\Program Files\\draw.io\\draw.io.exe" -x --transparent -s {poster_scale} -b 10 -o "{tofile}" "{fromfile}"'
    cmd = [
        r"C:\Program Files\draw.io\draw.io.exe",
        "-x", "--transparent",
        "-s", str(poster_scale),
        "-b", "10",
        "-o", str(tofile),
        str(fromfile),
    ]
    logger.debug(cmd)
    subprocess.run(cmd)

def onfile_convert_svg(fromfile, orig_extension, tofile, new_extension, poster_scale):
#     cmd = f'magick -density {int(144 * poster_scale)} "{fromfile}" "{tofile}"'
    cmd = [
        "magick",
        "-density", str(int(144 * poster_scale)),
        str(fromfile),
        str(tofile),
    ]
    logger.debug(cmd)
    subprocess.run(cmd)

def onfile_convert_umlet(fromfile, orig_extension, tofile, new_extension, poster_scale):
    umlet_path = str(Path('C:/', 'prg', 'Umlet', 'Umlet'))
    cmd = [
        umlet_path,
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
    mmpath = str(Path('C:/prg/node_modules/.bin/mmdc'))
#     cmd = f'{mmpath} -w 1400 -i {fromfile} -o {tofile}'
    cmd = [
        mmpath,
        "-w", "1400",
        "-i", str(fromfile),
        "-o", str(tofile),
    ]
    logger.debug(cmd)
    subprocess.run(cmd)

def onfile_convert_plantuml(fromfile, orig_extension, tofile, new_extension, scale):
    pupath = str(Path('C:/prg/plantuml/plantuml-mit-1.2025.2.jar'))
    cmd = f'cat {fromfile} | java -jar {pupath} -tsvg -pipe > {tofile}'
    logger.debug(cmd)
    subprocess.run(cmd, shell=True)

def run_convert(paths, args):
    # global global_destination_path
    # global_destination_path = paths.destdir

    if (args.command=='drawio') or (args.command=='all'):
        _img_walk(
            paths.sourcedir, '.drawio', 
            paths.pngdir, '.png', 
            onfile_convert_drawio,
            getattr(args, 'file', None), args.scale)

    if (args.command=='svg') or (args.command=='all'):
        _img_walk(
            paths.sourcedir, '.svg', 
            paths.pngdir, '.png', 
            onfile_convert_svg,
            getattr(args, 'file', None), args.scale)

    if (args.command=='archi') or (args.command=='all'):
        _img_walk(
            paths.archidir, '.svg', 
            paths.pngdir, '.png', 
            onfile_convert_svg,
            getattr(args, 'file', None), args.scale)

    if (args.command=='plantuml') or (args.command=='all'):
        _img_walk(
            paths.sourcedir, '.puml', 
            paths.plantumldir, '.svg', 
            onfile_convert_plantuml,
            getattr(args, 'file', None), args.scale)
        _img_walk(
            paths.plantumldir, '.svg', 
            paths.pngdir, '.png', 
            onfile_convert_svg,
            getattr(args, 'file', None), args.scale)

    if (args.command=='mermaid') or (args.command=='all'):
        _img_walk(
            paths.sourcedir, '.mmd', 
            paths.pngdir, '.png', 
            onfile_convert_mmd,
            getattr(args, 'file', None), args.scale)

    if (args.command=='umlet') or (args.command=='all'):
        _img_walk(
            paths.sourcedir, '.uxf', 
            paths.umletdir, '.svg', 
            onfile_convert_umlet,
            getattr(args, 'file', None), args.scale)
        _img_walk(
            paths.umletdir, '.svg', 
            paths.pngdir, '.png', 
            onfile_convert_svg,
            getattr(args, 'file', None), args.scale)
