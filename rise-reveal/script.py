import functools
import pathlib
import re
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


@require_npm_install
def copy():
    """Copy upstream files to a new directory."""

    if (root / 'export').is_dir():
        shutil.rmtree(root / 'export')

    # mkdir -p export
    (root / 'export').mkdir(parents=True, exist_ok=True)

    # cp -r ./node_modules/reveal.js/ ./export/reveal.js/
    shutil.copytree(root / 'node_modules/reveal.js/', root / 'export/reveal.js/')

    # cp -r ./node_modules/reveal.js-plugins/chalkboard/ ./export/reveal.js-chalkboard/'
    shutil.copytree(root / 'node_modules/reveal.js-plugins/chalkboard/', root / 'export/reveal.js-chalkboard/')


@require_npm_install
def patch_reveal_css():
    """Disable CSS definitions that affect 'html' and 'body' elements.

    Currently this just means adding /* at the beginning of line 11.
    """

    target_css = root / 'export/reveal.js/css/reveal.css'
    print(f'patching {target_css.relative_to(root)} for RISE')
    upstream_css = root / 'export/reveal.js/css/reveal.css.upstream'
    if not upstream_css.is_file():
        shutil.copy(target_css, upstream_css)

    # Read from upstream and write to target.
    text = upstream_css.read_text()
    with target_css.open('w', newline='') as file:
        for i, line in enumerate(text.splitlines(keepends=True), 1):
            if i == 11:
                file.write('/*')
            file.write(line)


@require_npm_install
def patch_notes():
    """Patch the notes plugin.

    Currently this just means adding /* at the beginning of line 11.
    """

    # Modify notes.js.
    target_js = root / 'export/reveal.js/plugin/notes/notes.js'
    print(f'patching {target_js.relative_to(root)} for RISE')
    upstream_js = root / 'export/reveal.js/plugin/notes/notes.js.patched'
    if not upstream_js.is_file():
        shutil.copy(target_js, upstream_js)
    text = upstream_js.read_text()

    # Ensure notes.js can find notes.html.
    text = text.replace('src$=', 'src*=')

    # Bind to 't' instead of 's'.
    text = text.replace("keyCode: 83", "keyCode: 84")
    text = text.replace("key: 'S'", "key: 'T'")

    with target_js.open('w', newline='') as file:
        file.write(text)

    # Modify notes.html.
    target_html = root / 'export/reveal.js/plugin/notes/notes.html'
    print(f'patching {target_html.relative_to(root)} for RISE')
    upstream_html = root / 'export/reveal.js/plugin/notes/notes.html.patched'
    if not upstream_html.is_file():
        shutil.copy(target_html, upstream_html)
    text = upstream_html.read_text()

    # Inject CSS above the layout selector.
    with target_html.open('w', newline='') as file:
        for line in text.splitlines(keepends=True):
            if 'Layout selector' in line:
                file.write('#speaker-controls>.speaker-controls-notes .inner_cell>.ctb_hideshow, \n')
                file.write('#speaker-controls>.speaker-controls-notes .inner_cell>.input_area { \n')
                file.write('    display: none; \n')
                file.write('}\n')
                file.write('\n')
            file.write(line)


@require_npm_install
def patch_reveal_themes():
    """Patch the reveal.js themes.

    When going to reveal-3.8.0 we found out that reveal's native themes
    like simple, sky, and similar, failed to have their global background
    show up in our slides.

    This script patches the original themes as shipping with reveal.js to
    fix this issue.

    *   One thing that goes wrong is when reveal tries to tweak settings
        on just the 'body' tag; these don't make it to <body> because they
        are too general and get superseded by other css in the jupyter arena
        so we replace these 'body {' definitions so they apply on
        a more specific css selector.

    *   That is still not enough: the body tag also needs background-attachment
        to be reset to fixed, somehow something defines it to 'scroll' which
        breaks it for those themes.

    """

    replacement_text = '\n'.join([
        'body.notebook_app.rise-enabled {',
        '    /* PATCHED by patch-reveal-themes.sh */',
        '    background-attachment: fixed !important;',
    ])

    for target_css in (root / 'export/reveal.js/css/theme/').glob('*.css'):
        print(f'patching theme {target_css.relative_to(root)} for RISE')
        upstream_css = target_css.with_suffix(f'{target_css.suffix}.patched')
        if not upstream_css.is_file():
            shutil.copy(target_css, upstream_css)
        text = upstream_css.read_text()
        with target_css.open('w', newline='') as file:
            file.write(re.sub(r'^body {', replacement_text, text, flags=re.MULTILINE))


@require_npm_install
def patch_chalkboard():
    """Patch chalkboard.js."""

    target_js = root / 'export/reveal.js-chalkboard/chalkboard.js'
    print(f'patching file {target_js.relative_to(root)} for RISE')
    upstream_js = root / 'export/reveal.js-chalkboard/chalkboard.js.patched'
    if not upstream_js.is_file():
        shutil.copy(target_js, upstream_js)

    patch_file = root / 'chalkboard.js.patch'
    subprocess.check_output([
        'git', 'apply', '--unsafe-paths',
        '--directory=export/reveal.js-chalkboard/',
        patch_file,
    ])


@require_npm_install
def build():
    """Build reveal.js for RISE."""

    copy()
    patch()


@require_npm_install
def patch():
    """Run all of the 'patch_' functions."""

    patch_reveal_css()
    patch_notes()
    patch_reveal_themes()
    patch_chalkboard()


def clean():
    """Remove the packages installed by node and the local export directory."""

    if (root / 'node_modules').is_dir():
        shutil.rmtree(root / 'node_modules')

    if (root / 'export').is_dir():
        shutil.rmtree(root / 'export')


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        globals()[arg.replace('-', '_')]()
