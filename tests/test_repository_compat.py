import tempfile
import unittest
from pathlib import Path

from chanchan.repository import GameDataRepository
from chanchan.storage import LocalStorage


class RepositoryRoundtripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo = GameDataRepository(LocalStorage(self.root))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_rune_roundtrip_uses_normalized_structure(self) -> None:
        self.repo.save_rune("天选福星", "一级强化符文", "D个痛快！ I", "rune-content")
        self.assertEqual(self.repo.get_rune("天选福星", "一级强化符文", "D个痛快！ I"), "rune-content")
        self.assertIn("D个痛快！ I", self.repo.list_runes("天选福星", "一级强化符文"))
        expected = self.root / "season_天选福星" / "hex" / "一级强化符文" / "D个痛快！ I.txt"
        self.assertTrue(expected.exists())

    def test_equipment_roundtrip_uses_normalized_structure(self) -> None:
        self.repo.save_equipment("天选福星", "光明装备", "光明版冕卫", "equip-content")
        result = self.repo.get_equipment("天选福星", "光明版冕卫", "光明装备")
        self.assertEqual(result, ("光明装备", "equip-content"))
        self.assertIn("光明装备", self.repo.list_equipment_types("天选福星"))
        self.assertIn(("光明装备", "光明版冕卫"), self.repo.list_equipment("天选福星"))
        expected = self.root / "season_天选福星" / "equipment" / "光明装备" / "光明版冕卫.txt"
        self.assertTrue(expected.exists())


if __name__ == "__main__":
    unittest.main()
