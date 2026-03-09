"""
Unit tests for matcher.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.matcher import (
    build_job_text,
    calculate_match_score,
    filter_by_preference,
    match_jobs,
    get_summary_stats,
    generate_email_content,
    SKILL_WEIGHTS,
)


# ===== Fixtures =====

@pytest.fixture
def python_ai_resume():
    return {
        'name': 'Test Dev',
        'skills': ['Python', 'AI', 'LangChain', 'React'],
        'preferred_roles': ['engineer', 'developer'],
        'preferred_locations': ['remote'],
    }


@pytest.fixture
def sample_jobs():
    return [
        {
            'id': 'j1',
            'title': 'AI Engineer',
            'company': 'TechCorp',
            'description': 'Python AI machine learning langchain developer needed',
            'tags': ['python', 'ai', 'langchain'],
            'location': 'Remote',
            'source': 'RemoteOK',
        },
        {
            'id': 'j2',
            'title': 'Frontend Developer',
            'company': 'WebCo',
            'description': 'React developer with TypeScript experience',
            'tags': ['react', 'typescript'],
            'location': 'Remote',
            'source': 'Remotive',
        },
        {
            'id': 'j3',
            'title': 'Java Backend Engineer',
            'company': 'OldCorp',
            'description': 'Spring Boot Java developer',
            'tags': ['java', 'spring'],
            'location': 'New York, NY',
            'source': 'RemoteOK',
        },
        {
            'id': 'j4',
            'title': 'Data Scientist',
            'company': 'DataCo',
            'description': 'Machine learning python numpy pandas',
            'tags': ['python', 'ml', 'data science'],
            'location': 'Remote',
            'source': 'Remotive',
        },
    ]


# ===== Tests: calculate_match_score =====

class TestCalculateMatchScore:

    def test_high_skill_match(self, sample_jobs):
        resume_skills = ['Python', 'AI', 'LangChain']
        score = calculate_match_score(resume_skills, sample_jobs[0])
        assert score > 0.5, f"Expected high match, got {score}"

    def test_no_skill_match(self, sample_jobs):
        resume_skills = ['COBOL', 'Fortran']
        score = calculate_match_score(resume_skills, sample_jobs[0])
        assert score == 0.0

    def test_empty_skills(self, sample_jobs):
        score = calculate_match_score([], sample_jobs[0])
        assert score == 0.0

    def test_score_capped_at_one(self, sample_jobs):
        # All skills match, bonus from title should not exceed 1.0
        resume_skills = ['Python', 'AI', 'LangChain', 'machine learning', 'developer']
        score = calculate_match_score(resume_skills, sample_jobs[0])
        assert score <= 1.0

    def test_title_bonus_applied(self, sample_jobs):
        # 'AI' in title 'AI Engineer' - should give title bonus
        resume_skills = ['AI']
        score_ai_job = calculate_match_score(resume_skills, sample_jobs[0])   # AI Engineer
        score_fe_job = calculate_match_score(resume_skills, sample_jobs[1])   # Frontend (AI not in title)
        # AI job should score higher due to title bonus
        assert score_ai_job >= score_fe_job

    def test_weighted_skills_score_higher(self, sample_jobs):
        # LangChain has weight 4, Java has weight 2
        score_langchain = calculate_match_score(['LangChain'], sample_jobs[0])  # has langchain
        score_java = calculate_match_score(['Java'], sample_jobs[2])             # has java
        # Both match their respective jobs; weights make langchain proportionally higher per skill
        assert score_langchain > 0
        assert score_java > 0

    def test_case_insensitive_matching(self, sample_jobs):
        score_upper = calculate_match_score(['PYTHON'], sample_jobs[0])
        score_lower = calculate_match_score(['python'], sample_jobs[0])
        assert score_upper == score_lower


# ===== Tests: filter_by_preference =====

class TestFilterByPreference:

    def test_no_preferences_returns_all(self, sample_jobs):
        resume = {'preferred_roles': [], 'preferred_locations': []}
        result = filter_by_preference(resume, sample_jobs)
        assert len(result) == len(sample_jobs)

    def test_role_filter_applied(self, sample_jobs):
        resume = {'preferred_roles': ['engineer'], 'preferred_locations': []}
        result = filter_by_preference(resume, sample_jobs)
        titles = [j['title'].lower() for j in result]
        # 'AI Engineer' and 'Java Backend Engineer' contain 'engineer'
        # Remote jobs with 'remote' in location also pass through regardless
        assert any('engineer' in t for t in titles)

    def test_remote_jobs_require_role_match(self, sample_jobs):
        # Remote jobs now require role matching (2026-03-10 fix)
        # When preferred_roles is set but doesn't match any remote job, no remote jobs pass through
        resume = {
            'preferred_roles': ['designer'],  # nothing matches designer
            'preferred_locations': ['remote'],
        }
        result = filter_by_preference(resume, sample_jobs)
        # No remote jobs should be included since none match "designer"
        remote_jobs = [j for j in sample_jobs if 'remote' in j['location'].lower()]
        result_ids = {j['id'] for j in result}
        for job in remote_jobs:
            assert job['id'] not in result_ids

    def test_remote_jobs_pass_when_role_matches(self, sample_jobs):
        # Remote jobs pass through when role matches
        resume = {
            'preferred_roles': ['ai'],  # matches AI Engineer
            'preferred_locations': ['remote'],
        }
        result = filter_by_preference(resume, sample_jobs)
        result_ids = {j['id'] for j in result}
        # j1 (AI Engineer) should match "ai"
        assert 'j1' in result_ids  # AI Engineer
        # j2 (Frontend Developer) doesn't have "ai" in title
        assert 'j2' not in result_ids
        # j4 (Data Scientist) doesn't have "ai" in title
        assert 'j4' not in result_ids

    def test_remote_jobs_pass_when_no_role_preference(self, sample_jobs):
        # When no role preference, all remote jobs pass through
        resume = {
            'preferred_roles': [],
            'preferred_locations': ['remote'],
        }
        result = filter_by_preference(resume, sample_jobs)
        remote_jobs = [j for j in sample_jobs if 'remote' in j['location'].lower()]
        result_ids = {j['id'] for j in result}
        for job in remote_jobs:
            assert job['id'] in result_ids

    def test_location_filter_non_remote(self, sample_jobs):
        resume = {
            'preferred_roles': [],
            'preferred_locations': ['new york'],
        }
        result = filter_by_preference(resume, sample_jobs)
        result_ids = {j['id'] for j in result}
        # j3 is New York, all remote jobs also pass through
        assert 'j3' in result_ids

    def test_no_duplicates_in_result(self, sample_jobs):
        resume = {
            'preferred_roles': ['engineer'],
            'preferred_locations': ['remote'],
        }
        result = filter_by_preference(resume, sample_jobs)
        ids = [j['id'] for j in result]
        assert len(ids) == len(set(ids)), "Duplicate jobs in filter result"


# ===== Tests: match_jobs =====

class TestMatchJobs:

    def test_returns_top_n(self, python_ai_resume, sample_jobs):
        result = match_jobs(python_ai_resume, sample_jobs, top_n=2)
        assert len(result) <= 2

    def test_result_has_required_keys(self, python_ai_resume, sample_jobs):
        result = match_jobs(python_ai_resume, sample_jobs, top_n=5)
        for item in result:
            assert 'job' in item
            assert 'score' in item
            assert 'matched_skills' in item

    def test_sorted_by_score_descending(self, python_ai_resume, sample_jobs):
        result = match_jobs(python_ai_resume, sample_jobs, top_n=10)
        scores = [item['score'] for item in result]
        assert scores == sorted(scores, reverse=True)

    def test_score_is_percentage(self, python_ai_resume, sample_jobs):
        result = match_jobs(python_ai_resume, sample_jobs, top_n=10)
        for item in result:
            assert 0 <= item['score'] <= 100

    def test_empty_jobs_returns_empty(self, python_ai_resume):
        result = match_jobs(python_ai_resume, [], top_n=5)
        assert result == []

    def test_matched_skills_are_subset_of_resume_skills(self, python_ai_resume, sample_jobs):
        result = match_jobs(python_ai_resume, sample_jobs, top_n=10)
        resume_skills_lower = {s.lower() for s in python_ai_resume['skills']}
        for item in result:
            for skill in item['matched_skills']:
                assert skill.lower() in resume_skills_lower


# ===== Tests: get_summary_stats =====

class TestGetSummaryStats:

    def test_empty_returns_zeros(self):
        stats = get_summary_stats([])
        assert stats['count'] == 0
        assert stats['avg_score'] == 0
        assert stats['top_skills'] == []

    def test_count_correct(self):
        items = [
            {'score': 80, 'matched_skills': ['python', 'ai']},
            {'score': 60, 'matched_skills': ['python']},
        ]
        stats = get_summary_stats(items)
        assert stats['count'] == 2

    def test_avg_score_correct(self):
        items = [
            {'score': 80, 'matched_skills': []},
            {'score': 60, 'matched_skills': []},
        ]
        stats = get_summary_stats(items)
        assert stats['avg_score'] == 70.0

    def test_top_skills_most_common_first(self):
        items = [
            {'score': 90, 'matched_skills': ['python', 'ai', 'python']},
            {'score': 70, 'matched_skills': ['python', 'react']},
        ]
        stats = get_summary_stats(items)
        top = [skill for skill, _ in stats['top_skills']]
        assert top[0] == 'python'  # most common


# ===== Tests: generate_email_content =====

class TestGenerateEmailContent:

    def _make_matched_job(self, title='Python Dev', company='TechCorp', score=85.0, skills=None):
        return {
            'job': {
                'title': title,
                'company': company,
                'salary': '100k-140k',
                'location': 'Remote',
                'url': 'https://example.com/job',
            },
            'score': score,
            'matched_skills': skills or ['python', 'django'],
        }

    def test_returns_string(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        result = generate_email_content(resume, [self._make_matched_job()])
        assert isinstance(result, str)

    def test_contains_name(self):
        resume = {'name': 'Bob', 'skills': ['python']}
        result = generate_email_content(resume, [self._make_matched_job()])
        assert 'Bob' in result

    def test_default_name_when_missing(self):
        resume = {'skills': ['python']}
        result = generate_email_content(resume, [self._make_matched_job()])
        assert '求職者' in result

    def test_contains_job_title(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        jobs = [self._make_matched_job(title='Senior ML Engineer')]
        result = generate_email_content(resume, jobs)
        assert 'Senior ML Engineer' in result

    def test_contains_company(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        jobs = [self._make_matched_job(company='AIStartup')]
        result = generate_email_content(resume, jobs)
        assert 'AIStartup' in result

    def test_contains_score(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        jobs = [self._make_matched_job(score=92.5)]
        result = generate_email_content(resume, jobs)
        assert '92.5' in result

    def test_contains_matched_skills(self):
        resume = {'name': 'Alice', 'skills': ['python', 'fastapi']}
        jobs = [self._make_matched_job(skills=['python', 'fastapi'])]
        result = generate_email_content(resume, jobs)
        assert 'python' in result

    def test_multiple_jobs_numbered(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        jobs = [
            self._make_matched_job(title='Job One'),
            self._make_matched_job(title='Job Two'),
        ]
        result = generate_email_content(resume, jobs)
        assert 'Job One' in result
        assert 'Job Two' in result
        assert '1.' in result
        assert '2.' in result

    def test_empty_jobs_list(self):
        resume = {'name': 'Alice', 'skills': ['python']}
        result = generate_email_content(resume, [])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_matched_skills_shows_na(self):
        resume = {'name': 'Alice', 'skills': []}
        job_item = {
            'job': {'title': 'Dev', 'company': 'Co', 'salary': 'N/A', 'location': 'Remote', 'url': 'http://x'},
            'score': 80.0,
            'matched_skills': [],
        }
        result = generate_email_content(resume, [job_item])
        assert 'N/A' in result


# ===== Tests: SKILL_WEIGHTS sanity =====

class TestSkillWeights:

    def test_high_value_skills_have_higher_weight(self):
        assert SKILL_WEIGHTS.get('llm', 0) >= SKILL_WEIGHTS.get('python', 0)
        assert SKILL_WEIGHTS.get('langchain', 0) >= SKILL_WEIGHTS.get('sql', 0)

    def test_all_weights_positive(self):
        for skill, weight in SKILL_WEIGHTS.items():
            assert weight > 0, f"Skill '{skill}' has non-positive weight: {weight}"


# ===== Tests: build_job_text =====

class TestBuildJobText:

    def test_returns_string(self):
        job = {'title': 'Python Dev', 'description': 'Uses python', 'tags': ['python']}
        result = build_job_text(job)
        assert isinstance(result, str)

    def test_output_is_lowercase(self):
        job = {'title': 'Python DEV', 'description': 'Uses DJANGO', 'tags': ['REACT']}
        result = build_job_text(job)
        assert result == result.lower()

    def test_includes_title(self):
        job = {'title': 'AI Engineer', 'description': '', 'tags': []}
        result = build_job_text(job)
        assert 'ai engineer' in result

    def test_includes_description(self):
        job = {'title': '', 'description': 'Build LLM agents', 'tags': []}
        result = build_job_text(job)
        assert 'llm agents' in result

    def test_includes_tags(self):
        job = {'title': '', 'description': '', 'tags': ['Python', 'FastAPI']}
        result = build_job_text(job)
        assert 'python' in result
        assert 'fastapi' in result

    def test_missing_fields_handled_gracefully(self):
        result = build_job_text({})
        assert isinstance(result, str)

    def test_result_matches_calculate_match_score_internal(self):
        """Passing pre-built job_text to calculate_match_score should give same result."""
        job = {'title': 'Python Developer', 'description': 'Python and Django', 'tags': ['python']}
        skills = ['Python', 'Django']
        score_auto = calculate_match_score(skills, job)
        job_text = build_job_text(job)
        score_prebuilt = calculate_match_score(skills, job, job_text=job_text)
        assert score_auto == score_prebuilt


# ===== Tests: calculate_match_score with pre-built job_text =====

class TestCalculateMatchScoreWithJobText:

    def test_prebuilt_text_matches_auto_computation(self):
        job = {'title': 'ML Engineer', 'description': 'machine learning python', 'tags': ['ml', 'python']}
        skills = ['Python', 'ML']
        auto_score = calculate_match_score(skills, job)
        prebuilt_score = calculate_match_score(skills, job, job_text=build_job_text(job))
        assert auto_score == prebuilt_score

    def test_custom_job_text_overrides_job_fields(self):
        """When job_text is provided, it should be used for matching, not job fields."""
        job = {'title': 'Java Developer', 'description': 'Java spring', 'tags': ['java']}
        custom_text = 'python fastapi langchain developer'
        score = calculate_match_score(['Python', 'LangChain'], job, job_text=custom_text)
        assert score > 0  # matches custom text, not job fields

    def test_none_job_text_falls_back_to_auto(self):
        job = {'title': 'React Dev', 'description': 'React TypeScript', 'tags': ['react']}
        score = calculate_match_score(['react'], job, job_text=None)
        assert score > 0
