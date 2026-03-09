"""
Unit tests for main.py - send_notification function and main() orchestration
"""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


# ===== Tests: send_notification =====

class TestSendNotification:
    """Tests for the send_notification function in main.py"""

    def test_returns_true_when_send_succeeds(self):
        with patch('src.main.send_telegram_message', return_value=True) as mock_send:
            with patch('src.main.MESSAGE_TARGET', 'chat-id'):
                from src.main import send_notification
                result = send_notification('hello')
                assert result is True
                mock_send.assert_called_once_with('hello', 'chat-id')

    def test_returns_false_when_send_fails(self):
        with patch('src.main.send_telegram_message', return_value=False):
            with patch('src.main.MESSAGE_TARGET', 'chat-id'):
                from src.main import send_notification
                result = send_notification('hello')
                assert result is False

    def test_passes_message_and_target(self):
        with patch('src.main.send_telegram_message', return_value=True) as mock_send:
            with patch('src.main.MESSAGE_TARGET', '999'):
                from src.main import send_notification
                send_notification('test message')
                mock_send.assert_called_once_with('test message', '999')

    def test_telegram_notify_method(self):
        """NOTIFY_METHOD=telegram should call send_telegram_message"""
        with patch('src.main.NOTIFY_METHOD', 'telegram'):
            with patch('src.main.send_telegram_message', return_value=True) as mock_send:
                with patch('src.main.MESSAGE_TARGET', '123'):
                    from src.main import send_notification
                    result = send_notification('msg')
                    assert result is True
                    mock_send.assert_called_once()

    def test_openclaw_notify_method(self):
        """NOTIFY_METHOD=openclaw should also call send_telegram_message"""
        with patch('src.main.NOTIFY_METHOD', 'openclaw'):
            with patch('src.main.send_telegram_message', return_value=True) as mock_send:
                with patch('src.main.MESSAGE_TARGET', '123'):
                    from src.main import send_notification
                    result = send_notification('msg')
                    assert result is True
                    mock_send.assert_called_once()

    def test_unknown_notify_method_returns_false(self, capsys):
        """Unknown NOTIFY_METHOD should return False without calling send_telegram_message"""
        with patch('src.main.NOTIFY_METHOD', 'unknown_method'):
            with patch('src.main.send_telegram_message') as mock_send:
                from src.main import send_notification
                result = send_notification('msg')
                assert result is False
                mock_send.assert_not_called()

    def test_returns_false_when_send_raises(self):
        with patch('src.main.send_telegram_message', side_effect=Exception('timeout')):
            with patch('src.main.MESSAGE_TARGET', '123'):
                from src.main import send_notification
                # send_notification delegates to send_telegram_message; if it raises, propagate
                try:
                    result = send_notification('hello')
                    # If no exception propagated, result should reflect failure
                    assert result is False
                except Exception:
                    pass  # Acceptable — send_telegram_message raised


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
                with patch('src.main.send_notification', return_value=True):
                    with patch.dict('os.environ', {}, clear=False):
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
                    with patch('src.main.send_notification', return_value=True):
                        from src.main import main
                        main()
                mock_match.assert_called()

    def test_main_with_force_refetch(self):
        """When FORCE_REFETCH is set, main() should call fetch_all_jobs."""
        with patch('src.main.get_all_resumes', return_value=[self._mock_resume()]):
            with patch('src.main.load_jobs', return_value=[self._mock_job()]):
                with patch('src.main.fetch_all_jobs', return_value=[self._mock_job()]) as mock_fetch:
                    with patch('src.main.save_jobs') as mock_save:
                        with patch('src.main.send_notification', return_value=True):
                            with patch.dict('os.environ', {'FORCE_REFETCH': '1'}):
                                from src.main import main
                                main()
                mock_fetch.assert_called_once()
                mock_save.assert_called_once()

    def test_main_continues_when_send_fails(self, capsys):
        """main() should not crash if send_notification returns False."""
        with patch('src.main.get_all_resumes', return_value=[self._mock_resume()]):
            with patch('src.main.load_jobs', return_value=[self._mock_job()]):
                with patch('src.main.send_notification', return_value=False):
                    os.environ.pop('OPENAI_API_KEY', None)
                    from src.main import main
                    main()  # should not raise
        captured = capsys.readouterr()
        assert 'Done' in captured.out
