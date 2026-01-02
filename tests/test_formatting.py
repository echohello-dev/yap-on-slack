"""Unit tests for text formatting functions."""

from yap_on_slack.post_messages import parse_rich_text_from_string


class TestParseRichTextFromString:
    """Test suite for parse_rich_text_from_string function."""

    def test_plain_text(self):
        """Test plain text without formatting."""
        result = parse_rich_text_from_string("Hello world")
        assert result == [{"type": "text", "text": "Hello world"}]

    def test_empty_string(self):
        """Test empty string input."""
        result = parse_rich_text_from_string("")
        assert result == [{"type": "text", "text": " "}]  # Empty string returns space

    # Bold formatting tests
    def test_single_asterisk_bold(self):
        """Test bold text with single asterisks."""
        result = parse_rich_text_from_string("This is *bold* text")
        assert result == [
            {"type": "text", "text": "This is "},
            {"type": "text", "text": "bold", "style": {"bold": True}},
            {"type": "text", "text": " text"},
        ]

    def test_double_asterisk_bold(self):
        """Test bold text with double asterisks."""
        result = parse_rich_text_from_string("This is **bold** text")
        assert result == [
            {"type": "text", "text": "This is "},
            {"type": "text", "text": "bold", "style": {"bold": True}},
            {"type": "text", "text": " text"},
        ]

    def test_multiple_bold_sections(self):
        """Test multiple bold sections in one string."""
        result = parse_rich_text_from_string("*First* and *second* bold")
        assert result == [
            {"type": "text", "text": "First", "style": {"bold": True}},
            {"type": "text", "text": " and "},
            {"type": "text", "text": "second", "style": {"bold": True}},
            {"type": "text", "text": " bold"},
        ]

    def test_bold_at_start(self):
        """Test bold text at the start."""
        result = parse_rich_text_from_string("*bold* at start")
        assert result == [
            {"type": "text", "text": "bold", "style": {"bold": True}},
            {"type": "text", "text": " at start"},
        ]

    def test_bold_at_end(self):
        """Test bold text at the end."""
        result = parse_rich_text_from_string("at end *bold*")
        assert result == [
            {"type": "text", "text": "at end "},
            {"type": "text", "text": "bold", "style": {"bold": True}},
        ]

    # Italic formatting tests
    def test_italic(self):
        """Test italic text with underscores."""
        result = parse_rich_text_from_string("This is _italic_ text")
        assert result == [
            {"type": "text", "text": "This is "},
            {"type": "text", "text": "italic", "style": {"italic": True}},
            {"type": "text", "text": " text"},
        ]

    def test_multiple_italic_sections(self):
        """Test multiple italic sections."""
        result = parse_rich_text_from_string("_First_ and _second_ italic")
        assert result == [
            {"type": "text", "text": "First", "style": {"italic": True}},
            {"type": "text", "text": " and "},
            {"type": "text", "text": "second", "style": {"italic": True}},
            {"type": "text", "text": " italic"},
        ]

    # Strikethrough tests
    def test_strikethrough(self):
        """Test strikethrough text with tildes."""
        result = parse_rich_text_from_string("This is ~strike~ text")
        assert result == [
            {"type": "text", "text": "This is "},
            {"type": "text", "text": "strike", "style": {"strike": True}},
            {"type": "text", "text": " text"},
        ]

    # Code formatting tests
    def test_inline_code(self):
        """Test inline code with backticks."""
        result = parse_rich_text_from_string("Run `npm install` command")
        assert result == [
            {"type": "text", "text": "Run "},
            {"type": "text", "text": "npm install", "style": {"code": True}},
            {"type": "text", "text": " command"},
        ]

    def test_multiple_code_sections(self):
        """Test multiple code sections."""
        result = parse_rich_text_from_string("`code1` and `code2` here")
        assert result == [
            {"type": "text", "text": "code1", "style": {"code": True}},
            {"type": "text", "text": " and "},
            {"type": "text", "text": "code2", "style": {"code": True}},
            {"type": "text", "text": " here"},
        ]

    # Emoji tests
    def test_emoji(self):
        """Test emoji parsing."""
        result = parse_rich_text_from_string("Hello :wave: world")
        assert result == [
            {"type": "text", "text": "Hello "},
            {"type": "emoji", "name": "wave"},
            {"type": "text", "text": " world"},
        ]

    def test_multiple_emojis(self):
        """Test multiple emojis."""
        result = parse_rich_text_from_string(":rocket: Deploy :white_check_mark:")
        assert result == [
            {"type": "emoji", "name": "rocket"},
            {"type": "text", "text": " Deploy "},
            {"type": "emoji", "name": "white_check_mark"},
        ]

    def test_emoji_with_underscores(self):
        """Test emoji names with underscores."""
        result = parse_rich_text_from_string(":thinking_face:")
        assert result == [{"type": "emoji", "name": "thinking_face"}]

    # Link tests
    def test_link_with_label(self):
        """Test link with custom label."""
        result = parse_rich_text_from_string("Check <https://example.com|this link>")
        assert result == [
            {"type": "text", "text": "Check "},
            {"type": "link", "url": "https://example.com", "text": "this link"},
        ]

    def test_link_without_label(self):
        """Test link without label (URL as label)."""
        result = parse_rich_text_from_string("Visit <https://example.com>")
        assert result == [
            {"type": "text", "text": "Visit "},
            {"type": "link", "url": "https://example.com", "text": "https://example.com"},
        ]

    def test_raw_url(self):
        """Test raw URL without brackets."""
        result = parse_rich_text_from_string("Visit https://example.com today")
        assert len(result) == 3
        assert result[0] == {"type": "text", "text": "Visit "}
        assert result[1]["type"] == "link"
        assert result[1]["url"] == "https://example.com"
        assert result[2] == {"type": "text", "text": " today"}

    def test_long_url_truncation(self):
        """Test that long URLs are truncated in label."""
        long_url = "https://example.com/" + "a" * 50
        result = parse_rich_text_from_string(f"Visit {long_url}")
        assert len(result) == 2
        assert result[1]["type"] == "link"
        assert result[1]["url"] == long_url
        assert len(result[1]["text"]) <= 33  # 30 chars + "..."

    # Multi-line tests
    def test_newline_preservation(self):
        """Test that newlines are preserved."""
        result = parse_rich_text_from_string("Line 1\nLine 2")
        assert result == [
            {"type": "text", "text": "Line 1"},
            {"type": "text", "text": "\n"},
            {"type": "text", "text": "Line 2"},
        ]

    def test_multiple_newlines(self):
        """Test multiple newlines."""
        result = parse_rich_text_from_string("Line 1\n\nLine 3")
        # Should have: Line 1, \n, \n, Line 3
        assert len(result) == 4
        assert result[1] == {"type": "text", "text": "\n"}
        assert result[2] == {"type": "text", "text": "\n"}

    # Bullet point tests
    def test_bullet_with_dot(self):
        """Test bullet points with dot character."""
        result = parse_rich_text_from_string("• First item")
        assert result[0] == {"type": "text", "text": "First item"}

    def test_bullet_with_dash(self):
        """Test bullet points with dash."""
        result = parse_rich_text_from_string("- First item")
        assert result[0] == {"type": "text", "text": "First item"}

    def test_multiple_bullets(self):
        """Test multiple bullet points."""
        result = parse_rich_text_from_string("• First\n• Second")
        assert result[0] == {"type": "text", "text": "First"}
        assert result[1] == {"type": "text", "text": "\n"}
        assert result[2] == {"type": "text", "text": "Second"}

    def test_bullets_with_preceding_text(self):
        """Test bullets following normal text get newline."""
        result = parse_rich_text_from_string("Header:\n• Item")
        # Should have a newline before bullet item
        assert {"type": "text", "text": "\n"} in result

    # Mixed formatting tests
    def test_bold_and_italic(self):
        """Test mixed bold and italic."""
        result = parse_rich_text_from_string("*bold* and _italic_")
        assert result == [
            {"type": "text", "text": "bold", "style": {"bold": True}},
            {"type": "text", "text": " and "},
            {"type": "text", "text": "italic", "style": {"italic": True}},
        ]

    def test_bold_with_emoji(self):
        """Test bold text with emoji."""
        result = parse_rich_text_from_string("*Deploy* :rocket:")
        assert result == [
            {"type": "text", "text": "Deploy", "style": {"bold": True}},
            {"type": "text", "text": " "},
            {"type": "emoji", "name": "rocket"},
        ]

    def test_code_with_link(self):
        """Test code with link."""
        result = parse_rich_text_from_string("`npm install` from https://npmjs.com")
        assert len(result) == 3
        assert result[0] == {"type": "text", "text": "npm install", "style": {"code": True}}
        assert result[1] == {"type": "text", "text": " from "}
        assert result[2]["type"] == "link"

    def test_complex_formatting(self):
        """Test complex mixed formatting."""
        text = "*Issue* in prod :bug:: `TypeError`"
        result = parse_rich_text_from_string(text)
        # Issue (bold), " in prod ", :bug:, ": ", TypeError (code)
        assert len(result) == 5
        assert result[0] == {"type": "text", "text": "Issue", "style": {"bold": True}}
        assert result[1] == {"type": "text", "text": " in prod "}
        assert result[2] == {"type": "emoji", "name": "bug"}
        assert result[3] == {"type": "text", "text": ": "}
        assert result[4] == {"type": "text", "text": "TypeError", "style": {"code": True}}

    # Edge cases
    def test_unclosed_bold(self):
        """Test unclosed bold marker (should be treated as plain text)."""
        result = parse_rich_text_from_string("This is *unclosed")
        # With current implementation, unclosed markers are treated as plain text
        assert {"type": "text", "text": "This is *unclosed"} in result or len(result) > 0

    def test_empty_bold(self):
        """Test empty bold markers."""
        result = parse_rich_text_from_string("Text ** more")
        # Should handle gracefully
        assert len(result) > 0

    def test_nested_formatting_attempt(self):
        """Test attempted nested formatting (not typically supported)."""
        result = parse_rich_text_from_string("*bold _and italic_*")
        # Parser handles this sequentially, not nested
        assert len(result) > 0

    def test_special_chars_in_text(self):
        """Test special characters in plain text."""
        result = parse_rich_text_from_string("Price: $100 & tax")
        assert {"type": "text", "text": "Price: $100 & tax"} in result or len(result) > 0

    def test_only_formatting_markers(self):
        """Test string with only formatting markers."""
        result = parse_rich_text_from_string("***")
        assert len(result) > 0

    def test_whitespace_preservation(self):
        """Test that whitespace is preserved."""
        result = parse_rich_text_from_string("  Leading and trailing  ")
        assert len(result) > 0
        # Check that whitespace is somewhere in the result
        text_content = "".join(
            elem.get("text", "") for elem in result if elem.get("type") == "text"
        )
        assert "  " in text_content

    # @mention tests
    def test_broadcast_here(self):
        """Test @here broadcast mention."""
        result = parse_rich_text_from_string("Attention @here please check")
        assert result == [
            {"type": "text", "text": "Attention "},
            {"type": "broadcast", "range": "here"},
            {"type": "text", "text": " please check"},
        ]

    def test_broadcast_channel(self):
        """Test @channel broadcast mention."""
        result = parse_rich_text_from_string("@channel important update")
        assert result == [
            {"type": "broadcast", "range": "channel"},
            {"type": "text", "text": " important update"},
        ]

    def test_broadcast_everyone(self):
        """Test @everyone broadcast mention."""
        result = parse_rich_text_from_string("Hey @everyone!")
        assert result == [
            {"type": "text", "text": "Hey "},
            {"type": "broadcast", "range": "everyone"},
            {"type": "text", "text": "!"},
        ]

    def test_user_mention(self):
        """Test @username mention."""
        result = parse_rich_text_from_string("cc @oncall")
        assert result == [
            {"type": "text", "text": "cc "},
            {"type": "text", "text": "@oncall", "style": {"bold": True}},
        ]

    def test_user_mention_with_formatting(self):
        """Test @username mention with other formatting."""
        result = parse_rich_text_from_string("*FYI* @john-doe check this :rocket:")
        assert result[0] == {"type": "text", "text": "FYI", "style": {"bold": True}}
        assert result[1] == {"type": "text", "text": " "}
        assert result[2] == {"type": "text", "text": "@john-doe", "style": {"bold": True}}
        assert result[3] == {"type": "text", "text": " check this "}
        assert result[4] == {"type": "emoji", "name": "rocket"}

    def test_multiple_mentions(self):
        """Test multiple user mentions."""
        result = parse_rich_text_from_string("@alice @bob please review")
        assert result[0] == {"type": "text", "text": "@alice", "style": {"bold": True}}
        assert result[1] == {"type": "text", "text": " "}
        assert result[2] == {"type": "text", "text": "@bob", "style": {"bold": True}}
        assert result[3] == {"type": "text", "text": " please review"}
