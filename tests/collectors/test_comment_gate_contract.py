from pathlib import Path

COMMENT_GATE_TEST = Path("tests/collectors/test_comment_assertions.py")


def test_comment_not_all_empty_gate_test_is_declared() -> None:
    assert COMMENT_GATE_TEST.exists()

    source = COMMENT_GATE_TEST.read_text(encoding="utf-8")

    assert "@pytest.mark.gate" in source
    assert "def test_comment_not_all_empty" in source
