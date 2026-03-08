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


# ===== Tests: main() function =====

class TestMainFunction:
    """Tests for the main() orchestration function."""

    def _mock_resume(self):
        return {
            'name': 'Test User',
            'skills': ['python', 'ai'],
            'preferred_roles': ['engineer'],
            'preferred_locations': ['remote'],
        }

    def _mock_job(self):
        return {
            'id': 'j1',
            'title': 'AI Engineer',
            'company': 'TechCorp',
            'description': 'Python AI developer',
            'tags': ['python', 'ai'],
            'location': 'Remote',
            'source': 'RemoteOK',
            'url': 'https://example.com/j1',
        }

    def test_main_exits_when_no_resumes(self, capsys):
        with patch('src.main.get_all_resumes', return_value=[]):
            with patch('src.main.load_jobs', return_value=[self._mock_job()]):
                from src.main import main
                main()
        captured = capsys.readouterr()
        assert 'No resumes' in captured.out

    def test_main_exits_when_no_jobs(self, capsys):
        with patch('src.main.get_all_resumes', return_value=[self._mock_resume()]):
            with patch('src.main.load_jobs', return_value=[]):
                from src.main import main
                main()
        captured = capsys.readouterr()
        assert 'No jobs' in captured.out

    def test_main_runs_without_ai_key(self, capsys):
        """main() should succeed using simple matching when no OPENAI_API_KEY."""
        with patch('src.main.get_all_resumes', return_value=[self._mock_resume()]):
            with patch('src.main.load_jobs', return_value=[self._mock_job()]):
                with patch('src.main.send_telegram', return_value=True):
                    with patch.dict('os.environ', {}, clear=False):
                        # Remove AI key if present
                        import os
                        os.environ.pop('OPENAI_API_KEY', None)
                        os.environ.pop('OPENAI_BASE_URL', None)
                        from src.main import main
                        main()
        captured = capsys.readouterr()
        assert 'Done' in captured.out

    def test_main_calls_match_jobs(self):
        """main() should invoke match_jobs for each resume."""
        with patch('src.main.get_all_resumes', return_value=[self._mock_resume()]):
            with patch('src.main.load_jobs', return_value=[self._mock_job()]):
                with patch('src.main.match_jobs', return_value=[]) as mock_match:
                    with patch('src.main.send_telegram', return_value=True):
                        from src.main import main
                        main()
                mock_match.assert_called()

    def test_main_with_force_refetch(self):
        """When FORCE_REFETCH is set, main() should call fetch_all_jobs."""
        with patch('src.main.get_all_resumes', return_value=[self._mock_resume()]):
            with patch('src.main.load_jobs', return_value=[self._mock_job()]):
                with patch('src.main.fetch_all_jobs', return_value=[self._mock_job()]) as mock_fetch:
                    with patch('src.main.save_jobs') as mock_save:
                        with patch('src.main.send_telegram', return_value=True):
                            with patch.dict('os.environ', {'FORCE_REFETCH': '1'}):
                                from src.main import main
                                main()
                mock_fetch.assert_called_once()
                mock_save.assert_called_once()

    def test_main_continues_when_send_fails(self, capsys):
        """main() should not crash if send_telegram returns False."""
        with patch('src.main.get_all_resumes', return_value=[self._mock_resume()]):
            with patch('src.main.load_jobs', return_value=[self._mock_job()]):
                with patch('src.main.send_telegram', return_value=False):
                    import os
                    os.environ.pop('OPENAI_API_KEY', None)
                    from src.main import main
                    main()  # should not raise
        captured = capsys.readouterr()
        assert 'Done' in captured.out
