from project_context.gmail.utils import extract_quoted_blocks, remove_gmail_trailing_quoted_content


def test_extract_quoted_blocks_single_level():
    text = (
        "Thanks for confirming!\n"
        "\n"
        "On Mon, 12 Jan 2026 at 10:58, John Smith <john@example.com> wrote:\n"
        "> Hi there,\n"
        "> Can we confirm the date?\n"
        "> Thanks\n"
    )
    blocks = extract_quoted_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].sender_email == "john@example.com"
    assert blocks[0].sender_name == "John Smith"
    assert "Can we confirm the date?" in blocks[0].content
    assert "Hi there," in blocks[0].content


def test_extract_quoted_blocks_nested():
    text = (
        "Sounds good.\n"
        "\n"
        "On Tue, 13 Jan 2026 at 09:00, Alice Brown <alice@example.com> wrote:\n"
        "> Got it, thanks.\n"
        ">\n"
        "> On Mon, 12 Jan 2026 at 10:58, Bob Green <bob@example.com> wrote:\n"
        ">> Please send the invoice.\n"
        ">> Regards\n"
    )
    blocks = extract_quoted_blocks(text)
    assert len(blocks) >= 2

    emails = {b.sender_email for b in blocks}
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails

    bob_block = next(b for b in blocks if b.sender_email == "bob@example.com")
    assert "Please send the invoice." in bob_block.content


def test_extract_quoted_blocks_no_quotes():
    text = "Just a plain message with no quoted content."
    blocks = extract_quoted_blocks(text)
    assert blocks == []


def test_extract_quoted_blocks_gmail_comma_format():
    text = (
        "OK\n"
        "\n"
        "On Mon, 12 Jan 2026, 10:58, Jane Doe <jane@example.com> wrote:\n"
        "> Meeting at 3pm works.\n"
    )
    blocks = extract_quoted_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].sender_email == "jane@example.com"
    assert "Meeting at 3pm works." in blocks[0].content


def test_remove_gmail_trailing_quoted_content_strips():
    text = (
        "My reply here.\n"
        "\n"
        "On Mon, 12 Jan 2026 at 10:58, Someone <someone@example.com> wrote:\n"
        "> Old message\n"
    )
    result = remove_gmail_trailing_quoted_content(text)
    assert "My reply here." in result
    assert "Old message" not in result
    assert "wrote:" not in result


def test_remove_gmail_trailing_quoted_content_no_quotes():
    text = "Just a message."
    result = remove_gmail_trailing_quoted_content(text)
    assert result == "Just a message."


def test_remove_gmail_trailing_quoted_content_forwarded():
    text = (
        "See below.\n"
        "\n"
        "---------- Forwarded message\n"
        "From: test@test.com\n"
    )
    result = remove_gmail_trailing_quoted_content(text)
    assert "See below." in result
    assert "Forwarded" not in result
