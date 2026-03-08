"""
Unit tests for main.py - send_telegram function
"""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


# ===== Tests: send_telegram =====

class TestSendTelegram:
    """Tests for the send_telegram function in main.py"""

    def _get_send_telegram(self):
        """Import send_telegram from main freshly."""
        # Import send_telegram directly (avoiding running main())
        import importlib
        import src.main as main_mod
        return main_mod.send_telegram

    def test_returns_false_when_no_bot_token(self):
        with patch('src.main.TELEGRAM_BOT_TOKEN', None):
            with patch('src.main.MESSAGE_TARGET', 'some-chat-id'):
                from src.main import send_telegram
                result = send_telegram('hello')
                assert result is False

    def test_returns_false_when_no_message_target(self):
        with patch('src.main.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('src.main.MESSAGE_TARGET', None):
                from src.main import send_telegram
                result = send_telegram('hello')
                assert result is False

    def test_returns_true_on_success(self):
        mock_response = MagicMock()
        mock_response.ok = True

        with patch('src.main.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('src.main.MESSAGE_TARGET', '123456'):
                with patch('requests.post', return_value=mock_response):
                    from src.main import send_telegram
                    result = send_telegram('hello')
                    assert result is True

    def test_returns_false_on_api_error(self):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.text = 'Unauthorized'

        with patch('src.main.TELEGRAM_BOT_TOKEN', 'bad-token'):
            with patch('src.main.MESSAGE_TARGET', '123456'):
                with patch('requests.post', return_value=mock_response):
                    from src.main import send_telegram
                    result = send_telegram('hello')
                    assert result is False

    def test_returns_false_on_network_exception(self):
        with patch('src.main.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('src.main.MESSAGE_TARGET', '123456'):
                with patch('requests.post', side_effect=Exception('timeout')):
                    from src.main import send_telegram
                    result = send_telegram('hello')
                    assert result is False

    def test_sends_to_correct_url(self):
        mock_response = MagicMock()
        mock_response.ok = True

        with patch('src.main.TELEGRAM_BOT_TOKEN', 'mytoken123'):
            with patch('src.main.MESSAGE_TARGET', '999'):
                with patch('requests.post', return_value=mock_response) as mock_post:
                    from src.main import send_telegram
                    send_telegram('test')
                    url = mock_post.call_args[0][0]
                    assert 'mytoken123' in url
                    assert 'sendMessage' in url

    def test_payload_contains_message(self):
        mock_response = MagicMock()
        mock_response.ok = True

        with patch('src.main.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('src.main.MESSAGE_TARGET', '123'):
                with patch('requests.post', return_value=mock_response) as mock_post:
                    from src.main import send_telegram
                    send_telegram('my message text')
                    payload = mock_post.call_args[1]['json']
                    assert payload['text'] == 'my message text'
                    assert payload['chat_id'] == '123'

    def test_payload_uses_markdown_parse_mode(self):
        mock_response = MagicMock()
        mock_response.ok = True

        with patch('src.main.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('src.main.MESSAGE_TARGET', '123'):
                with patch('requests.post', return_value=mock_response) as mock_post:
                    from src.main import send_telegram
                    send_telegram('msg')
                    payload = mock_post.call_args[1]['json']
                    assert payload.get('parse_mode') == 'Markdown'
