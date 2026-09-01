"""GBK mojibake 还原工具。

当 Windows/GBK 客户端发送 UTF-8 表单时，中文字符会被：
1. 客户端发送 GBK 字节（如"英语" = D3 A2 D3 EF）
2. 服务端按 CP1252/Latin-1 解码成乱码（如 Ó¢Óï）
3. 再按 UTF-8 存入数据库（如 c393c2a2c393c3af）

本模块提供还原函数，将乱码还原为正确的中文。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def is_gbk_mojibake(text: str) -> bool:
    """检测字符串是否是 GBK mojibake（乱码）。

    特征：
    - 包含 CP1252/Latin-1 特有的高位字符（如 Ó、¢、ï）
    - 这些字符组合起来可以还原为有效的 GBK 中文

    Args:
        text: 待检测的字符串

    Returns:
        True 如果是 GBK mojibake
    """
    if not text or not isinstance(text, str):
        return False

    # 检查是否包含 CP1252/Latin-1 特有的高位字符
    # 这些字符在正常的 UTF-8 中文文本中不会出现
    cp1252_chars = set()
    for char in text:
        code = ord(char)
        # CP1252 特有字符范围：0x80-0xFF 中的部分字符
        # 这些字符在 UTF-8 中文文本中很少见
        if 0x80 <= code <= 0xFF:
            cp1252_chars.add(char)

    # 如果没有高位字符，不是 mojibake
    if not cp1252_chars:
        return False

    # 尝试按 CP1252 编码再按 GBK 解码，看是否能得到有效中文
    try:
        # 将字符串按 CP1252 编码为字节
        raw_bytes = text.encode('cp1252', errors='strict')
        # 尝试按 GBK 解码
        decoded = raw_bytes.decode('gbk', errors='strict')
        # 检查解码结果是否包含中文字符
        has_chinese = any('一' <= char <= '鿿' for char in decoded)
        return has_chinese
    except (UnicodeDecodeError, UnicodeEncodeError):
        return False


def fix_gbk_mojibake(text: str) -> str:
    """还原 GBK mojibake（乱码）为正确的中文。

    还原过程：
    1. 将乱码字符串按 CP1252 编码为字节
    2. 将字节按 GBK 解码为正确的中文

    Args:
        text: 包含 GBK mojibake 的字符串

    Returns:
        还原后的字符串，如果不是 mojibake 则原样返回
    """
    if not text or not isinstance(text, str):
        return text

    # 先检测是否是 mojibake
    if not is_gbk_mojibake(text):
        return text

    try:
        # 按 CP1252 编码为字节
        raw_bytes = text.encode('cp1252', errors='strict')
        # 按 GBK 解码
        decoded = raw_bytes.decode('gbk', errors='strict')
        logger.info("Fixed GBK mojibake: %r -> %r", text, decoded)
        return decoded
    except (UnicodeDecodeError, UnicodeEncodeError) as e:
        logger.warning("Failed to fix GBK mojibake for %r: %s", text, e)
        return text


def fix_document_encoding(
    filename: str | None,
    subject: str | None,
    grade: str | None,
) -> tuple[str | None, str | None, str | None]:
    """修复文档的编码问题。

    Args:
        filename: 文件名
        subject: 科目
        grade: 年级

    Returns:
        修复后的 (filename, subject, grade)
    """
    fixed_filename = fix_gbk_mojibake(filename) if filename else filename
    fixed_subject = fix_gbk_mojibake(subject) if subject else subject
    fixed_grade = fix_gbk_mojibake(grade) if grade else grade

    # 记录修复情况
    changes = []
    if filename != fixed_filename:
        changes.append(f"filename: {filename!r} -> {fixed_filename!r}")
    if subject != fixed_subject:
        changes.append(f"subject: {subject!r} -> {fixed_subject!r}")
    if grade != fixed_grade:
        changes.append(f"grade: {grade!r} -> {fixed_grade!r}")

    if changes:
        logger.info("Fixed document encoding: %s", ", ".join(changes))

    return fixed_filename, fixed_subject, fixed_grade
