"""
Unit tests for ai_evaluator.py
Tests simple_match and format_ai_message (no OpenAI required)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock
from src.ai_evaluator import (
    simple_match,
    format_ai_message,
    get_openai_client,
    evaluate_match_with_ai,
    evaluate_batch,
)


# ===== Fixtures =====

@pytest.fixture
def resume():
    return {
        'name': 'Alice',
        'skills': ['Python', 'AI', 'React', 'Docker'],
        'preferred_roles': ['engineer'],
    }


@pytest.fixture
def ai_job():
    return {
        'title': 'AI Engineer',
        'company': 'TechCorp',
        'description': 'We need Python and AI experience with React skills.',
        'tags': ['python', 'ai', 'react'],
        'url': 'https://example.com/job1',
        'source': 'RemoteOK',
    }


@pytest.fixture
def matched_jobs():
    return [
        {
            'job': {
                'title': 'AI Engineer',
                'company': 'TechCorp',
                'url': 'https://example.com/job1',
                'source': 'RemoteOK',
            },
            'evaluation': {
                'reason': 'Strong Python and AI background.',
                'strengths': ['Python expertise', 'AI experience'],
                'gaps': ['Missing Kubernetes'],
            },
            'ai_score': 92,
        },
        {
            'job': {
                'title': 'Frontend Developer',
                'company': 'WebCo',
                'url': 'https://example.com/job2',
                'source': 'Remotive',
            },
            'evaluation': {
                'reason': 'React fits the role.',
                'strengths': ['React skills'],
                'gaps': [],
            },
            'ai_score': 78,
        },
        {
            'job': {
                'title': 'Backend Engineer',
                'company': 'CloudOps',
                'url': 'https://example.com/job3',
                'source': 'RemoteOK',
            },
            'evaluation': {
                'reason': 'Decent match.',
                'strengths': ['Docker knowledge'],
                'gaps': ['No Go experience'],
            },
            'ai_score': 55,
        },
    ]


# ===== Tests: simple_match =====

class TestSimpleMatch:

    def test_all_skills_match_returns_100(self, resume, ai_job):
        resume_all = {'skills': ['python', 'ai', 'react']}
        score = simple_match(resume_all, ai_job)
        assert score == 100

    def test_no_skills_match_returns_zero(self, resume):
        job = {'title': 'COBOL Developer', 'description': 'COBOL mainframe', 'tags': ['cobol']}
        resume_no_match = {'skills': ['haskell', 'erlang']}
        score = simple_match(resume_no_match, job)
        assert score == 0

    def test_empty_skills_returns_zero(self, ai_job):
        score = simple_match({'skills': []}, ai_job)
        assert score == 0

    def test_partial_match_returns_proportional_score(self):
        resume = {'skills': ['python', 'java', 'cobol']}
        job = {'title': 'Python Dev', 'description': 'We use python only', 'tags': []}
        score = simple_match(resume, job)
        # 1 out of 3 skills match -> 33
        assert score == 33

    def test_score_is_capped_at_100(self):
        # Even with many repeated-looking matches, max is 100
        resume = {'skills': ['python'] * 5}
        job = {'title': 'Python Dev', 'description': 'python python python', 'tags': ['python']}
        score = simple_match(resume, job)
        assert score <= 100

    def test_case_insensitive_matching(self):
        resume = {'skills': ['Python', 'REACT']}
        job = {'title': 'Dev', 'description': 'python react experience', 'tags': []}
        score = simple_match(resume, job)
        assert score == 100

    def test_returns_integer(self, resume, ai_job):
        score = simple_match(resume, ai_job)
        assert isinstance(score, int)

    def test_no_skills_key_returns_zero(self, ai_job):
        score = simple_match({}, ai_job)
        assert score == 0

    def test_tags_are_included_in_matching(self):
        resume = {'skills': ['kubernetes']}
        job = {'title': 'DevOps', 'description': 'Cloud infrastructure', 'tags': ['kubernetes']}
        score = simple_match(resume, job)
        assert score == 100

    def test_score_range_is_0_to_100(self):
        resume = {'skills': ['python', 'rust', 'haskell', 'erlang']}
        job = {'title': 'Python Dev', 'description': 'python only', 'tags': []}
        score = simple_match(resume, job)
        assert 0 <= score <= 100


# ===== Tests: format_ai_message =====

class TestFormatAiMessage:

    def test_empty_jobs_returns_no_match_message(self, resume):
        result = format_ai_message(resume, [])
        assert 'Alice' in result
        assert '沒有找到匹配' in result

    def test_result_contains_job_title(self, resume, matched_jobs):
        result = format_ai_message(resume, matched_jobs)
        assert 'AI Engineer' in result

    def test_result_contains_company(self, resume, matched_jobs):
        result = format_ai_message(resume, matched_jobs)
        assert 'TechCorp' in result

    def test_result_contains_candidate_name(self, resume, matched_jobs):
        result = format_ai_message(resume, matched_jobs)
        assert 'Alice' in result

    def test_result_contains_job_count(self, resume, matched_jobs):
        result = format_ai_message(resume, matched_jobs)
        assert '3' in result

    def test_fire_emoji_for_score_90_plus(self, resume):
        high_score_job = [{
            'job': {'title': 'Top Job', 'company': 'BigCo', 'url': 'https://x.com', 'source': 'RemoteOK'},
            'evaluation': {'reason': 'Perfect.', 'strengths': ['Python'], 'gaps': []},
            'ai_score': 95,
        }]
        result = format_ai_message(resume, high_score_job)
        assert '🔥' in result

    def test_check_emoji_for_score_75_to_89(self, resume):
        mid_job = [{
            'job': {'title': 'Good Job', 'company': 'MidCo', 'url': 'https://x.com', 'source': 'Remotive'},
            'evaluation': {'reason': 'Good fit.', 'strengths': ['React'], 'gaps': []},
            'ai_score': 80,
        }]
        result = format_ai_message(resume, mid_job)
        assert '✅' in result

    def test_thumbs_up_for_score_50_to_74(self, resume):
        ok_job = [{
            'job': {'title': 'OK Job', 'company': 'OkCo', 'url': 'https://x.com', 'source': 'Remotive'},
            'evaluation': {'reason': 'Decent.', 'strengths': ['Docker'], 'gaps': []},
            'ai_score': 60,
        }]
        result = format_ai_message(resume, ok_job)
        assert '👍' in result

    def test_thinking_emoji_for_low_score(self, resume):
        low_job = [{
            'job': {'title': 'Unlikely Job', 'company': 'LowCo', 'url': 'https://x.com', 'source': 'RemoteOK'},
            'evaluation': {'reason': 'Weak.', 'strengths': [], 'gaps': ['Everything']},
            'ai_score': 30,
        }]
        result = format_ai_message(resume, low_job)
        assert '🤔' in result

    def test_result_contains_apply_link(self, resume, matched_jobs):
        result = format_ai_message(resume, matched_jobs)
        assert 'https://example.com/job1' in result

    def test_result_contains_strengths(self, resume, matched_jobs):
        result = format_ai_message(resume, matched_jobs)
        assert 'Python expertise' in result

    def test_default_name_when_no_name(self, matched_jobs):
        result = format_ai_message({}, matched_jobs)
        assert '求職者' in result


# ===== Tests: get_openai_client (no API key) =====

class TestGetOpenAIClient:

    def test_returns_none_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY if set
            env = {k: v for k, v in os.environ.items() if k != 'OPENAI_API_KEY'}
            with patch.dict(os.environ, env, clear=True):
                client = get_openai_client()
                assert client is None

    def test_evaluate_returns_default_when_no_client(self, resume, ai_job):
        with patch('src.ai_evaluator.get_openai_client', return_value=None):
            result = evaluate_match_with_ai(resume, ai_job)
        assert 'reason' in result
        assert 'strengths' in result
        assert 'gaps' in result
        assert 'ai_score' in result
        assert result['ai_score'] is None

    def test_evaluate_batch_returns_list(self, resume):
        jobs = [{'title': 'Dev', 'company': 'Co', 'description': 'python', 'tags': []}]
        with patch('src.ai_evaluator.get_openai_client', return_value=None):
            results = evaluate_batch(resume, jobs, top_n=1)
        assert isinstance(results, list)
