import unittest
from datetime import date

from chanchan.notice_parser import extract_balance_changes, summarize_notice


class NoticeParserTests(unittest.TestCase):
    def test_summarize_notice_uses_body_fields(self) -> None:
        content = "标题：版本更新\n日期：2026-02-10\nID：12345\n\n正文"
        summary = summarize_notice(content, "notice/2026-02-10_12345.txt")
        self.assertEqual(summary.title, "版本更新")
        self.assertEqual(summary.notice_id, "12345")
        self.assertEqual(summary.published_at, date(2026, 2, 10))

    def test_extract_balance_changes_matches_tagged_sections(self) -> None:
        content = """
标题：平衡调整
日期：2026-02-10

【天选福星】——英雄调整
亚索：攻击力提升

【英雄联盟传奇】——羁绊调整
某羁绊：数值调整
"""
        changes = extract_balance_changes(content, ["天选福星", "英雄联盟传奇"])
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0].category, "英雄调整")
        self.assertEqual(changes[0].season, "天选福星")
        self.assertIn("攻击力提升", changes[0].content)


if __name__ == "__main__":
    unittest.main()
