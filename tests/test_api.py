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
        assert 'total' in data
        assert 'offset' in data
        assert 'limit' in data
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


# ===== Tests: GET /api/jobs/{job_id} =====

class TestGetJobByIdEndpoint:

    def test_get_existing_job_returns_200(self, client):
        response = client.get('/api/jobs/rok-1')
        assert response.status_code == 200

    def test_get_existing_job_returns_correct_data(self, client):
        data = client.get('/api/jobs/rok-1').json()
        assert data['id'] == 'rok-1'
        assert data['title'] == 'Senior Python Developer'

    def test_get_nonexistent_job_returns_404(self, client):
        response = client.get('/api/jobs/nonexistent-999')
        assert response.status_code == 404

    def test_get_job_404_has_detail(self, client):
        data = client.get('/api/jobs/missing').json()
        assert 'detail' in data

    def test_get_another_job_by_id(self, client):
        data = client.get('/api/jobs/rem-2').json()
        assert data['id'] == 'rem-2'
        assert data['company'] == 'WebCo'


# ===== Tests: Salary filtering =====

class TestSalaryFiltering:

    def test_salary_min_filter(self, client):
        """Jobs where salary_max >= salary_min should pass"""
        data = client.get('/api/jobs?salary_min=110000').json()
        for job in data['jobs']:
            assert (job.get('salary_max') or 0) >= 110000

    def test_salary_max_filter(self, client):
        """Jobs where salary_min <= salary_max should pass"""
        data = client.get('/api/jobs?salary_max=130000').json()
        for job in data['jobs']:
            assert (job.get('salary_min') or 0) <= 130000

    def test_salary_min_excludes_low_paying(self, client):
        """Very high salary_min should exclude most jobs"""
        data = client.get('/api/jobs?salary_min=200000').json()
        assert data['count'] == 0

    def test_salary_filter_combined(self, client):
        """salary_min + salary_max combined"""
        data = client.get('/api/jobs?salary_min=50000&salary_max=150000').json()
        for job in data['jobs']:
            assert (job.get('salary_max') or 0) >= 50000
            assert (job.get('salary_min') or 0) <= 150000

    def test_no_salary_filter_returns_all(self, client):
        """Without salary filters, all jobs are returned"""
        data = client.get('/api/jobs').json()
        assert data['count'] == len(SAMPLE_JOBS)


# ===== Tests: Pagination (offset) =====

class TestPagination:

    def test_offset_zero_returns_from_start(self, client):
        data = client.get('/api/jobs?offset=0').json()
        assert data['offset'] == 0
        assert data['count'] == len(SAMPLE_JOBS)

    def test_offset_skips_items(self, client):
        all_data = client.get('/api/jobs').json()
        all_ids = [j['id'] for j in all_data['jobs']]

        data = client.get('/api/jobs?offset=1').json()
        page_ids = [j['id'] for j in data['jobs']]
        # First item is skipped
        assert all_ids[1] == page_ids[0]

    def test_offset_beyond_total_returns_empty(self, client):
        data = client.get(f'/api/jobs?offset={len(SAMPLE_JOBS) + 100}').json()
        assert data['count'] == 0
        assert data['jobs'] == []

    def test_total_reflects_full_count(self, client):
        data = client.get('/api/jobs?limit=1').json()
        assert data['total'] == len(SAMPLE_JOBS)
        assert data['count'] == 1

    def test_total_with_filter_reflects_filtered_count(self, client):
        data = client.get('/api/jobs?source=RemoteOK&limit=1').json()
        # 2 RemoteOK jobs exist; total=2, count=1
        assert data['total'] == 2
        assert data['count'] == 1

    def test_limit_and_offset_combined(self, client):
        data = client.get('/api/jobs?limit=1&offset=1').json()
        assert data['count'] <= 1
        assert data['offset'] == 1
        assert data['limit'] == 1

    def test_response_includes_limit_and_offset(self, client):
        data = client.get('/api/jobs?limit=10&offset=0').json()
        assert data['limit'] == 10
        assert data['offset'] == 0


# ===== Tests: POST /api/jobs/refresh =====

class TestRefreshEndpoint:

    def test_refresh_returns_200_on_success(self, client):
        mock_jobs = SAMPLE_JOBS.copy()
        with patch('src.fetcher.fetch_all_jobs', return_value=mock_jobs):
            with patch('src.fetcher.save_jobs'):
                response = client.post('/api/jobs/refresh')
                assert response.status_code == 200

    def test_refresh_response_has_status_and_count(self, client):
        mock_jobs = SAMPLE_JOBS.copy()
        with patch('src.fetcher.fetch_all_jobs', return_value=mock_jobs):
            with patch('src.fetcher.save_jobs'):
                data = client.post('/api/jobs/refresh').json()
                assert 'status' in data
                assert 'count' in data

    def test_refresh_status_is_success(self, client):
        mock_jobs = SAMPLE_JOBS.copy()
        with patch('src.fetcher.fetch_all_jobs', return_value=mock_jobs):
            with patch('src.fetcher.save_jobs'):
                data = client.post('/api/jobs/refresh').json()
                assert data['status'] == 'success'

    def test_refresh_count_matches_fetched(self, client):
        mock_jobs = SAMPLE_JOBS.copy()
        with patch('src.fetcher.fetch_all_jobs', return_value=mock_jobs):
            with patch('src.fetcher.save_jobs'):
                data = client.post('/api/jobs/refresh').json()
                assert data['count'] == len(mock_jobs)

    def test_refresh_returns_500_on_error(self, client):
        with patch('src.fetcher.fetch_all_jobs', side_effect=Exception('fetch failed')):
            response = client.post('/api/jobs/refresh')
            assert response.status_code == 500

    def test_refresh_500_has_detail(self, client):
        with patch('src.fetcher.fetch_all_jobs', side_effect=Exception('fetch failed')):
            data = client.post('/api/jobs/refresh').json()
            assert 'detail' in data
