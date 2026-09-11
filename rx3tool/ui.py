"""Consistent, plain console output for people following the setup."""
import shlex
import sys


class Failure(Exception):
    """An expected problem with a message the user can act on."""

    def __init__(self, message, hint=None):
        super().__init__(message)
        self.hint = hint


def say(*parts):
    print(*parts, flush=True)


def stage(title):
    say()
    say(f'== {title}')


def ok(message):
    say(f'  [ OK ] {message}')


def warn(message, hint=None):
    say(f'  [WARN] {message}')
    if hint:
        for line in hint.splitlines():
            say(f'         {line}')


def fail(message, hint=None):
    say(f'  [FAIL] {message}')
    if hint:
        for line in hint.splitlines():
            say(f'         {line}')


def info(message):
    say(f'         {message}')


def quote(argv):
    return ' '.join(shlex.quote(str(a)) for a in argv)


def show_command(argv, privileged=False, dry_run=False):
    prefix = '[dry-run] ' if dry_run else ''
    tag = 'sudo ' if privileged else ''
    say(f'  {prefix}$ {tag}{quote(argv)}')


def progress(label, done, total, last=[None]):
    """Print coarse progress without flooding logs when output is not a TTY."""
    if total:
        percent = min(100, int(done * 100 / total))
        step = 1 if sys.stdout.isatty() else 10
        bucket = percent // step
        if last[0] == (label, bucket):
            return
        last[0] = (label, bucket)
        text = f'  {label}: {done / 1048576:.1f} / {total / 1048576:.1f} MiB ({percent}%)'
    else:
        bucket = done // (16 * 1048576)
        if last[0] == (label, bucket):
            return
        last[0] = (label, bucket)
        text = f'  {label}: {done / 1048576:.1f} MiB'
    if sys.stdout.isatty():
        end = '\n' if total and done >= total else '\r'
        print(text.ljust(70), end=end, flush=True)
    else:
        print(text, flush=True)
