"""Command line for setting up and running RX3 on a Raspberry Pi 5."""
import argparse
import os
import subprocess
import sys

from . import REPO
from . import config as configuration
from .ui import Failure, fail, say, show_command, stage

STEPS = """\
Typical first installation on the Raspberry Pi (see README.md):
  ./rx3 doctor          check this Pi and list missing packages
  ./rx3 config init     create rx3.conf (optional; defaults are detected)
  ./rx3 setup           recover firmware, assemble runtime, build, install, validate
  ./rx3 start           start RX3            ./rx3 stop    stop it again
"""


def build(config, dry_run=False):
    from .assemble import read_marker
    say(f'Building the compatibility helpers into {config.build}')
    env = dict(os.environ, RX3_BUILD=str(config.build), RX3_ALSA_CARD=config.get('audio', 'card'))
    commands = [['sh', str(REPO / 'build.sh'), 'native']]
    if read_marker(config.runtime) is not None:
        commands.append(['sh', str(REPO / 'build.sh'), 'shim', str(config.runtime)])
    else:
        say(f'  The 32-bit player shim links against the assembled runtime, which is not in '
            f'{config.runtime} yet.')
        say('  Only the Pi-side helpers are built now; run ./rx3 assemble, then ./rx3 build again.')
    for command in commands:
        show_command(command, dry_run=dry_run)
        if not dry_run and subprocess.run(command, env=env).returncode != 0:
            raise Failure('The build failed (see the messages above)',
                          'Run ./rx3 doctor to check the build prerequisites.')
    if len(commands) == 1:
        return False
    say('\nNext step: ./rx3 install')
    return True


def selftest(verbose=False):
    """Offline tests: no firmware, network, hardware, sudo or running player."""
    import unittest
    stage('Python unit tests (tests/)')
    suite = unittest.defaultTestLoader.discover(str(REPO / 'tests'), top_level_dir=str(REPO))
    result = unittest.TextTestRunner(verbosity=2 if verbose else 1).run(suite)
    failures = 0 if result.wasSuccessful() else 1
    stage('Existing replay tests')
    for name in ('test-navigation.py', 'test-pad-mapping.py', 'test-held-pads.py', 'test-shift-jog.py',
                 'test-grid-jog.py', 'test-midi-reconnect.py', 'test-touch-recovery.py'):
        code = subprocess.run([sys.executable, str(REPO / name)], cwd=str(REPO),
                              capture_output=not verbose).returncode
        say(f'  {"pass" if code == 0 else "FAIL"}  {name}')
        failures += code != 0
    stage('C unit tests (host build)')
    import tempfile
    with tempfile.TemporaryDirectory(prefix='rx3-selftest-') as out:
        env = dict(os.environ, RX3_BUILD=out)
        if subprocess.run(['sh', str(REPO / 'build.sh'), 'native'], env=env,
                          capture_output=not verbose).returncode:
            say('  FAIL  sh build.sh native (run ./rx3 doctor --stage build)')
            failures += 1
        else:
            for name in ('test-frame-exchange', 'test-frame-scale', 'test-mixer-layout', 'test-mixer-state',
                         'test-tempo-step', 'test-tempo-input', 'test-pad-bank', 'test-pad-intent',
                         'test-audio-recovery'):
                result = subprocess.run([os.path.join(out, name)], capture_output=True, text=True)
                code = result.returncode
                if code:
                    say(f'  {name} exit {code}: {result.stdout}{result.stderr}')
                say(f'  {"pass" if code == 0 else "FAIL"}  {name}')
                failures += code != 0
    say('\n' + ('All offline tests passed.' if not failures else f'{failures} test group(s) failed.'))
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='./rx3', description=__doc__, epilog=STEPS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config', help='settings file (default: rx3.conf beside this tool)')
    parser.add_argument('--set', action='append', default=[], metavar='SECTION.KEY=VALUE',
                        help='override one setting, e.g. --set usb.uuid=1234-ABCD')
    commands = parser.add_subparsers(dest='command', metavar='COMMAND')

    def command(name, help_text):
        sub = commands.add_parser(name, help=help_text, description=help_text)
        return sub

    doctor = command('doctor', 'check prerequisites, configuration, runtime and devices (read-only)')
    doctor.add_argument('--stage', action='append', choices=('recover', 'build', 'runtime', 'devices'),
                        help='check only these stages (repeatable)')
    cfg = command('config', 'show the effective settings or create rx3.conf')
    cfg.add_argument('action', nargs='?', choices=('show', 'init'), default='show')
    cfg.add_argument('--force', action='store_true', help='with init: replace an existing rx3.conf')
    recover = command('recover', 'download and verify the official RX3 1.19 files, recover the images')
    recover.add_argument('--from', dest='directories', action='append', default=[], metavar='DIR',
                         help='folder that already holds the official ZIP files (any file names)')
    recover.add_argument('--file', dest='files', action='append', default=[], metavar='ZIP',
                         help='an official ZIP file downloaded elsewhere (repeatable)')
    recover.add_argument('--offline', action='store_true', help='never download; use local files only')
    recover.add_argument('--keep-intermediate', action='store_true', help='keep the decrypted ISO image')
    recover.add_argument('--force', action='store_true', help='redo every stage even if verified')
    recover.add_argument('--dry-run', action='store_true', help='show what would happen')
    assemble = command('assemble', 'create or repair the RX3 runtime directory from the recovered images')
    assemble.add_argument('--repair', action='store_true', help='rewrite every firmware file')
    assemble.add_argument('--dry-run', action='store_true')
    m = command('mapping', 'fetch the pinned public FLX6 mapping, or check your configured XML')
    m.add_argument('--offline', action='store_true')
    m.add_argument('--dry-run', action='store_true')
    b = command('build', 'build the display/touch helpers and the 32-bit player shim')
    b.add_argument('--dry-run', action='store_true')
    install = command('install', 'install the patched player and the shim into the runtime')
    install.add_argument('--dry-run', action='store_true')
    command('validate', 'check the assembled runtime (read-only)')
    setup = command('setup', 'run recover, assemble, build, install and validate in order')
    setup.add_argument('--from', dest='directories', action='append', default=[], metavar='DIR')
    setup.add_argument('--file', dest='files', action='append', default=[], metavar='ZIP')
    setup.add_argument('--offline', action='store_true')
    setup.add_argument('--dry-run', action='store_true')
    start = command('start', 'start the player, display, touch and MIDI helpers')
    start.add_argument('--dry-run', action='store_true')
    stop = command('stop', 'stop RX3 and release the controller, display and mounts')
    stop.add_argument('--keep-mounts', action='store_true', help='leave the runtime mounts in place')
    stop.add_argument('--dry-run', action='store_true')
    command('status', 'show which RX3 processes and mounts are active')
    selftest_parser = command('selftest', 'run the offline tests (no firmware or hardware needed)')
    selftest_parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    try:
        return run(args) or 0
    except Failure as error:
        say()
        fail(str(error), error.hint)
        return 1
    except (OSError, subprocess.SubprocessError) as error:
        fail(str(error), "Check the path/permissions and the command output above; run ./rx3 doctor.")
        return 1
    except KeyboardInterrupt:
        say('\nInterrupted. Run the same command again to continue; finished steps are kept.')
        return 130


def run(args):
    if args.command == 'selftest':
        return selftest(args.verbose)
    config = configuration.load(args.config, args.set,
                                allow_missing=args.command == "config" and args.action == "init")
    if args.command == 'doctor':
        from .doctor import Doctor, STAGES
        return Doctor(config, tuple(args.stage) if args.stage else STAGES).run()
    if args.command == 'config':
        return config_command(config, args)
    config.require_valid()
    if args.command == 'recover':
        from .recover import Recovery
        Recovery(config, args.files, args.directories, args.dry_run, args.keep_intermediate,
                 args.offline).run(args.force)
    elif args.command == 'assemble':
        from .assemble import Assembler
        Assembler(config, args.dry_run, args.repair).run()
    elif args.command == 'mapping':
        from .mapping import ensure
        ensure(config, args.offline, args.dry_run)
    elif args.command == 'build':
        build(config, args.dry_run)
    elif args.command == 'install':
        from .install import Installer
        Installer(config, args.dry_run).run()
    elif args.command == 'validate':
        from .doctor import Doctor
        return Doctor(config, ('runtime',)).run()
    elif args.command == 'setup':
        return setup(config, args)
    elif args.command in ('start', 'stop', 'status'):
        from .launch import Launcher
        launcher = Launcher(config, getattr(args, 'dry_run', False))
        if args.command == 'start':
            launcher.start()
        elif args.command == 'stop':
            launcher.stop(args.keep_mounts)
        else:
            launcher.status()
    return 0


def setup(config, args):
    from .assemble import Assembler
    from .doctor import Doctor
    from .install import Installer
    from .recover import Recovery
    if not args.dry_run and Doctor(config, ('recover', 'build')).run():
        raise Failure('Setup prerequisites are missing; fix the doctor failures first.')
    from .mapping import ensure
    ensure(config, args.offline, args.dry_run)
    stage('Step 1 of 5: recover the RX3 1.19 firmware images')
    Recovery(config, args.files, args.directories, args.dry_run, offline=args.offline).run()
    stage('Step 2 of 5: assemble the runtime')
    if args.dry_run and not (config.firmware_dir / 'images').is_dir():
        say('  [dry-run] would assemble the runtime once the images exist')
    else:
        Assembler(config, args.dry_run).run()
    stage('Step 3 of 5: build the compatibility helpers')
    built = build(config, args.dry_run)
    stage('Step 4 of 5: install the patched player and shim')
    if args.dry_run:
        say('  [dry-run] would install root/pdj/rbp-pi and lib/fbshim.so')
    elif built:
        Installer(config).run()
    stage('Step 5 of 5: validate')
    if args.dry_run:
        say('  [dry-run] would run ./rx3 validate')
        return 0
    code = Doctor(config, ('runtime',)).run()
    if code == 0:
        say('\nSetup finished. Check the devices with ./rx3 doctor, then start RX3 with ./rx3 start')
    return code


def config_command(config, args):
    target = config.source or (REPO / 'rx3.conf')
    if args.action == 'init':
        if target.exists() and not args.force:
            say(f'{target} already exists; edit it, or use --force to recreate it from rx3.conf.example')
            return 1
        text = (REPO / 'rx3.conf.example').read_text(encoding='utf-8')
        target.write_text(text, encoding='utf-8')
        say(f'Created {target}. Every value set to "auto" is detected at start; edit it only if')
        say('./rx3 doctor reports a problem or you want a different path, card or USB.')
        return 0
    problems = config.validate()
    say(f"Settings file: {config.source or 'none (built-in defaults; create one with ./rx3 config init)'}")
    for section, keys in configuration.DEFAULTS.items():
        say(f'[{section}]')
        for key in keys:
            value = config.get(section, key)
            origin = config.origin.get((section, key), 'default')
            shown = value
            if section == 'paths' or key == 'mapping':
                try:
                    shown = f'{value}  ->  {config.path(section, key)}'
                except Failure:
                    pass
            say(f'  {key} = {shown}' + ('' if origin == 'file' else f'    ({origin})'))
    detected = []
    for label, probe in (('display', config.drm_device), ('touch', config.touch_device)):
        try:
            value, how = probe()
            detected.append(f'{label}: {value} ({how})')
        except Failure as error:
            detected.append(f'{label}: not detected - {error}')
    try:
        detected.append(f'run player as uid {config.uid()} gid {config.gid()} groups '
                        f'{",".join(map(str, config.groups())) or "-"}')
    except (Failure, KeyError, ValueError) as error:
        detected.append(f'user: {error}')
    say('Detected now:')
    for line in detected:
        say(f'  {line}')
    for problem in problems:
        fail(problem)
    return 1 if problems else 0
