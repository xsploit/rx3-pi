"""Offline setup regressions. No firmware, network, sudo or hardware."""
import hashlib
import io
import json
import struct
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from rx3tool import config, system
from rx3tool.assemble import Assembler, MARKER, FORMAT, extract_tar, read_marker, write_marker
from rx3tool.cli import main
from rx3tool.cramfs import Image, MAGIC
from rx3tool.launch import Launcher, USB1, USB2
from rx3tool.mapping import ensure
from rx3tool.recover import Recovery
from rx3tool.safefs import Tree
from rx3tool.ui import Failure

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rx3 paths with spaces ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.conf = self.root / 'rx3.conf'
        self.conf.write_text('[paths]\nruntime = runtime\nstate = state\nwork = work\n')
        self.cfg = config.load(self.conf, env={})

    def test_config_precedence_and_relative_paths(self):
        c = config.load(self.conf, ['audio.card=Final'], env={'RX3_AUDIO_CARD': 'Environment'})
        self.assertEqual(c.runtime, self.root / 'runtime')
        self.assertEqual(c.get('audio', 'card'), 'Final')
        self.assertEqual(c.origin['audio', 'card'], '--set')

    def test_runtime_symlink_cannot_alias_system_directory(self):
        (self.root / 'system-alias').symlink_to('/etc', target_is_directory=True)
        c = config.load(self.conf, ['paths.runtime=system-alias'], env={})
        self.assertTrue(c.validate())

    def test_missing_build_dependencies_are_reported(self):
        from rx3tool.doctor import Doctor
        d = Doctor(self.cfg, ('build',))
        with patch('rx3tool.doctor.shutil.which', return_value=None):
            d.build_checks()
        self.assertGreater(d.failures, 0)
        self.assertIn('gcc-arm-linux-gnueabi', d.packages)

    def test_new_explicit_config_can_be_created(self):
        target = self.root / 'new.conf'
        self.assertEqual(main(['--config', str(target), 'config', 'init']), 0)
        self.assertTrue(target.is_file())
        self.assertEqual(main(['--config', str(target), 'config', 'init']), 1)

    def test_bad_config_does_not_start(self):
        for setting in ('paths.runtime=/', 'firmware.version=1.20', 'user.uid=0', 'audio.card=bad;command'):
            with self.subTest(setting=setting):
                self.assertTrue(config.load(self.conf, [setting], env={}).validate())

    def test_runtime_writes_reject_traversal_and_symlinks(self):
        outside = self.root / 'outside'; outside.mkdir()
        sentinel = outside / 'sentinel'; sentinel.write_text('safe')
        with Tree(self.cfg.runtime, create=True) as tree:
            tree.symlink('escape', str(outside))
            for path in ('../outside/sentinel', 'escape/sentinel'):
                with self.assertRaises(Failure): tree.write(path, b'changed')
            tree.symlink(MARKER, str(sentinel))
            with self.assertRaises(Failure): write_marker(self.cfg.runtime, {'format': FORMAT})
            self.assertIsNone(read_marker(self.cfg.runtime))
        self.assertEqual(sentinel.read_text(), 'safe')

    def test_interrupted_assembly_is_recognized(self):
        self.cfg.runtime.mkdir()
        write_marker(self.cfg.runtime, {'format': FORMAT, 'firmware': '1.19', 'state': 'assembling'})
        (self.cfg.runtime / 'partial-file').write_text('partial')
        with patch('rx3tool.assemble.runtime_mounts', return_value=[]), patch('rx3tool.assemble.player_pids', return_value=[]):
            Assembler(self.cfg).check_target()
        self.assertEqual(read_marker(self.cfg.runtime)['state'], 'assembling')

    def test_unmarked_runtime_is_preserved(self):
        self.cfg.runtime.mkdir(); (self.cfg.runtime / 'keep').touch()
        with self.assertRaises(Failure): Assembler(self.cfg).check_target()
        self.assertTrue((self.cfg.runtime / 'keep').exists())

    def test_tar_traversal_rejected(self):
        tar = self.root / 'bad.tar.gz'
        with tarfile.open(tar, 'w:gz') as out:
            m = tarfile.TarInfo('../../escape'); m.size = 1
            out.addfile(m, io.BytesIO(b'x'))
        with Tree(self.cfg.runtime, create=True) as tree, self.assertRaises(Failure):
            extract_tar(tar, tree, 'root')
        self.assertFalse((self.root / 'escape').exists())

    def test_truncated_cramfs_is_actionable(self):
        image = self.root / 'truncated'
        image.write_bytes(struct.pack('<III', MAGIC, 4096, 0) + bytes(64))
        with self.assertRaisesRegex(Failure, 'truncated'): Image(image)

    def test_dry_run_does_not_create_state_or_spawn(self):
        launch = Launcher(self.cfg, dry_run=True)
        with patch('rx3tool.launch.subprocess.Popen') as popen:
            with launch.lock(): launch.spawn('player', ['harmless-command'])
            popen.assert_not_called()
        self.assertFalse(self.cfg.state.exists())

    def test_start_waits_for_spawned_player_instead_of_initial_pid_scan(self):
        from unittest.mock import MagicMock
        c = config.load(self.conf, ['controller.mapping=map.xml'], env={})
        launch = Launcher(c)
        process = MagicMock(); process.poll.return_value = None
        stopped = {k: [] for k in ('player', 'display', 'touch', 'midi')}
        started = {k: [123] for k in stopped}
        with patch.object(launch, 'preflight', return_value=('/dev/dri/card0','test','/dev/input/event0','test',self.root/'map.xml')), patch.object(launch, 'prepare_mounts', return_value=False), patch.object(launch, 'helpers', side_effect=[stopped, started]), patch.object(launch, 'ensure_sudo'), patch.object(launch, 'spawn', return_value=process), patch('rx3tool.launch.Tree') as tree, patch('rx3tool.launch.time.monotonic', side_effect=[0, 1, 11]), patch('rx3tool.launch.time.sleep') as sleep, patch('rx3tool.launch.player_pids', return_value=[]):
            launch.start()
            sleep.assert_called_once_with(.5)
        self.assertGreaterEqual(process.poll.call_count, 2)

    def test_unknown_player_and_other_midi_are_not_stopped(self):
        processes = [(123, 1000, ['rbp-pi'], 'rbp-pi')]
        with patch('rx3tool.system.processes', return_value=processes), patch('rx3tool.system.process_root', return_value=None):
            self.assertEqual(system.player_pids(self.cfg.runtime), [])
        with patch('rx3tool.launch.processes', return_value=[(123, 1000, ['python3', 'flx6-rx3.py'], 'python3')]), patch('rx3tool.launch.os.getuid', return_value=1000), patch('rx3tool.launch.player_pids', return_value=[]):
            self.assertEqual(Launcher(self.cfg).helpers()['midi'], [])

    def test_sudo_monitor_is_scoped_to_runtime(self):
        argv = ['sudo', '-n', '--', 'chroot', '--userspec=1000:1000', str(self.cfg.runtime), '/bin/busybox']
        with patch('rx3tool.system.processes', return_value=[(123, 1000, argv, 'sudo')]):
            self.assertEqual(system.player_pids(self.cfg.runtime), [123])
            self.assertEqual(system.player_pids(self.root / 'other'), [])

    def test_changed_usb_preserves_local_library(self):
        (self.cfg.runtime / USB1).mkdir(parents=True)
        dst = self.cfg.runtime / USB2; dst.mkdir(parents=True)
        (dst / '.rx3-usb-uuid').write_text('aaaa-bbbb\n')
        c = config.load(self.conf, ['usb.uuid=cccc-dddd'], env={})
        with self.assertRaisesRegex(Failure, 'different USB'): Launcher(c).prepare_library()
        self.assertEqual((dst / '.rx3-usb-uuid').read_text(), 'aaaa-bbbb\n')

    def test_mapping_checksum_failure_writes_nothing(self):
        c = config.load(self.conf, ['controller.mapping=map.xml'], env={})
        with patch('rx3tool.mapping.urllib.request.urlopen', return_value=io.BytesIO(b'wrong')), self.assertRaisesRegex(Failure, 'checksum'):
            ensure(c)
        self.assertFalse((self.root / 'map.xml').exists())

    def test_recovery_rejects_wrong_input_hash(self):
        p = self.root / 'input.zip'; p.write_bytes(b'bad')
        item = {'name': 'input.zip', 'size': 3, 'sha256': hashlib.sha256(b'yes').hexdigest()}
        with self.assertRaisesRegex(Failure, 'SHA-256'): Recovery(self.cfg).check_explicit(item, p)

    def test_resume_restarts_when_server_ignores_range(self):
        data = b'whole payload'; p = self.root / 'file.partial'; p.write_bytes(b'whole')
        response = io.BytesIO(data); response.status = 200
        recovery = Recovery(self.cfg, opener=lambda *a, **k: response)
        recovery._fetch({'name': 'file', 'size': len(data), 'url': 'https://example.invalid/file'}, p, 5)
        self.assertEqual(p.read_bytes(), data)

if __name__ == '__main__': unittest.main()
