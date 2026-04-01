import unittest

from chanchan.pathing import build_key, rune_level_dir, season_prefix, txt_filename


class PathingTests(unittest.TestCase):
    def test_season_prefix_sanitizes_invalid_chars(self) -> None:
        self.assertEqual(season_prefix('天选/福星:*?"'), "season_天选福星")

    def test_rune_level_dir_keeps_suffix(self) -> None:
        self.assertEqual(rune_level_dir("三级强化符文"), "三级强化符文")

    def test_txt_filename_and_build_key(self) -> None:
        self.assertEqual(txt_filename("亚索"), "亚索.txt")
        self.assertEqual(build_key("season_x", "hero", "亚索.txt"), "season_x/hero/亚索.txt")


if __name__ == "__main__":
    unittest.main()
