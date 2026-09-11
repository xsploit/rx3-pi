"""File operations confined to one directory tree without following symlinks.

The RX3 runtime deliberately contains absolute symlinks such as
`/sbin/e2fsck -> /sbin/fsck.ext2`. They are correct inside the chroot but would
point at the host system if followed from outside. Every write below walks the
path one component at a time with O_NOFOLLOW relative to directory handles, so
a symlink in the runtime can never redirect a write, FIFO or directory onto
the host.
"""
import errno
import os
import stat
from pathlib import PurePosixPath

from .ui import Failure

DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def parts(relative):
    """Split a runtime-relative path, interpreting a leading slash inside the runtime and rejecting parent parts."""
    text = str(relative)
    if '\0' in text or '\n' in text:
        raise Failure(f'Unsafe path in runtime: {text!r}')
    pure = PurePosixPath(text)
    if pure.is_absolute():
        pure = pure.relative_to('/')
    items = [p for p in pure.parts if p not in ('', '.')]
    if not items or any(p == '..' for p in items):
        raise Failure(f'Unsafe path in runtime: {text!r}')
    return items


class Tree:
    """A directory handle used as the root for all confined operations."""

    def __init__(self, root, create=False):
        self.root = os.fspath(root)
        if create:
            os.makedirs(self.root, exist_ok=True)
        try:
            self.fd = os.open(self.root, DIR_FLAGS)
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise Failure(f'Runtime directory must not be a symlink: {self.root}')
            raise

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _parent(self, items, create):
        fd = os.dup(self.fd)
        try:
            for name in items[:-1]:
                try:
                    child = os.open(name, DIR_FLAGS, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(name, 0o755, dir_fd=fd)
                    child = os.open(name, DIR_FLAGS, dir_fd=fd)
                except OSError as error:
                    if error.errno in (errno.ELOOP, errno.ENOTDIR):
                        raise Failure(f'Refusing to follow a symlink or file inside the runtime: '
                                      f'{"/".join(items)} (at {name!r})')
                    raise
                os.close(fd)
                fd = child
            return fd
        except BaseException:
            os.close(fd)
            raise

    def lstat(self, relative):
        items = parts(relative)
        try:
            fd = self._parent(items, False)
        except FileNotFoundError:
            return None
        try:
            return os.stat(items[-1], dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        finally:
            os.close(fd)

    def mkdir(self, relative, mode=0o755):
        items = parts(relative)
        fd = self._parent(items, True)
        try:
            try:
                os.mkdir(items[-1], mode, dir_fd=fd)
            except FileExistsError:
                st = os.stat(items[-1], dir_fd=fd, follow_symlinks=False)
                if not stat.S_ISDIR(st.st_mode):
                    raise Failure(f'Expected a directory in the runtime: {relative}')
                return False
            child = os.open(items[-1], DIR_FLAGS, dir_fd=fd)
            try:
                os.fchmod(child, mode)
            finally:
                os.close(child)
            return True
        finally:
            os.close(fd)

    def chmod_dir(self, relative, mode):
        items = parts(relative)
        fd = self._parent(items, False)
        try:
            child = os.open(items[-1], DIR_FLAGS, dir_fd=fd)
            try:
                os.fchmod(child, mode)
            finally:
                os.close(child)
        finally:
            os.close(fd)

    def write(self, relative, source, mode=0o644, replace=True):
        """Atomically create a regular file from bytes or a readable stream."""
        items = parts(relative)
        fd = self._parent(items, True)
        temp = f'.{items[-1]}.rx3-partial'
        try:
            existing = self._lstat_at(fd, items[-1])
            if existing is not None and not stat.S_ISREG(existing.st_mode):
                raise Failure(f'Refusing to replace a non-regular file in the runtime: {relative}')
            if existing is not None and not replace:
                return False
            try:
                os.unlink(temp, dir_fd=fd)
            except FileNotFoundError:
                pass
            out = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                          0o600, dir_fd=fd)
            try:
                with os.fdopen(out, 'wb', closefd=False) as target:
                    if isinstance(source, (bytes, bytearray, memoryview)):
                        target.write(source)
                    else:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            target.write(block)
                os.fchmod(out, mode & 0o7777 & ~0o6000)
            finally:
                os.close(out)
            os.replace(temp, items[-1], src_dir_fd=fd, dst_dir_fd=fd)
            return True
        except BaseException:
            try:
                os.unlink(temp, dir_fd=fd)
            except OSError:
                pass
            raise
        finally:
            os.close(fd)

    def sparse_file(self, relative, size, mode=0o644):
        """Create or resize a regular file (for the emulated framebuffer)."""
        items = parts(relative)
        fd = self._parent(items, True)
        try:
            out = os.open(items[-1], os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK |
                          os.O_CLOEXEC, mode,
                          dir_fd=fd)
            try:
                st = os.fstat(out)
                if not stat.S_ISREG(st.st_mode):
                    raise Failure(f'Expected a regular file in the runtime: {relative}')
                if st.st_size != size:
                    os.ftruncate(out, size)
            finally:
                os.close(out)
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise Failure(f'Refusing to follow a symlink inside the runtime: {relative}')
            raise
        finally:
            os.close(fd)

    def symlink(self, relative, target, replace=False):
        if '\0' in target or not target:
            raise Failure(f'Unsafe symlink target for {relative}')
        items = parts(relative)
        fd = self._parent(items, True)
        try:
            existing = self._lstat_at(fd, items[-1])
            if existing is not None:
                if stat.S_ISLNK(existing.st_mode) and os.readlink(items[-1], dir_fd=fd) == target:
                    return False
                if not replace or stat.S_ISDIR(existing.st_mode):
                    raise Failure(f'Path already exists and differs from the recorded symlink: {relative}')
                os.unlink(items[-1], dir_fd=fd)
            os.symlink(target, items[-1], dir_fd=fd)
            return True
        finally:
            os.close(fd)

    def fifo(self, relative, mode=0o660):
        items = parts(relative)
        fd = self._parent(items, True)
        try:
            existing = self._lstat_at(fd, items[-1])
            if existing is not None:
                if stat.S_ISFIFO(existing.st_mode):
                    return False
                raise Failure(f'Expected a FIFO in the runtime but found another file: {relative}')
            os.mkfifo(items[-1], mode, dir_fd=fd)
            return True
        finally:
            os.close(fd)

    def rename(self, relative, new_relative):
        a, b = parts(relative), parts(new_relative)
        fa, fb = self._parent(a, False), self._parent(b, True)
        try:
            if self._lstat_at(fb, b[-1]) is not None:
                raise Failure(f'Refusing to overwrite {new_relative}')
            os.rename(a[-1], b[-1], src_dir_fd=fa, dst_dir_fd=fb)
        finally:
            os.close(fa)
            os.close(fb)

    def unlink(self, relative):
        """Remove a regular file or symlink (never a directory)."""
        items = parts(relative)
        fd = self._parent(items, False)
        try:
            existing = self._lstat_at(fd, items[-1])
            if existing is None:
                return False
            if stat.S_ISDIR(existing.st_mode):
                raise Failure(f'Refusing to remove a directory: {relative}')
            os.unlink(items[-1], dir_fd=fd)
            return True
        finally:
            os.close(fd)

    def open_read(self, relative):
        items = parts(relative)
        fd = self._parent(items, False)
        try:
            handle = os.open(items[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=fd)
            if not stat.S_ISREG(os.fstat(handle).st_mode):
                os.close(handle)
                raise Failure(f"Expected a regular file in the runtime: {relative}")
        finally:
            os.close(fd)
        return os.fdopen(handle, 'rb')

    @staticmethod
    def _lstat_at(fd, name):
        try:
            return os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return None


def real_directory_chain(root, relative):
    """True if every component of root/relative exists and none is a symlink."""
    with Tree(root) as tree:
        try:
            st = tree.lstat(relative)
        except Failure:
            return False
        return st is not None and not stat.S_ISLNK(st.st_mode)
