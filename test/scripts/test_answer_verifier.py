import answer_verifier as av


def test_html_table_keeps_blank_cells_aligned():
    html = (
        "<table><tr><td>\u9898\u53f7</td><td>1</td><td>2</td><td>3</td><td>4</td>"
        "<td>5</td><td>6</td><td>7</td><td>8</td></tr>"
        "<tr><td>\u7b54\u6848</td><td>C</td><td>B</td><td>D</td><td></td>"
        "<td>C</td><td>D</td><td></td><td>B</td></tr></table>"
    )
    mapping, blank = av._parse_html_tables(html)
    assert mapping[5] == "C"
    assert mapping[6] == "D"
    assert mapping[8] == "B"
    assert 4 in blank
    assert 7 in blank


def test_prefix_parser_does_not_match_free_text():
    text = "18. was awarded\n21. confusing\n26. A\n37. B"
    mapping = av._parse_prefix(text)
    assert 18 not in mapping
    assert 21 not in mapping
    assert mapping[26] == "A"
    assert mapping[37] == "B"


def test_inline_parser_matches_history():
    text = (
        "1\uff0e\u3010\u5206\u6790\u3011\u672c\u9898\u4e3b\u8981\u8003\u67e5\u77f3\u5668\u65f6\u4ee3\u3002\n"
        "\u3010\u89e3\u7b54\u3011\u2026\u2026\u9009\u7b54C\u9879\uff1b\n"
        "2\uff0e\u2026\u2026\u9009\u7b54B\u9879\u3002"
    )
    mapping = av._parse_inline(text)
    assert mapping[1] == "C"
    assert mapping[2] == "B"


def test_raw_table_priority_over_ocr_errors():
    raw = (
        "\u53c2\u8003\u7b54\u6848\n\u9898\u53f7\n1\n2\n3\n4\n5\n6\n7\n"
        "\u7b54\u6848\nD\nA\nC\nB\nD\nC\nA\n"
    )
    ocr = (
        "<table><tr><td>\u9898\u53f7</td><td>1</td><td>2</td><td>3</td><td>4</td>"
        "<td>5</td><td>6</td><td>7</td></tr>"
        "<tr><td>\u7b54\u6848</td><td>D</td><td>A</td><td>C</td><td>B</td>"
        "<td>a</td><td>D</td><td>\u2200</td></tr></table>"
    )
    evidence = av.build_evidence(raw, "", ocr)
    assert evidence.table[5] == "D"
    assert evidence.table[6] == "C"
    assert evidence.table[7] == "A"


def test_long_free_text_answer_needs_manual_review():
    """长自由文本答案（作文/长解答题）→ essay_manual_review（需人工审核）。

    2026-08-25：英语 Q46 作文答案（713 字符）无法通过答案区标记自动验证，
    标记为"需人工审核"，区别于短答案的 free_text_answer。
    """
    raw = "\u53c2\u8003\u7b54\u6848\n\u9898\u53f7 46\n\u7b54\u6848\n\u4e00\u7bc7\u8303\u6587"
    evidence = av.build_evidence(raw, "", "")
    essay = "Dear Jim,\n" + "I am very glad to hear that you are coming to China. " * 8
    ver = av.verify_one("46", essay, None, evidence)
    assert ver.status == av.UNVERIFIABLE
    assert ver.reason == "essay_manual_review"


def test_short_free_text_answer_stays_free_text():
    """短自由文本答案（找不到证据）仍标记 free_text_answer。"""
    raw = "\u53c2\u8003\u7b54\u6848\n\u9898\u53f7 1\n\u7b54\u6848\nA"
    evidence = av.build_evidence(raw, "", "")
    # 题号 9 不在答案区，答案较短（<100 字符）→ free_text_answer
    ver = av.verify_one("9", "x\u7684\u503c\u4e3a\u221a2", None, evidence)
    assert ver.status == av.UNVERIFIABLE
    assert ver.reason == "free_text_answer"
