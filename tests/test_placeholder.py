"""Test configuration and pytest setup."""


def test_imports():
    """Test that core modules can be imported."""
    from yap_on_slack import post_messages

    assert hasattr(post_messages, "parse_rich_text_from_string")
    assert hasattr(post_messages, "post_message")
    assert hasattr(post_messages, "add_reaction")
    assert hasattr(post_messages, "load_config")
    assert hasattr(post_messages, "load_messages")
