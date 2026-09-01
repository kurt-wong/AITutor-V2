"""encoding.py 单元测试 — 验证 GBK mojibake 检测和还原。

测试覆盖：
- GBK mojibake 检测（"Ó¢Óï" -> True）
- GBK mojibake 还原（"Ó¢Óï" -> "英语"）
- 正常 UTF-8 中文不被误伤
- 乱码文件名整体还原
"""

import pytest

from app.utils.encoding import (
    fix_gbk_mojibake,
    fix_document_encoding,
    is_gbk_mojibake,
)


class TestIsGbkMojibake:
    """测试 GBK mojibake 检测。"""

    def test_detects_gbk_mojibake_chinese(self):
        """检测中文 GBK mojibake。"""
        # "英语" 的 GBK mojibake
        assert is_gbk_mojibake("Ó¢Óï") is True

    def test_detects_gbk_mojibake_grade(self):
        """检测年级 GBK mojibake。"""
        # "高一" 的 GBK mojibake
        assert is_gbk_mojibake("¸ßÒ»") is True

    def test_rejects_normal_utf8_chinese(self):
        """正常 UTF-8 中文不被误判。"""
        assert is_gbk_mojibake("英语") is False
        assert is_gbk_mojibake("高一") is False
        assert is_gbk_mojibake("数学") is False

    def test_rejects_ascii(self):
        """ASCII 字符不被误判。"""
        assert is_gbk_mojibake("English") is False
        assert is_gbk_mojibake("test.pdf") is False

    def test_rejects_empty_string(self):
        """空字符串不被误判。"""
        assert is_gbk_mojibake("") is False
        assert is_gbk_mojibake(None) is False

    def test_detects_gbk_mojibake_filename(self):
        """检测乱码文件名。"""
        # "北京东城" 的 GBK mojibake
        assert is_gbk_mojibake("±±¾©¶«³Ç") is True


class TestFixGbkMojibake:
    """测试 GBK mojibake 还原。"""

    def test_fixes_chinese_subject(self):
        """修复中文科目。"""
        assert fix_gbk_mojibake("Ó¢Óï") == "英语"

    def test_fixes_chinese_grade(self):
        """修复中文年级。"""
        assert fix_gbk_mojibake("¸ßÒ»") == "高一"

    def test_fixes_chinese_filename(self):
        """修复中文文件名。"""
        assert fix_gbk_mojibake("±±¾©¶«³Ç") == "北京东城"

    def test_preserves_normal_utf8(self):
        """正常 UTF-8 中文原样返回。"""
        assert fix_gbk_mojibake("英语") == "英语"
        assert fix_gbk_mojibake("高一") == "高一"

    def test_preserves_ascii(self):
        """ASCII 字符原样返回。"""
        assert fix_gbk_mojibake("English") == "English"
        assert fix_gbk_mojibake("test.pdf") == "test.pdf"

    def test_preserves_empty_string(self):
        """空字符串原样返回。"""
        assert fix_gbk_mojibake("") == ""
        assert fix_gbk_mojibake(None) is None

    def test_fixes_mixed_filename(self):
        """修复混合乱码文件名。"""
        # "2026北京东城高一（上）期末英语（教师版）.pdf" 的 GBK mojibake
        mojibake = "2026±±¾©¶«³Ç¸ßÒ»£¨ÉÏ£©ÆÚÄ©Ó¢Óï£¨½ÌÊ¦°æ£©.pdf"
        expected = "2026北京东城高一（上）期末英语（教师版）.pdf"
        assert fix_gbk_mojibake(mojibake) == expected


class TestFixDocumentEncoding:
    """测试文档编码修复。"""

    def test_fixes_all_fields(self):
        """修复所有字段。"""
        filename = "2026±±¾©¶«³Ç¸ßÒ»£¨ÉÏ£©ÆÚÄ©Ó¢Óï£¨½ÌÊ¦°æ£©.pdf"
        subject = "Ó¢Óï"
        grade = "¸ßÒ»"

        fixed_filename, fixed_subject, fixed_grade = fix_document_encoding(
            filename, subject, grade
        )

        assert fixed_filename == "2026北京东城高一（上）期末英语（教师版）.pdf"
        assert fixed_subject == "英语"
        assert fixed_grade == "高一"

    def test_preserves_normal_fields(self):
        """正常字段原样返回。"""
        filename = "test.pdf"
        subject = "英语"
        grade = "高一"

        fixed_filename, fixed_subject, fixed_grade = fix_document_encoding(
            filename, subject, grade
        )

        assert fixed_filename == "test.pdf"
        assert fixed_subject == "英语"
        assert fixed_grade == "高一"

    def test_handles_none_fields(self):
        """处理 None 字段。"""
        fixed_filename, fixed_subject, fixed_grade = fix_document_encoding(
            None, None, None
        )

        assert fixed_filename is None
        assert fixed_subject is None
        assert fixed_grade is None
