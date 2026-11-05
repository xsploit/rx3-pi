"""Replay FLX4 MIDI through the shipped profile, including deck-two routing."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('flx4_bridge', ROOT / 'flx6-rx3.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class FLX4Mapping(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.now = 0.0
        self.b = bridge.Bridge(str(ROOT / 'mappings/Pioneer-DDJ-FLX4.rx3.xml'),
                               lambda *event: self.events.append(event), lambda: self.now)

    def test_both_decks_and_pad_releases(self):
        for deck, status, pads in ((1, 0x90, 0x97), (2, 0x91, 0x99)):
            for note, key in ((0x0b, 0x4101), (0x0c, 0x4102), (0x54, 0x5020),
                              (0x10, 0x410c), (0x11, 0x410d), (0x4d, 0x410e),
                              (0x58, 0x4112), (0x68, 0x410b)):
                self.events.clear()
                self.b.feed(bytes((status, note, 127, status-16, note, 0)))
                self.assertEqual(self.events, [(key, 0, deck, 0, 0., 0),
                                               (key, 2, deck, 0, 0., 0)])
            for offset, bank in ((0, 0x5040), (0x60, 0x5041), (0x20, 0x5043)):
                for pad in range(8):
                    self.events.clear()
                    self.b.feed(bytes((pads, offset+pad, 127, pads-16, offset+pad, 0)))
                    self.assertEqual(self.events, [(0x4117+pad, 0, deck, 0, 0., bank),
                                                   (0x4117+pad, 2, deck, 0, 0., bank)])

    def test_load_browse_and_high_resolution_faders(self):
        self.b.feed(bytes((0x96, 0x47, 127)))
        self.assertEqual(self.events[-1][:3], (0x4311, 0, 2))
        self.b.feed(bytes((0xb6, 0x40, 1, 0x40, 127)))
        self.assertEqual(self.events[-2:], [(0x420c, 4, 0, 1, 0., 0x4252),
                                           (0x420c, 4, 0, -1, 0., 0x4252)])
        for deck, status in ((1, 0xb0), (2, 0xb1)):
            for value, expected in ((0, 0.), (127, 1.)):
                self.b.feed(bytes((status, 0x13, value, 0x33, value)))
                self.assertEqual(self.events[-1], (0x501e, 4, deck, 0, expected, 0))

    def test_flx4_jog_resolution(self):
        self.assertEqual(self.b.jog_resolution, 720)
        for ch, status in ((1, 0xb0), (2, 0xb1)):
            self.b.feed(bytes((status, 0x22, 65)))
            self.assertEqual(self.b.jogs[ch]['total'], 1)
            self.b.jogs[ch]['total'] = 720
            self.assertEqual(self.b.pulse(ch), 1620)
        self.now = .02
        self.b.tick()
        for event in self.events:
            self.assertAlmostEqual(event[4], .125)


if __name__ == '__main__':
    unittest.main()
