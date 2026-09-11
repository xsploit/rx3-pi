import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from firmware_image import crypt, crypt_stream
from rx3tool import recover as recovery


class RecoveryStreaming(unittest.TestCase):
    def test_cipher_matches_existing_sector_format(self):
        key = bytes(range(32))
        plain = bytes(range(256)) * 256
        expected = crypt(plain, key, False)
        encrypted = io.BytesIO()
        crypt_stream(io.BytesIO(plain), encrypted, len(plain), key, False)
        self.assertEqual(encrypted.getvalue(), expected)
        decoded = io.BytesIO()
        crypt_stream(io.BytesIO(expected), decoded, len(expected), key, True)
        self.assertEqual(decoded.getvalue(), plain)

    def test_truncated_or_unaligned_stream_rejected(self):
        for data, length in [(b'x' * 511, 512), (b'x', 1), (b'', -512)]:
            with self.subTest(length=length), self.assertRaises(ValueError):
                crypt_stream(io.BytesIO(data), io.BytesIO(), length, bytes(32), True)

    def test_zip_stream_and_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            zipped = root / 'parts.zip'
            with zipfile.ZipFile(zipped, 'w', zipfile.ZIP_DEFLATED) as z:
                z.writestr('part0', b'a' * 200000)
                z.writestr('part1', b'b' * 200000)
            output = root / 'joined'
            with output.open('wb') as out:
                import shutil
                for name in ('part0', 'part1'):
                    with recovery.open_zip_member(zipped, name) as source:
                        shutil.copyfileobj(source, out)
            self.assertEqual(output.read_bytes(), b'a' * 200000 + b'b' * 200000)
            import hashlib
            self.assertEqual(recovery.sha256_file(output), hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
