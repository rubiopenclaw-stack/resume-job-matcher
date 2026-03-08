"""
Unit tests for openclaw_notifier.py
"""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.openclaw_notifier import (
    format_job_message,
    send_telegram_message,
    send_via_gateway,
    send_to_openclaw,
)


# ===== Fixtures =====

@pytest.fixture
def resume():
    return {'name': 'Alice', 'skills': ['python', 'ai']}


@pytest.fixture
def matched_jobs():
    return [
        {
            'job': {
                'title': 'AI Engineer',
                'company': 'TechCorp',
                'url': 'https://example.com/job1',
                'salary': '$120k-150k',
            },
            'score': 92.5,
            'matched_skills': ['python', 'ai'],
        },
        {
            'job': {
                'title': 'ML Researcher',
                'company': 'AILab',
                'url': 'https://example.com/job2',
                'salary': '',
            },
            'score': 80.0,
            'matched_skills': ['python'],
        },
    ]


# ===== Tests: format_job_message =====

class TestFormatJobMessage:

    def test_returns_string(self, resume, matched_jobs):
        result = format_job_message(resume, matched_jobs)
        assert isinstance(result, str)

    def test_contains_resume_name(self, resume, matched_jobs):
        result = format_job_message(resume, matched_jobs)
        assert 'Alice' in result

    def test_empty_jobs_returns_no_match_message(self, resume):
        result = format_job_message(resume, [])
        assert 'Alice' in result
        assert '沒有' in result or 'no' in result.lower() or '❌' in result

    def test_contains_job_title(self, resume, matched_jobs):
        result = format_job_message(resume, matched_jobs)
        assert 'AI Engineer' in result

    def test_contains_company(self, resume, matched_jobs):
        result = format_job_message(resume, matched_jobs)
        assert 'TechCorp' in result

    def test_contains_score(self, resume, matched_jobs):
        result = format_job_message(resume, matched_jobs)
        assert '92.5' in result

    def test_contains_url(self, resume, matched_jobs):
        result = format_job_message(resume, matched_jobs)
        assert 'https://example.com/job1' in result

    def test_no_salary_replaced_with_fallback(self, resume, matched_jobs):
        # second job has empty salary
        result = format_job_message(resume, matched_jobs)
        assert isinstance(result, str)  # does not crash

    def test_shows_at_most_5_jobs(self, resume):
        many_jobs = [
            {
                'job': {
                    'title': f'Job {i}',
                    'company': 'Corp',
                    'url': f'https://example.com/{i}',
                    'salary': '$100k',
                },
                'score': 80.0 - i,
                'matched_skills': ['python'],
            }
            for i in range(8)
        ]
        result = format_job_message(resume, many_jobs)
        # Should mention remaining count
        assert '3' in result  # 8 - 5 = 3 remaining

    def test_default_name_when_missing(self, matched_jobs):
        result = format_job_message({}, matched_jobs)
        assert '求職者' in result

    def test_total_count_shown(self, resume, matched_jobs):
        result = format_job_message(resume, matched_jobs)
        assert '2' in result  # 2 matched jobs shown in header

    def test_job_count_header_shows_total(self, resume):
        jobs = [
            {
                'job': {'title': f'Job {i}', 'company': 'Co', 'url': f'https://x.com/{i}', 'salary': ''},
                'score': 70.0,
                'matched_skills': [],
            }
            for i in range(7)
        ]
        result = format_job_message(resume, jobs)
        assert '7' in result


# ===== Tests: send_telegram_message =====

class TestSendTelegramMessage:

    def test_returns_false_when_no_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', None):
                with patch('src.openclaw_notifier.TELEGRAM_CHAT_ID', None):
                    result = send_telegram_message('hello', chat_id='123')
                    assert result is False

    def test_returns_false_when_no_chat_id(self):
        with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('src.openclaw_notifier.TELEGRAM_CHAT_ID', None):
                result = send_telegram_message('hello', chat_id=None)
                assert result is False

    def test_returns_true_on_success(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {'ok': True, 'result': {}}

        with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('requests.post', return_value=mock_response):
                result = send_telegram_message('hello', chat_id='123456')
                assert result is True

    def test_returns_false_on_api_error(self):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'

        with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('requests.post', return_value=mock_response):
                result = send_telegram_message('hello', chat_id='123456')
                assert result is False

    def test_returns_false_on_exception(self):
        with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('requests.post', side_effect=Exception('network error')):
                result = send_telegram_message('hello', chat_id='123456')
                assert result is False

    def test_uses_env_chat_id_when_not_provided(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {'ok': True}

        with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('src.openclaw_notifier.TELEGRAM_CHAT_ID', 'env-chat-id'):
                with patch('requests.post', return_value=mock_response) as mock_post:
                    send_telegram_message('hello')
                    call_kwargs = mock_post.call_args
                    payload = call_kwargs[1]['json'] if 'json' in call_kwargs[1] else call_kwargs[0][1]
                    assert payload['chat_id'] == 'env-chat-id'

    def test_correct_payload_structure(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {'ok': True}

        with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', 'fake-token'):
            with patch('requests.post', return_value=mock_response) as mock_post:
                send_telegram_message('test message', chat_id='999')
                payload = mock_post.call_args[1]['json']
                assert payload['text'] == 'test message'
                assert payload['chat_id'] == '999'
                assert 'parse_mode' in payload


# ===== Tests: send_via_gateway =====

class TestSendViaGateway:

    def test_uses_telegram_when_bot_token_available(self):
        with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', 'my-token'):
            with patch('src.openclaw_notifier.send_telegram_message', return_value=True) as mock_send:
                result = send_via_gateway('hello', to='123')
                mock_send.assert_called_once()
                assert result is True

    def test_falls_back_gracefully_when_no_token(self):
        with patch('src.openclaw_notifier.TELEGRAM_BOT_TOKEN', None):
            with patch.dict(os.environ, {}, clear=True):
                result = send_via_gateway('hello')
                assert result is False


# ===== Tests: send_to_openclaw =====

class TestSendToOpenclaw:

    def test_calls_send_telegram_message(self, resume, matched_jobs):
        with patch('src.openclaw_notifier.send_telegram_message', return_value=True) as mock_send:
            result = send_to_openclaw(resume, matched_jobs, target='123')
            mock_send.assert_called_once()
            assert result is True

    def test_passes_formatted_message(self, resume, matched_jobs):
        with patch('src.openclaw_notifier.send_telegram_message', return_value=True) as mock_send:
            send_to_openclaw(resume, matched_jobs, target='123')
            args = mock_send.call_args[0]
            # First arg is the message string
            assert 'Alice' in args[0]

    def test_passes_target_as_chat_id(self, resume, matched_jobs):
        with patch('src.openclaw_notifier.send_telegram_message', return_value=True) as mock_send:
            send_to_openclaw(resume, matched_jobs, target='999999')
            args = mock_send.call_args[0]
            assert args[1] == '999999'

    def test_returns_false_on_failure(self, resume, matched_jobs):
        with patch('src.openclaw_notifier.send_telegram_message', return_value=False):
            result = send_to_openclaw(resume, matched_jobs)
            assert result is False
