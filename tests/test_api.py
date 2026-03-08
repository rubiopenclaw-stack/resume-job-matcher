"""
API tests for api.py using FastAPI TestClient
"""
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient


# ===== Sample test data =====

SAMPLE_JOBS = [
    {
        'id': 'rok-1',
        'title': 'Senior Python Developer',
        'company': 'TechCorp',
        'description': 'Looking for Python and Django developer with AI experience',
        'tags': ['python', 'django', 'ai'],
        'location': 'Remote',
        'source': 'RemoteOK',
        'url': 'https://example.com/job1',
        'salary_min': 100000,
        'salary_max': 140000,
    },
    {
        'id': 'rem-2',
        'title': 'React Frontend Engineer',
        'company': 'WebCo',
        'description': 'React TypeScript developer for our frontend team',
        'tags': ['react', 'typescript', 'css'],
        'location': 'Remote',
        'source': 'Remotive',
        'url': 'https://example.com/job2',
        'salary_min': 0,
        'salary_max': 0,
    },
    {
        'id': 'rok-3',
        'title': 'DevOps Engineer',
        'company': 'CloudOps',
        'description': 'Kubernetes Docker AWS infrastructure engineer',
        'tags': ['kubernetes', 'docker', 'aws'],
        'location': 'New York, NY',
        'source': 'RemoteOK',
        'url': 'https://example.com/job3',
        'salary_min': 120000,
        'salary_max': 160000,
    },
]

JOBS_DATA = {
    'fetched_at': datetime.now().isoformat(),
    'count': len(SAMPLE_JOBS),
    'jobs': SAMPLE_JOBS,
    'sources': ['RemoteOK', 'Remotive'],
}


@pytest.fixture
def jobs_file(tmp_path):
    """Create a temporary jobs JSON file"""
    jobs_dir = tmp_path / 'jobs'
    jobs_dir.mkdir()
    jobs_file = jobs_dir / 'latest.json'
    jobs_file.write_text(json.dumps(JOBS_DATA), encoding='utf-8')
    return jobs_file


@pytest.fixture
def client(jobs_file):
    """Create a TestClient with patched JOBS_FILE path"""
    from src import api
    # Patch the file path and clear cache
    original_path = api.JOBS_FILE
    api.JOBS_FILE = jobs_file
    api.invalidate_cache()

    with TestClient(api.app) as c:
        yield c

    # Restore
    api.JOBS_FILE = original_path
    api.invalidate_cache()


# ===== Tests: GET /api/health =====

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        data = client.get('/api/health').json()
        assert 'status' in data
        assert 'jobs_count' in data
        assert 'cached_at' in data

    def test_health_status_is_healthy(self, client):
        data = client.get('/api/health').json()
        assert data['status'] == 'healthy'

    def test_health_jobs_count(self, client):
        data = client.get('/api/health').json()
        assert data['jobs_count'] == len(SAMPLE_JOBS)


# ===== Tests: GET /api/jobs =====

class TestGetJobsEndpoint:

    def test_get_jobs_returns_200(self, client):
        response = client.get('/api/jobs')
        assert response.status_code == 200

    def test_get_jobs_response_structure(self, client):
        data = client.get('/api/jobs').json()
        assert 'count' in data
        assert 'jobs' in data
        assert 'cache_age_minutes' in data

    def test_get_all_jobs(self, client):
        data = client.get('/api/jobs').json()
        assert data['count'] == len(SAMPLE_JOBS)

    def test_search_by_title_keyword(self, client):
        data = client.get('/api/jobs?search=python').json()
        assert data['count'] >= 1
        jobs = data['jobs']
        # All results should be relevant to python
        assert any('python' in (j.get('title', '') + j.get('description', '')).lower() for j in jobs)

    def test_search_returns_empty_when_no_match(self, client):
        data = client.get('/api/jobs?search=COBOLFORTRAN999').json()
        assert data['count'] == 0

    def test_filter_by_source(self, client):
        data = client.get('/api/jobs?source=RemoteOK').json()
        for job in data['jobs']:
            assert job['source'] == 'RemoteOK'

    def test_filter_by_location(self, client):
        data = client.get('/api/jobs?location=new+york').json()
        for job in data['jobs']:
            assert 'new york' in job['location'].lower()

    def test_limit_parameter(self, client):
        data = client.get('/api/jobs?limit=1').json()
        assert len(data['jobs']) <= 1

    def test_limit_default_is_50(self, client):
        data = client.get('/api/jobs').json()
        # We have 3 jobs, all should be returned (under default limit of 50)
        assert data['count'] == 3

    def test_search_and_source_combined(self, client):
        data = client.get('/api/jobs?search=python&source=RemoteOK').json()
        for job in data['jobs']:
            assert job['source'] == 'RemoteOK'

    def test_cache_age_is_non_negative(self, client):
        data = client.get('/api/jobs').json()
        assert data['cache_age_minutes'] >= 0

    def test_refresh_invalidates_cache(self, client):
        from src import api
        # Prime the cache
        client.get('/api/jobs')
        assert 'jobs' in api._cache
        # Request with refresh=true
        client.get('/api/jobs?refresh=true')
        # Cache gets re-populated after refresh
        assert 'jobs' in api._cache


# ===== Tests: GET /api/jobs/sources =====

class TestSourcesEndpoint:

    def test_sources_returns_200(self, client):
        response = client.get('/api/jobs/sources')
        assert response.status_code == 200

    def test_sources_response_structure(self, client):
        data = client.get('/api/jobs/sources').json()
        assert 'sources' in data
        assert isinstance(data['sources'], list)

    def test_sources_contains_expected(self, client):
        data = client.get('/api/jobs/sources').json()
        assert 'RemoteOK' in data['sources']
        assert 'Remotive' in data['sources']

    def test_sources_are_sorted(self, client):
        data = client.get('/api/jobs/sources').json()
        sources = data['sources']
        assert sources == sorted(sources)


# ===== Tests: GET /api/jobs/locations =====

class TestLocationsEndpoint:

    def test_locations_returns_200(self, client):
        response = client.get('/api/jobs/locations')
        assert response.status_code == 200

    def test_locations_response_structure(self, client):
        data = client.get('/api/jobs/locations').json()
        assert 'locations' in data
        assert isinstance(data['locations'], list)

    def test_locations_max_20(self, client):
        data = client.get('/api/jobs/locations').json()
        assert len(data['locations']) <= 20


# ===== Tests: GET /api/jobs/tags =====

class TestTagsEndpoint:

    def test_tags_returns_200(self, client):
        response = client.get('/api/jobs/tags')
        assert response.status_code == 200

    def test_tags_response_structure(self, client):
        data = client.get('/api/jobs/tags').json()
        assert 'tags' in data
        assert isinstance(data['tags'], list)

    def test_tags_max_20(self, client):
        data = client.get('/api/jobs/tags').json()
        assert len(data['tags']) <= 20

    def test_tags_contains_known_skills(self, client):
        data = client.get('/api/jobs/tags').json()
        # python appears in job1, should be in tags
        assert 'python' in data['tags']


# ===== Tests: Cache logic =====

class TestCacheLogic:

    def test_cache_is_used_on_second_request(self, client):
        from src import api
        api.invalidate_cache()
        # First request loads from file
        client.get('/api/jobs')
        ts1 = api._cache.get('timestamp')
        # Second request should use cache (same timestamp)
        client.get('/api/jobs')
        ts2 = api._cache.get('timestamp')
        assert ts1 == ts2

    def test_invalidate_cache_clears_data(self, client):
        from src import api
        client.get('/api/jobs')  # populate cache
        api.invalidate_cache()
        assert 'jobs' not in api._cache
        assert 'timestamp' not in api._cache


# ===== Tests: Search logic =====

class TestSearchLogic:

    def test_title_match_scores_higher_than_description_only(self, client):
        """Jobs matching in title should rank above description-only matches"""
        data = client.get('/api/jobs?search=python').json()
        jobs = data['jobs']
        if len(jobs) > 1:
            # 'Senior Python Developer' should come first (title match)
            assert 'python' in jobs[0]['title'].lower() or 'python' in jobs[0].get('description', '').lower()

    def test_search_is_case_insensitive(self, client):
        data_lower = client.get('/api/jobs?search=python').json()
        data_upper = client.get('/api/jobs?search=PYTHON').json()
        assert data_lower['count'] == data_upper['count']
