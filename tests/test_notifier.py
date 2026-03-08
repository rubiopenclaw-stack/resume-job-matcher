"""
Unit tests for notifier.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock resend before importing notifier (resend may not be installed in test env)
from unittest.mock import MagicMock, patch
if 'resend' not in sys.modules:
    sys.modules['resend'] = MagicMock()

import pytest
import src.notifier as notifier_module
from src.notifier import markdown_to_html, send_email, send_match_report, send_digest_email


# ===== Tests: markdown_to_html =====

class TestMarkdownToHtml:

    def test_returns_string(self):
        result = markdown_to_html("Hello")
        assert isinstance(result, str)

    def test_wraps_in_html_doctype(self):
        result = markdown_to_html("Hello")
        assert '<!DOCTYPE html>' in result

    def test_single_bold(self):
        result = markdown_to_html("This is **bold** text")
        assert '<strong>bold</strong>' in result

    def test_multiple_bold_segments(self):
        # Previously broken: only handled first occurrence
        result = markdown_to_html("**foo** and **bar**")
        assert '<strong>foo</strong>' in result
        assert '<strong>bar</strong>' in result

    def test_link_conversion(self):
        result = markdown_to_html("[Click here](https://example.com)")
        assert '<a href="https://example.com">Click here</a>' in result

    def test_multiple_links(self):
        result = markdown_to_html("[A](http://a.com) [B](http://b.com)")
        assert '<a href="http://a.com">A</a>' in result
        assert '<a href="http://b.com">B</a>' in result

    def test_h1_heading(self):
        result = markdown_to_html("# Title Here")
        assert '<h1>Title Here</h1>' in result

    def test_h2_heading(self):
        result = markdown_to_html("## Section")
        assert '<h2>Section</h2>' in result

    def test_h3_heading(self):
        result = markdown_to_html("### Subsection")
        assert '<h3>Subsection</h3>' in result

    def test_h2_not_converted_as_h1(self):
        result = markdown_to_html("## Section")
        # Should not produce h1 for an h2 heading
        assert '<h1>' not in result

    def test_paragraph_break(self):
        result = markdown_to_html("First para\n\nSecond para")
        assert '</p><p>' in result

    def test_line_break(self):
        result = markdown_to_html("Line one\nLine two")
        assert '<br>' in result

    def test_footer_present(self):
        result = markdown_to_html("content")
        assert 'Resume Job Matcher' in result

    def test_empty_string(self):
        result = markdown_to_html("")
        assert isinstance(result, str)
        assert len(result) > 0  # still returns the HTML wrapper

    def test_bold_not_left_dangling(self):
        result = markdown_to_html("**bold**")
        # Should not have leftover ** markers
        assert '**' not in result


# ===== Tests: send_email =====

class TestSendEmail:

    def test_returns_false_without_api_key(self):
        env = {k: v for k, v in os.environ.items() if k != 'RESEND_API_KEY'}
        with patch.dict(os.environ, env, clear=True):
            result = send_email("test@example.com", "Subject", "<p>Hi</p>")
        assert result is False

    def test_sends_email_when_api_key_set(self):
        mock_resend_emails = MagicMock()
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-key'}):
            with patch.object(notifier_module.resend.Emails, 'send', return_value=MagicMock()) as mock_send:
                result = send_email("to@example.com", "Subj", "<p>Body</p>")
        assert result is True

    def test_send_uses_default_from_email(self):
        env = {k: v for k, v in os.environ.items() if k not in ('RESEND_API_KEY', 'EMAIL_FROM')}
        env['RESEND_API_KEY'] = 'test-key'
        captured = {}
        def capture_send(params):
            captured['params'] = params
            return MagicMock()
        with patch.dict(os.environ, env, clear=True):
            with patch.object(notifier_module.resend.Emails, 'send', side_effect=capture_send):
                send_email("to@example.com", "Subj", "<p>Body</p>")
        assert captured['params']['from'] == 'jobs@resend.dev'

    def test_send_uses_env_from_email(self):
        env = {'RESEND_API_KEY': 'test-key', 'EMAIL_FROM': 'custom@myco.com'}
        captured = {}
        def capture_send(params):
            captured['params'] = params
            return MagicMock()
        with patch.dict(os.environ, env):
            with patch.object(notifier_module.resend.Emails, 'send', side_effect=capture_send):
                send_email("to@example.com", "Subj", "<p>Body</p>")
        assert captured['params']['from'] == 'custom@myco.com'

    def test_returns_false_on_exception(self):
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-key'}):
            with patch.object(notifier_module.resend.Emails, 'send', side_effect=Exception("API error")):
                result = send_email("to@example.com", "Subj", "<p>Body</p>")
        assert result is False

    def test_from_email_param_override(self):
        captured = {}
        def capture_send(params):
            captured['params'] = params
            return MagicMock()
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-key'}):
            with patch.object(notifier_module.resend.Emails, 'send', side_effect=capture_send):
                send_email("to@example.com", "Subj", "<p>Body</p>", from_email="override@example.com")
        assert captured['params']['from'] == 'override@example.com'

    def test_to_address_in_list(self):
        captured = {}
        def capture_send(params):
            captured['params'] = params
            return MagicMock()
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-key'}):
            with patch.object(notifier_module.resend.Emails, 'send', side_effect=capture_send):
                send_email("to@example.com", "Subj", "<p>Body</p>")
        assert captured['params']['to'] == ['to@example.com']


# ===== Tests: send_match_report =====

class TestSendMatchReport:

    def _make_matched_job(self, title='Dev', company='Co', score=75.0):
        return {
            'job': {
                'title': title,
                'company': company,
                'salary': '100k',
                'location': 'Remote',
                'url': 'https://example.com',
            },
            'score': score,
            'matched_skills': ['python'],
        }

    def test_returns_true_on_success(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        jobs = [self._make_matched_job()]
        with patch('src.notifier.send_email', return_value=True) as mock_send:
            result = send_match_report(resume, jobs, 'alice@example.com')
        assert result is True
        mock_send.assert_called_once()

    def test_subject_contains_name(self):
        resume = {'name': 'Bob', 'skills': ['python']}
        jobs = [self._make_matched_job()]
        with patch('src.notifier.send_email', return_value=True) as mock_send:
            send_match_report(resume, jobs, 'bob@example.com')
        _, subject, _ = mock_send.call_args[0]
        assert 'Bob' in subject

    def test_subject_contains_count(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        jobs = [self._make_matched_job(), self._make_matched_job(title='Dev2')]
        with patch('src.notifier.send_email', return_value=True) as mock_send:
            send_match_report(resume, jobs, 'alice@example.com')
        _, subject, _ = mock_send.call_args[0]
        assert '2' in subject

    def test_returns_false_when_send_fails(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        with patch('src.notifier.send_email', return_value=False):
            result = send_match_report(resume, [], 'alice@example.com')
        assert result is False


# ===== Tests: send_digest_email =====

class TestSendDigestEmail:

    def _make_job(self, title='AI Engineer'):
        return {
            'id': 'j1',
            'title': title,
            'company': 'TechCo',
            'description': 'Python AI developer',
            'tags': ['python', 'ai'],
            'location': 'Remote',
            'url': 'https://example.com',
        }

    def test_sends_email_to_recipient(self):
        resumes = [{'name': 'Alice', 'skills': ['python', 'ai'], 'preferred_roles': [], 'preferred_locations': []}]
        jobs = [self._make_job()]
        with patch('src.notifier.send_email', return_value=True) as mock_send:
            send_digest_email(resumes, jobs, 'allen@example.com')
        to_addr = mock_send.call_args[0][0]
        assert to_addr == 'allen@example.com'

    def test_subject_contains_resume_count(self):
        resumes = [
            {'name': 'Alice', 'skills': ['python'], 'preferred_roles': [], 'preferred_locations': []},
            {'name': 'Bob', 'skills': ['react'], 'preferred_roles': [], 'preferred_locations': []},
        ]
        jobs = [self._make_job()]
        with patch('src.notifier.send_email', return_value=True) as mock_send:
            send_digest_email(resumes, jobs, 'admin@example.com')
        _, subject, _ = mock_send.call_args[0]
        assert '2' in subject

    def test_empty_resumes(self):
        with patch('src.notifier.send_email', return_value=True) as mock_send:
            send_digest_email([], [], 'admin@example.com')
        mock_send.assert_called_once()
