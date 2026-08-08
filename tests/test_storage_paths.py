import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.storage.main import get_office_folder


class OfficeFolderTests(unittest.TestCase):
    def test_uses_selected_flyer_date_and_office(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("app.storage.main.CAPTURAS_DIR", root):
                folder = get_office_folder("ATALAYA", "06/08/2026")

            self.assertEqual(folder, root / "volantes 06-08-2026" / "ATALAYA")
            self.assertTrue(folder.is_dir())


if __name__ == "__main__":
    unittest.main()
