import functools
import pathlib
import platform
import shutil
import subprocess
import sys

root = pathlib.Path(__file__).parent


def require_npm_install(function):
    """Enforce that 'node_modules' exists."""

    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        name = function.__name__.replace('_', '-')
        if not (root / 'node_modules').is_dir():
            raise EnvironmentError(f'You must run "npm install" before running "npm run {name}"')
        return function(*args, **kwargs)

    return wrapped


def clean():
    """Remove the packages installed by node and the local export directory."""

    if (root / 'node_modules').is_dir():
        shutil.rmtree(root / 'node_modules')

    if (root / 'rise/static/main.css').is_file():
        (root / 'rise/static/main.css').unlink()

    for path in (root / 'rise/static/').glob('reveal.js*'):
        shutil.rmtree(path)


@require_npm_install
def less():
    """Build main.less into main.css."""

    lessc = root / 'node_modules/.bin/lessc'
    if platform.system() == 'Windows':
        lessc = lessc.with_suffix('.cmd')

    subprocess.check_output([
        lessc,
        '--autoprefix',
        root / 'src/less/main.less',
        root / 'rise/static/main.css',
    ])


@require_npm_install
def watch_less():
    """Watch less."""

    watch = root / 'node_modules/.bin/watch'
    if platform.system() == 'Windows':
        lessc = lessc.with_suffix('.cmd')

    subprocess.check_output([
        watch,
        'npm run less',
        root / 'src/less',
    ])


@require_npm_install
def install_rise_reveal():
    """Copy the 'export' directory from rise-reveal.

    On Windows, npm doesn't truly install rise-reveal. Instead, it creates
    an NTFS link which points to ../rise-reveal. However, shutil.copy() is
    unable to traverse the NTFS link, so we point to ../rise-reveal directly.
    """

    for src in (root / '../rise-reveal/export/').glob('reveal.js*'):
        shutil.copytree(src, root / 'rise/static/' / src.name)


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        globals()[arg.replace('-', '_')]()
