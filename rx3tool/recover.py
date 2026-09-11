"""Recover the pinned RX3 1.19 firmware images from official public downloads.

Everything is streamed with bounded memory and every stage is verified
against pinned SHA-256 values, so an interrupted or killed run can simply be
started again. The firmware key comes from AlphaTheta/Pioneer's published
GPL source package; it is written to a private file and never printed.

Outputs (all below the configured work directory):
  downloads/            the three official ZIP files (kept for re-runs)
  firmware/aes256.key   key recovered from the source package (mode 0600)
  firmware/images/      verified pdj.tar.gz, gui.tar.gz, rootfs.cramfs,
                        settings.tar.gz and release.txt
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import REPO
from .ui import Failure, fail, info, ok, progress, say, stage, warn

BUFFER = 1024 * 1024
SOURCE_PAGE = 'https://www.pioneerdj.com/en/support/open-source-code-distribution/gnu-open-source-license/'
FIRMWARE_PAGE = 'https://support.alphatheta.com/en-US/articles/4562999179673'

# RX3 1.19 is the version the patches and shim were written and tested against.
RELEASE = {
    'version': '1.19',
    'downloads': [
        {'name': 'official-source-0.zip', 'role': 'source',
         'url': 'https://files.microcms-assets.io/assets/3b9e29ce734e49babfedb3f8d1e728e3/'
                'f7f69f5f428841898c6d98f9976c23bb/A9BEE4F7-6932-4E11-8D9F-5288F5F79EC2.zip',
         'size': 209434594,
         'sha256': '0cb9277161e57e35d3fd84823a926ea0ba6a342c07817cf871dc5d286b5b0169',
         'member': 'pioneerdj_xdj_rx3.tar.bz2.00'},
        {'name': 'official-source-1.zip', 'role': 'source',
         'url': 'https://files.microcms-assets.io/assets/3b9e29ce734e49babfedb3f8d1e728e3/'
                '5b39b9d79cc747c2b31ff39e22074bad/57CB205B-D45A-4143-BC09-22D8400074C2.zip',
         'size': 43368153,
         'sha256': '6280e9e2c1c31a2d943608fde753de79c61b08f775aa063805ff84519537f484',
         'member': 'pioneerdj_xdj_rx3.tar.bz2.01'},
        {'name': 'XDJ-RX3_v119.zip', 'role': 'firmware',
         'url': 'https://downloads.support.alphatheta.com/firmwares/all-in-one-dj-systems/'
                'XDJ-RX3/XDJ-RX3_v119.zip',
         'size': 69171370,
         'sha256': 'ccef2b983ff9effed51bbf976d9679d3a1ba967e0474258023c6957e9e608f83',
         'member': 'XDJRX3.UPD'},
    ],
    'source_archive_size': 253238352,
    'key_member': 'pioneerdj_xdj_rx3/initramfs.tar.gz',
    'key_suffix': '/usr/local/pdj/aes256.key',
    'update_size': 69171216,
    'iso_size': 69171200,
    'iso_sha256': '29791419acbeb85ac42964fdbf7cf4d21254982f017da4089e3df126dd8b284a',
    'images': {
        'pdj.tar.gz': '6aafaf77e84e0565e329a01eec5738b2d54c73ffbc58aaf369e923ec18694a1e',
        'gui.tar.gz': '03dfc129137d0485d18b6605750ff66b33d561b7249f15ebf3f3e03adab36a7b',
        'rootfs.cramfs': '898e8af46b2d27b3183ac33e97e31bd0723840654c501c868521207bc12d16fd',
        'settings.tar.gz': 'ce7641f9b388fadfd602e236f63532a4f32da5d34df1aec2836f4a9c2fbcb472',
        'release.txt': '9a2aeb9e8dc23cf73946a8214e853a7a9cd6c151551b9e05f6569256ab7c799c',
    },
    'player_sha256': '60bcbd8876116bf09f0d8f747f95d7c7d3081ebd39d6fe14d56005a22f7f3b09',
}
IMAGES_SIZE = 30400000
MARKER = '.recovery-in-progress.json'


def sha256_file(path, label=None, size=None):
    digest = hashlib.sha256()
    done = 0
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(BUFFER), b''):
            digest.update(block)
            done += len(block)
            if label:
                progress(label, done, size)
    return digest.hexdigest()


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Recovery:
    def __init__(self, config, files=(), directories=(), dry_run=False, keep_intermediate=False,
                 offline=False, release=RELEASE, opener=None):
        self.config = config
        self.release = release
        self.files = [Path(f).expanduser() for f in files]
        self.directories = [Path(d).expanduser() for d in directories]
        self.dry_run = dry_run
        self.keep = keep_intermediate
        self.offline = offline
        self.downloads = config.downloads
        self.out = config.firmware_dir
        self.images = self.out / 'images'
        self.key = self.out / 'aes256.key'
        self.iso = self.out / 'XDJRX3.iso'
        self.marker = self.out / MARKER
        self.opener = opener or urllib.request.urlopen

    # -- stage bookkeeping ---------------------------------------------------
    def previous_run_report(self):
        try:
            data = json.loads(self.marker.read_text())
        except (OSError, ValueError):
            return
        if data.get('pid') and data['pid'] != os.getpid() and pid_alive(int(data['pid'])):
            raise Failure(f"Another recovery (process {data['pid']}) is still running",
                          'Wait for it to finish, or stop it before starting a new one.')
        warn(f"The previous recovery stopped during stage '{data.get('stage', 'unknown')}' "
             'without finishing.',
             'Possible causes include the system out-of-memory killer, running out of disk\n'
             'space, a closed terminal/SSH session or a power loss. This tool cannot tell which.\n'
             'To see whether Linux killed it for memory, run:\n'
             "  journalctl -k -b | grep -i -E 'out of memory|killed process'\n"
             '  (or: dmesg | grep -i -E "out of memory|killed process")\n'
             'Verified files are reused; unfinished ones are resumed or recreated.')

    def mark(self, name):
        if self.dry_run:
            return
        self.out.mkdir(parents=True, exist_ok=True)
        temp = self.marker.with_name(self.marker.name + '.tmp')
        temp.write_text(json.dumps({'pid': os.getpid(), 'stage': name, 'time': time.time()}))
        temp.replace(self.marker)

    def done(self):
        if self.dry_run:
            return
        manifest = {'version': self.release['version'], 'images': self.release['images'],
                    'player_sha256': self.release['player_sha256'], 'completed': time.time()}
        temp = self.out / 'manifest.json.tmp'
        temp.write_text(json.dumps(manifest, indent=2) + '\n')
        temp.replace(self.out / 'manifest.json')
        try:
            self.marker.unlink()
        except FileNotFoundError:
            pass

    # -- checks ----------------------------------------------------------------
    def images_verified(self, report=False):
        for name, digest in self.release['images'].items():
            path = self.images / name
            if not path.is_file() or sha256_file(path) != digest:
                if report:
                    info(f'missing or different: {path}')
                return False
        return True

    def preflight(self):
        stage('Checking recovery prerequisites')
        problems = []
        try:
            import cryptography  # noqa: F401
            ok('Python cryptography module found')
        except ImportError:
            problems.append(('Python module "cryptography" is missing',
                             'Install it: sudo apt install python3-cryptography'))
        if shutil.which('unzip') or shutil.which('7z'):
            ok('unzip or 7z found (the official source ZIPs use Deflate64)')
        else:
            problems.append(('Neither unzip nor 7z is installed', 'Install it: sudo apt install unzip'))
        if shutil.which('bsdtar') or shutil.which('7z'):
            ok('bsdtar or 7z found (reads the firmware ISO image)')
        else:
            problems.append(('Neither bsdtar nor 7z is installed',
                             'Install it: sudo apt install libarchive-tools'))
        need = self.space_needed()
        target = self.config.work
        probe = target
        while not probe.exists():
            probe = probe.parent
        free = shutil.disk_usage(probe).free
        if free < need:
            problems.append((f'Not enough free disk space at {probe}: {free / 1e6:.0f} MB free, '
                             f'about {need / 1e6:.0f} MB needed',
                             'Free some space or set [paths] work to a larger local disk.'))
        else:
            ok(f'Disk space: {free / 1e6:.0f} MB free, about {need / 1e6:.0f} MB needed at {probe}')
        available = memory_available()
        if available is not None:
            if available < 150 * 1048576:
                warn(f'Only {available / 1048576:.0f} MiB of memory is available',
                     'Recovery streams its data (about 80-100 MiB peak), but other programs may\n'
                     'push the system into the out-of-memory killer. Close the desktop/browser first.')
            else:
                ok(f'Memory available: {available / 1048576:.0f} MiB (recovery peak is about 100 MiB)')
        for message, hint in problems:
            fail(message, hint)
        if problems:
            raise Failure('Recovery prerequisites are missing (see above)')

    def space_needed(self):
        need = 0
        for item in self.release['downloads']:
            if self.find_existing(item) is None:
                partial = self.downloads / (item['name'] + '.partial')
                have = partial.stat().st_size if partial.exists() else 0
                need += item['size'] - have
        if not self.images_verified():
            if not self.iso.exists():
                need += self.release['iso_size']
            need += 2 * IMAGES_SIZE
        return need + 64 * 1048576

    # -- inputs ---------------------------------------------------------------
    def check_inputs(self):
        """Explicit --file/--from inputs must exist and be one of the official files."""
        sizes = {item['size']: item['name'] for item in self.release['downloads']}
        for path in self.files:
            if not path.exists():
                raise Failure(f'Input file not found: {path}')
            if not path.is_file():
                raise Failure(f'Input is not a regular file: {path}')
            if path.stat().st_size not in sizes:
                raise Failure(f'{path} is not one of the expected official files',
                              'Expected: ' + ', '.join(f'{n} ({s} bytes)' for s, n in sizes.items()))
        for directory in self.directories:
            if not directory.is_dir():
                raise Failure(f'--from must name a folder: {directory}')

    def candidates(self, item):
        """Yield (path, explicit) in priority order for one official download."""
        names = [item['name'], item['url'].rsplit('/', 1)[1]]
        for path in self.files:
            if path.stat().st_size == item['size']:
                yield path, True
        for directory in self.directories:
            seen = set()
            for name in names:
                if (directory / name).is_file():
                    seen.add(directory / name)
                    yield directory / name, True
            for path in sorted(directory.iterdir()):
                if path not in seen and path.is_file() and not path.name.endswith('.partial') \
                        and path.stat().st_size == item['size']:
                    yield path, True
        yield self.downloads / item['name'], False
        # Files left in the checkout by the earlier recover-firmware.py.
        yield REPO / item['name'], False

    def find_existing(self, item):
        for path, _ in self.candidates(item):
            if path.is_file() and path.stat().st_size == item['size']:
                return path
        return None

    def check_explicit(self, item, path):
        if not path.exists():
            raise Failure(f'Input file not found: {path}')
        if not path.is_file():
            raise Failure(f'Input is not a regular file: {path}')
        size = path.stat().st_size
        if size != item['size']:
            raise Failure(f'{path} is {size} bytes; the official {item["name"]} is {item["size"]} bytes',
                          'The file is incomplete or a different download. '
                          'Delete it and download again.')
        say(f'  Verifying {path} ...')
        if sha256_file(path, 'SHA-256', size) != item['sha256']:
            raise Failure(f'{path} does not match the official {item["name"]} (SHA-256 differs)',
                          'The file is corrupted or not the expected release. '
                          'Delete it and download again.')
        ok(f'Verified {path}')
        return path

    def obtain(self, item):
        for path, explicit in self.candidates(item):
            if explicit:
                return self.check_explicit(item, path)
            if path.is_file():
                if path.stat().st_size == item['size'] and sha256_file(path) == item['sha256']:
                    ok(f'Using verified download {path}')
                    return path
                if path.parent == self.downloads:
                    bad = path.with_name(path.name + '.corrupt')
                    warn(f'{path} does not match the official file; moving it to {bad.name}')
                    if not self.dry_run:
                        path.replace(bad)
        target = self.downloads / item['name']
        if self.offline:
            raise Failure(f'{item["name"]} is not available and --offline was given',
                          f'Download it from {item["url"]}\nand pass it with --from DIRECTORY.')
        if self.dry_run:
            say(f'  [dry-run] would download {item["url"]}\n            to {target}')
            return target
        return self.download(item, target)

    def download(self, item, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + '.partial')
        attempts = 0
        while True:
            attempts += 1
            start = partial.stat().st_size if partial.exists() else 0
            if start > item['size']:
                partial.unlink()
                start = 0
            try:
                if start < item['size']:
                    self._fetch(item, partial, start)
                break
            except (urllib.error.URLError, OSError, ConnectionError, TimeoutError) as error:
                if isinstance(error, urllib.error.HTTPError) and error.code in (403, 404, 410):
                    raise Failure(f'The official server no longer provides {item["url"]} '
                                  f'(HTTP {error.code})',
                                  f'Download {item["name"]} manually (see {FIRMWARE_PAGE}\n'
                                  f'or {SOURCE_PAGE}), check it matches SHA-256 {item["sha256"]},\n'
                                  'and pass its folder with: ./rx3 recover --from DIRECTORY')
                if attempts >= 4:
                    raise Failure(f'Download of {item["name"]} failed: {error}',
                                  f'Check the network connection and run the same command again; '
                                  f'the partial file {partial} will be resumed.')
                warn(f'Download interrupted ({error}); retrying in {2 * attempts} s')
                time.sleep(2 * attempts)
        say('  Verifying download ...')
        if sha256_file(partial, 'SHA-256', item['size']) != item['sha256']:
            bad = target.with_name(target.name + '.corrupt')
            partial.replace(bad)
            raise Failure(f'Downloaded {item["name"]} does not match the official SHA-256',
                          f'Saved as {bad} for inspection. Run the command again to download afresh.')
        partial.replace(target)
        ok(f'Downloaded and verified {target}')
        return target

    def _fetch(self, item, partial, start):
        headers = {'User-Agent': 'rx3-pi-setup (+https://github.com/xsploit/rx3-pi)'}
        if start:
            headers['Range'] = f'bytes={start}-'
            say(f'  Resuming {item["name"]} at {start / 1048576:.1f} MiB')
        else:
            say(f'  Downloading {item["name"]} ({item["size"] / 1048576:.0f} MiB) from {item["url"]}')
        request = urllib.request.Request(item['url'], headers=headers)
        with self.opener(request, timeout=60) as response:
            status = getattr(response, 'status', 200)
            if start and status != 206:
                start = 0
            mode = 'ab' if start else 'wb'
            done = start
            with partial.open(mode) as target:
                for block in iter(lambda: response.read(BUFFER), b''):
                    target.write(block)
                    done += len(block)
                    progress(item['name'], done, item['size'])
                    if done > item['size']:
                        raise OSError('server sent more data than expected')
        if done != item['size']:
            raise OSError(f'connection closed after {done} of {item["size"]} bytes')

    # -- key and firmware ------------------------------------------------------
    def recover_key(self, sources):
        """Stream both source-archive parts straight from their ZIPs (no joined copy)."""
        stage('Recovering the firmware key from the official source package')
        say('  Reading about 250 MB of compressed source; this can take a few minutes on a Pi.')
        if self.dry_run:
            say(f'  [dry-run] would write the key to {self.key} (mode 0600, never printed)')
            return
        openers = [lambda z=path, m=item['member']: open_zip_member(z, m)
                   for path, item in sources]
        chain = Chain(openers, 'source package', self.release['source_archive_size'])
        found = []
        try:
            with tarfile.open(fileobj=io.BufferedReader(chain, BUFFER), mode='r|bz2') as archive:
                for member in archive:
                    if member.name != self.release['key_member']:
                        continue
                    with archive.extractfile(member) as initramfs:
                        with tarfile.open(fileobj=initramfs, mode='r|gz') as inner:
                            for entry in inner:
                                if entry.isfile() and entry.name.endswith(self.release['key_suffix']):
                                    if entry.size > 65536:
                                        raise Failure('Unexpected source-package key size')
                                    with inner.extractfile(entry) as stream:
                                        found.append(stream.read(65537))
                    break
        except (tarfile.TarError, EOFError, OSError) as error:
            raise Failure(f'Could not read the official source package: {error}',
                          'Re-run the command; if it repeats, delete work/downloads/official-source-*.zip '
                          'so they are downloaded again.')
        finally:
            chain.close()
        if len(found) != 1:
            raise Failure('Expected exactly one firmware key in the source package')
        self.out.mkdir(parents=True, exist_ok=True)
        temp = self.key.with_name(self.key.name + '.partial')
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(found[0])
        os.chmod(temp, 0o600)
        temp.replace(self.key)
        ok(f'Key recovered from the public source package and saved privately to {self.key}')
        info('No device-specific key or CDJ is needed. Do not share this file.')

    def decrypt(self, firmware):
        stage('Decrypting the RX3 1.19 firmware update')
        if self.dry_run:
            say(f'  [dry-run] would write {self.iso}')
            return
        from firmware_image import crypt_stream, load_key, autoexec_iso_metadata
        partial = self.iso.with_name(self.iso.name + '.partial')
        length = self.release['update_size']
        with open_zip_member(firmware, 'XDJRX3.UPD') as source, partial.open('wb') as target:
            hashed = HashingWriter(target, 'decrypting', length - 16)
            try:
                crypt_stream(source, hashed, length - 16, load_key(self.key), True)
            except ValueError as error:
                raise Failure(f'Firmware update is incomplete or has an unexpected layout: {error}')
        with partial.open('rb') as source:
            try:
                volume = autoexec_iso_metadata(source.read(64 * 512 + 2048))
            except ValueError as error:
                partial.unlink()
                raise Failure(f'Decryption failed: {error}',
                              f'Delete {self.key} and run the command again to recover the key afresh.')
        if hashed.hexdigest() != self.release['iso_sha256']:
            partial.unlink()
            raise Failure('Decrypted firmware image does not match the known RX3 1.19 image',
                          f'Delete {self.key} and run the command again.')
        partial.replace(self.iso)
        ok(f'Decrypted and verified ISO image (volume {volume}): {self.iso}')

    def extract_images(self):
        stage('Extracting the runtime images from the firmware')
        names = [f'images/{n}' for n in self.release['images']]
        temp = self.out / '.images-partial'
        if self.dry_run:
            say(f'  [dry-run] would extract {", ".join(self.release["images"])} to {self.images}')
            return
        if temp.exists():
            shutil.rmtree(temp)
        temp.mkdir(parents=True)
        if shutil.which('bsdtar'):
            command = ['bsdtar', '-xf', str(self.iso), '-C', str(temp)] + names
        else:
            command = ['7z', 'x', '-y', '-o' + str(temp), str(self.iso)] + names
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise Failure(f'Extracting the ISO failed: {result.stderr.strip()[-400:]}')
        self.images.mkdir(parents=True, exist_ok=True)
        for name, digest in self.release['images'].items():
            path = temp / 'images' / name
            if not path.is_file() or sha256_file(path) != digest:
                raise Failure(f'Extracted {name} is missing or differs from the known 1.19 file')
            path.chmod(0o644)
            path.replace(self.images / name)
            ok(f'Verified {self.images / name}')
        shutil.rmtree(temp)

    # -- orchestration -----------------------------------------------------
    def run(self, force=False):
        say(f'Recovering RX3 {self.release["version"]} (the tested version; see README for 1.20)')
        say(f'  Downloads: {self.downloads}')
        say(f'  Output:    {self.out}')
        self.previous_run_report()
        self.check_inputs()
        if not force and self.images_verified():
            ok('Firmware images are already recovered and verified; nothing to do')
            self.done()
            return
        self.preflight()
        self.mark('download')
        stage('Obtaining the official downloads')
        paths = [(self.obtain(item), item) for item in self.release['downloads']]
        sources = [(p, i) for p, i in paths if i['role'] == 'source']
        firmware = next(p for p, i in paths if i['role'] == 'firmware')
        if force or not (self.iso.is_file() and self.iso.stat().st_size == self.release['iso_size']
                         and sha256_file(self.iso) == self.release['iso_sha256']):
            if force or not self.key.is_file() or self.key.stat().st_size == 0:
                self.mark('key')
                self.recover_key(sources)
            else:
                ok(f'Reusing previously recovered key {self.key}')
            self.mark('decrypt')
            self.decrypt(firmware)
        else:
            ok(f'Reusing verified ISO image {self.iso}')
        self.mark('extract')
        self.extract_images()
        if not self.keep and not self.dry_run and self.iso.exists():
            self.iso.unlink()
            info(f'Removed intermediate {self.iso.name} (use --keep-intermediate to keep it)')
        self.done()
        stage('Recovery complete')
        for name in self.release['images']:
            info(str(self.images / name))
        info(f'key: {self.key} (private)')
        old = legacy_leftovers()
        if old:
            say('\nFiles from the earlier recover-firmware.py are no longer used and may be deleted:')
            for path in old:
                info(str(path))
        say('\nNext step: ./rx3 assemble')


def memory_available():
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError):
        pass
    return None


class HashingWriter:
    def __init__(self, target, label, total):
        self.target, self.label, self.total = target, label, total
        self.digest = hashlib.sha256()
        self.done = 0

    def write(self, data):
        self.digest.update(data)
        self.done += len(data)
        if self.done % (4 * BUFFER) < len(data) or self.done == self.total:
            progress(self.label, self.done, self.total)
        return self.target.write(data)

    def hexdigest(self):
        return self.digest.hexdigest()


class ProcessStream(io.RawIOBase):
    """A subprocess's stdout as a stream; failure is reported on EOF."""

    def __init__(self, command, name):
        self.name = name
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def readable(self):
        return True

    def readinto(self, buffer):
        if self.process is None:
            return 0
        count = self.process.stdout.readinto(buffer)
        if not count:
            self._finish(True)
        return count

    def _finish(self, complete):
        if self.process is None:
            return
        process, self.process = self.process, None
        if not complete and process.poll() is None:
            process.terminate()
        process.stdout.close()
        error = process.stderr.read().decode(errors='replace').strip()
        process.stderr.close()
        code = process.wait()
        if complete and code:
            raise OSError(f'extracting {self.name} failed ({code}): {error[-300:]}')

    def close(self):
        try:
            self._finish(False)
        finally:
            super().close()


def open_zip_member(path, member):
    """Open one ZIP member for streaming, using unzip/7z for Deflate64."""
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as error:
        raise Failure(f'{path} is not a readable ZIP file: {error}')
    with archive:
        names = [n for n in archive.namelist() if Path(n).name == member]
        if len(names) != 1:
            raise Failure(f'{path} does not contain exactly one {member}')
        name = names[0]
        try:
            # The member keeps the underlying file open after the archive closes.
            return archive.open(name)
        except NotImplementedError:
            pass
    if shutil.which('unzip'):
        return ProcessStream(['unzip', '-p', str(path), name], name)
    if shutil.which('7z'):
        return ProcessStream(['7z', 'x', '-so', str(path), name], name)
    raise Failure('The source ZIP uses Deflate64; install unzip (sudo apt install unzip)')


class Chain(io.RawIOBase):
    """Concatenate streams produced lazily by `openers`, reporting progress."""

    def __init__(self, openers, label=None, total=None):
        self.openers = list(openers)
        self.current = None
        self.label, self.total, self.done = label, total, 0

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.current is None:
                if not self.openers:
                    return 0
                self.current = self.openers.pop(0)()
            count = self.current.readinto(buffer)
            if count:
                self.done += count
                if self.label:
                    progress(self.label, self.done, self.total)
                return count
            self.current.close()
            self.current = None

    def close(self):
        if self.current is not None:
            current, self.current = self.current, None
            current.close()
        super().close()


def legacy_leftovers():
    """Outputs of the earlier recover-firmware.py that are safe to delete later."""
    names = ['extracted', 'aes256.key', 'runtime-symlinks.json']
    return [REPO / n for n in names if (REPO / n).exists()]
