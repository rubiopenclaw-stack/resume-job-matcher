"""
Unit tests for fetcher.py
"""
import sys
import os
import json
import copy
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.fetcher import (
    JobSourceAdapter,
    RemoteOKAdapter,
    RemotiveAdapter,
    ArbeitnowAdapter,
    JobicyAdapter,
    HimalayasAdapter,
    JobFetcher,
    fetch_all_jobs,
    save_jobs,
    load_jobs,
)


# ===== Fixtures =====

SAMPLE_REMOTEOK_RESPONSE = [
    {"legal": "some header item"},  # first item is metadata, no slug
    {
        "id": "123",
        "slug": "python-dev-123",
        "position": "Senior Python Developer",
        "company": "TechCorp",
        "apply_url": "https://remoteok.com/l/python-dev-123",
        "description": "Python dev needed",
        "tags": ["python", "django"],
        "location": "Remote",
    },
    {
        "id": "456",
        "slug": "react-dev-456",
        "position": "React Developer",
        "company": "WebCo",
        "apply_url": "https://remoteok.com/l/react-dev-456",
        "description": "React dev needed",
        "tags": ["react", "typescript"],
        "location": "Remote",
    },
]

SAMPLE_REMOTIVE_RESPONSE = {
    "jobs": [
        {
            "id": 1001,
            "title": "ML Engineer",
            "company_name": "AILabs",
            "url": "https://remotive.com/job/1001",
            "description": "Machine learning engineer role",
            "tags": ["python", "ml"],
            "candidate_required_location": "Worldwide",
        },
        {
            "id": 1002,
            "title": "DevOps Engineer",
            "company_name": "CloudCo",
            "url": "https://remotive.com/job/1002",
            "description": "AWS DevOps role",
            "tags": ["aws", "docker", "kubernetes"],
            "candidate_required_location": "Remote",
        },
    ]
}


# ===== Tests: JobSourceAdapter normalize_job =====

class TestJobSourceAdapterNormalize:

    def test_normalize_job_required_fields(self):
        """normalize_job should produce all standard keys"""
        adapter = RemoteOKAdapter()
        raw = {
            'id': 'abc',
            'title': 'Dev',
            'company': 'Corp',
            'url': 'https://example.com',
            'description': 'test',
            'tags': ['python'],
            'location': 'Remote',
        }
        result = adapter.normalize_job(raw)
        for key in ('id', 'title', 'company', 'url', 'description', 'tags', 'location', 'source'):
            assert key in result

    def test_normalize_job_source_is_adapter_name(self):
        adapter = RemoteOKAdapter()
        result = adapter.normalize_job({'id': '1'})
        assert result['source'] == 'RemoteOK'

    def test_normalize_job_fallback_company_name(self):
        adapter = RemotiveAdapter()
        result = adapter.normalize_job({'company_name': 'FallbackCorp'})
        assert result['company'] == 'FallbackCorp'

    def test_normalize_job_includes_salary_fields(self):
        adapter = RemoteOKAdapter()
        raw = {'id': 'x', 'salary_min': 80000, 'salary_max': 120000}
        result = adapter.normalize_job(raw)
        assert result['salary_min'] == 80000
        assert result['salary_max'] == 120000


# ===== Tests: RemoteOKAdapter =====

class TestRemoteOKAdapter:

    def _mock_remoteok(self):
        """Return a fresh mock response with deep-copied data to avoid mutation"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = copy.deepcopy(SAMPLE_REMOTEOK_RESPONSE)
        return mock_resp

    def test_fetch_returns_list(self):
        adapter = RemoteOKAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remoteok()):
            jobs = adapter.fetch(limit=10)
        assert isinstance(jobs, list)

    def test_fetch_filters_header_item(self):
        """First item (no slug/company) should be filtered out"""
        adapter = RemoteOKAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remoteok()):
            jobs = adapter.fetch(limit=10)
        # Only 2 valid jobs (not the metadata entry)
        assert len(jobs) == 2

    def test_fetch_renames_position_to_title(self):
        adapter = RemoteOKAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remoteok()):
            jobs = adapter.fetch(limit=10)
        assert jobs[0].get('title') == 'Senior Python Developer'

    def test_fetch_respects_limit(self):
        adapter = RemoteOKAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remoteok()):
            jobs = adapter.fetch(limit=1)
        assert len(jobs) <= 1

    def test_fetch_returns_empty_on_exception(self):
        adapter = RemoteOKAdapter()
        with patch('src.fetcher.requests.get', side_effect=Exception("network error")):
            jobs = adapter.fetch()
        assert jobs == []

    def test_fetch_sets_source(self):
        adapter = RemoteOKAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remoteok()):
            jobs = adapter.fetch(limit=5)
        for job in jobs:
            assert job.get('source') == 'RemoteOK'


# ===== Tests: RemotiveAdapter =====

class TestRemotiveAdapter:

    def _mock_remotive(self):
        """Return a fresh mock response with deep-copied data to avoid mutation"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = copy.deepcopy(SAMPLE_REMOTIVE_RESPONSE)
        return mock_resp

    def test_fetch_returns_list(self):
        adapter = RemotiveAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remotive()):
            jobs = adapter.fetch(limit=10)
        assert isinstance(jobs, list)

    def test_fetch_returns_jobs_count(self):
        adapter = RemotiveAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remotive()):
            jobs = adapter.fetch(limit=10)
        assert len(jobs) == 2

    def test_fetch_renames_company_name(self):
        adapter = RemotiveAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remotive()):
            jobs = adapter.fetch(limit=10)
        assert jobs[0].get('company') == 'AILabs'

    def test_fetch_returns_empty_on_non_200(self):
        adapter = RemotiveAdapter()
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch('src.fetcher.requests.get', return_value=mock_resp):
            jobs = adapter.fetch()
        assert jobs == []

    def test_fetch_returns_empty_on_exception(self):
        adapter = RemotiveAdapter()
        with patch('src.fetcher.requests.get', side_effect=Exception("timeout")):
            jobs = adapter.fetch()
        assert jobs == []

    def test_fetch_sets_source(self):
        adapter = RemotiveAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_remotive()):
            jobs = adapter.fetch(limit=10)
        for job in jobs:
            assert job.get('source') == 'Remotive'


# ===== Tests: JobFetcher =====

class TestJobFetcher:

    def test_fetch_from_unknown_source_returns_empty(self):
        result = JobFetcher.fetch_from('NonExistent', 10)
        assert result == []

    def test_register_and_use_custom_adapter(self):
        class MockAdapter(JobSourceAdapter):
            name = "Mock"
            def fetch(self, limit=10):
                return [{'id': 'mock-1', 'title': 'Mock Job', 'source': 'Mock'}]

        JobFetcher.register_adapter('Mock', MockAdapter())
        result = JobFetcher.fetch_from('Mock', 10)
        assert len(result) == 1
        assert result[0]['id'] == 'mock-1'
        # cleanup
        del JobFetcher.ADAPTERS['Mock']

    def test_fetch_all_deduplicates(self):
        """fetch_all should not return duplicate jobs"""
        mock_jobs_1 = [{'id': 'j1', 'source': 'RemoteOK', 'slug': 'j1'}]
        mock_jobs_2 = [{'id': 'j1', 'source': 'RemoteOK', 'slug': 'j1'}]  # same id

        with patch.object(JobFetcher.ADAPTERS['RemoteOK'], 'fetch', return_value=mock_jobs_1), \
             patch.object(JobFetcher.ADAPTERS['Remotive'], 'fetch', return_value=mock_jobs_2):
            result = JobFetcher.fetch_all()

        ids = [j.get('id') for j in result]
        assert len(ids) == len(set(ids)), "fetch_all returned duplicates"

    def test_fetch_all_handles_adapter_failure(self):
        """fetch_all should still return other sources' jobs if one fails"""
        good_jobs = [{'id': 'g1', 'source': 'Remotive', 'slug': 'g1'}]

        with patch.object(JobFetcher.ADAPTERS['RemoteOK'], 'fetch', side_effect=Exception("fail")), \
             patch.object(JobFetcher.ADAPTERS['Remotive'], 'fetch', return_value=good_jobs):
            result = JobFetcher.fetch_all()

        sources = [j.get('source') for j in result]
        assert 'Remotive' in sources


# ===== Tests: save_jobs / load_jobs =====

class TestSaveLoadJobs:

    def test_save_jobs_creates_file(self, tmp_path):
        filepath = str(tmp_path / 'test_jobs.json')
        jobs = [{'id': '1', 'title': 'Dev', 'source': 'Test'}]
        save_jobs(jobs, filepath)
        assert Path(filepath).exists()

    def test_save_jobs_file_has_correct_structure(self, tmp_path):
        filepath = str(tmp_path / 'test_jobs.json')
        jobs = [{'id': '1', 'title': 'Dev', 'source': 'TestSource'}]
        save_jobs(jobs, filepath)
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        assert 'fetched_at' in data
        assert 'count' in data
        assert 'jobs' in data
        assert 'sources' in data
        assert data['count'] == 1

    def test_save_jobs_sources_list(self, tmp_path):
        filepath = str(tmp_path / 'test_jobs.json')
        jobs = [
            {'id': '1', 'source': 'RemoteOK'},
            {'id': '2', 'source': 'Remotive'},
        ]
        save_jobs(jobs, filepath)
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        assert set(data['sources']) == {'RemoteOK', 'Remotive'}

    def test_load_jobs_returns_list(self, tmp_path):
        filepath = str(tmp_path / 'latest.json')
        jobs = [{'id': '1', 'title': 'Dev', 'source': 'Test'}]
        save_jobs(jobs, filepath)
        loaded = load_jobs(filepath)
        assert isinstance(loaded, list)
        assert len(loaded) == 1

    def test_load_jobs_preserves_data(self, tmp_path):
        filepath = str(tmp_path / 'latest.json')
        jobs = [{'id': 'xyz', 'title': 'My Job', 'source': 'Test'}]
        save_jobs(jobs, filepath)
        loaded = load_jobs(filepath)
        assert loaded[0]['id'] == 'xyz'
        assert loaded[0]['title'] == 'My Job'

    def test_load_jobs_refetches_when_cache_expired(self, tmp_path):
        """load_jobs should call fetch_all_jobs when the file is older than 6 hours."""
        from unittest.mock import patch
        from datetime import datetime, timedelta

        filepath = str(tmp_path / 'latest.json')
        jobs = [{'id': '1', 'title': 'Old Job', 'source': 'Test'}]
        save_jobs(jobs, filepath)

        # Simulate cache being 7 hours old
        old_time = datetime.now() - timedelta(hours=7)
        new_jobs = [{'id': '2', 'title': 'Fresh Job', 'source': 'Test'}]

        with patch('src.fetcher.datetime') as mock_dt:
            mock_dt.now.return_value = datetime.now()
            mock_dt.fromisoformat.return_value = old_time
            with patch('src.fetcher.fetch_all_jobs', return_value=new_jobs) as mock_fetch:
                loaded = load_jobs(filepath)
                mock_fetch.assert_called_once()

    def test_load_jobs_uses_cache_when_fresh(self, tmp_path):
        """load_jobs should NOT call fetch_all_jobs when the file is fresh."""
        from unittest.mock import patch

        filepath = str(tmp_path / 'latest.json')
        jobs = [{'id': '1', 'title': 'Fresh Job', 'source': 'Test'}]
        save_jobs(jobs, filepath)

        with patch('src.fetcher.fetch_all_jobs') as mock_fetch:
            loaded = load_jobs(filepath)
            mock_fetch.assert_not_called()
        assert len(loaded) == 1

    def test_load_jobs_fetches_when_file_missing(self, tmp_path):
        """load_jobs should call fetch_all_jobs when file does not exist."""
        from unittest.mock import patch

        filepath = str(tmp_path / 'missing.json')
        new_jobs = [{'id': '99', 'title': 'New Job', 'source': 'Test'}]

        with patch('src.fetcher.fetch_all_jobs', return_value=new_jobs) as mock_fetch:
            loaded = load_jobs(filepath)
            mock_fetch.assert_called_once()
        assert len(loaded) == 1
        assert loaded[0]['id'] == '99'


# ===== Tests: JobicyAdapter =====

SAMPLE_JOBICY_RESPONSE = {
    "jobs": [
        {
            "id": 501,
            "url": "https://jobicy.com/jobs/501-senior-python",
            "jobTitle": "Senior Python Engineer",
            "companyName": "DataCo",
            "jobDescription": "Python engineering role worldwide",
            "jobExcerpt": "Python remote job",
            "jobIndustry": ["tech"],
            "jobType": ["full-time"],
            "jobGeo": "Worldwide",
            "jobLevel": "Senior",
            "annualSalaryMin": 90000,
            "annualSalaryMax": 130000,
            "salaryCurrency": "USD",
        },
        {
            "id": 502,
            "url": "https://jobicy.com/jobs/502-frontend",
            "jobTitle": "Frontend Developer",
            "companyName": "WebAgency",
            "jobDescription": "React developer needed",
            "jobExcerpt": "React remote",
            "jobIndustry": ["tech"],
            "jobType": ["full-time"],
            "jobGeo": "USA Only",
            "jobLevel": "Mid",
            "annualSalaryMin": 0,
            "annualSalaryMax": 0,
            "salaryCurrency": "USD",
        },
    ]
}


class TestJobicyAdapter:

    def _mock_jobicy(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = copy.deepcopy(SAMPLE_JOBICY_RESPONSE)
        return mock_resp

    def test_fetch_returns_list(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_jobicy()):
            jobs = adapter.fetch(limit=10)
        assert isinstance(jobs, list)

    def test_fetch_returns_correct_count(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_jobicy()):
            jobs = adapter.fetch(limit=10)
        assert len(jobs) == 2

    def test_fetch_maps_job_title(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_jobicy()):
            jobs = adapter.fetch(limit=10)
        assert jobs[0]['title'] == 'Senior Python Engineer'

    def test_fetch_maps_company_name(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_jobicy()):
            jobs = adapter.fetch(limit=10)
        assert jobs[0]['company'] == 'DataCo'

    def test_fetch_sets_salary_fields(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_jobicy()):
            jobs = adapter.fetch(limit=10)
        assert jobs[0]['salary_min'] == 90000
        assert jobs[0]['salary_max'] == 130000

    def test_fetch_sets_source(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_jobicy()):
            jobs = adapter.fetch(limit=10)
        for job in jobs:
            assert job['source'] == 'Jobicy'

    def test_fetch_returns_empty_on_non_200(self):
        adapter = JobicyAdapter()
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch('src.fetcher.requests.get', return_value=mock_resp):
            jobs = adapter.fetch()
        assert jobs == []

    def test_fetch_returns_empty_on_exception(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', side_effect=Exception('timeout')):
            jobs = adapter.fetch()
        assert jobs == []

    def test_fetch_respects_limit(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_jobicy()):
            jobs = adapter.fetch(limit=1)
        assert len(jobs) <= 1

    def test_fetch_includes_tags_from_industry(self):
        adapter = JobicyAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_jobicy()):
            jobs = adapter.fetch(limit=10)
        assert 'tech' in jobs[0]['tags']


# ===== Tests: HimalayasAdapter =====

SAMPLE_HIMALAYAS_RESPONSE = {
    "jobs": [
        {
            "id": "him-1",
            "title": "Staff ML Engineer",
            "company": {"name": "AIStartup"},
            "url": "https://himalayas.app/jobs/him-1",
            "description": "Machine learning engineer worldwide",
            "tags": ["python", "ml", "tensorflow"],
            "location": "Remote",
            "salary": {"min": 120000, "max": 180000, "currency": "USD"},
        },
        {
            "id": "him-2",
            "title": "DevOps Engineer",
            "company": {"name": "CloudFirm"},
            "url": "https://himalayas.app/jobs/him-2",
            "description": "Cloud DevOps role",
            "tags": ["aws", "docker", "kubernetes"],
            "location": "Remote",
            "salary": None,
        },
    ],
    "total": 2,
}


class TestHimalayasAdapter:

    def _mock_himalayas(self, last_page=True):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        data = copy.deepcopy(SAMPLE_HIMALAYAS_RESPONSE)
        if last_page:
            data['jobs'] = data['jobs']  # < page_size triggers break
        mock_resp.json.return_value = data
        return mock_resp

    def test_fetch_returns_list(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=10)
        assert isinstance(jobs, list)

    def test_fetch_returns_correct_count(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=10)
        assert len(jobs) == 2

    def test_fetch_maps_title(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=10)
        assert jobs[0]['title'] == 'Staff ML Engineer'

    def test_fetch_maps_company_name_from_dict(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=10)
        assert jobs[0]['company'] == 'AIStartup'

    def test_fetch_maps_salary(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=10)
        assert jobs[0]['salary_min'] == 120000
        assert jobs[0]['salary_max'] == 180000

    def test_fetch_handles_null_salary(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=10)
        assert jobs[1]['salary_min'] == 0
        assert jobs[1]['salary_max'] == 0

    def test_fetch_sets_source(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=10)
        for job in jobs:
            assert job['source'] == 'Himalayas'

    def test_fetch_includes_tags(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=10)
        assert 'python' in jobs[0]['tags']

    def test_fetch_returns_empty_on_non_200(self):
        adapter = HimalayasAdapter()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch('src.fetcher.requests.get', return_value=mock_resp):
            jobs = adapter.fetch()
        assert jobs == []

    def test_fetch_returns_empty_on_exception(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', side_effect=Exception('timeout')):
            jobs = adapter.fetch()
        assert jobs == []

    def test_fetch_respects_limit(self):
        adapter = HimalayasAdapter()
        with patch('src.fetcher.requests.get', return_value=self._mock_himalayas()):
            jobs = adapter.fetch(limit=1)
        assert len(jobs) <= 1


# ===== Tests: All adapters registered in JobFetcher =====

class TestAllAdaptersRegistered:

    def test_jobicy_in_adapters(self):
        assert 'Jobicy' in JobFetcher.ADAPTERS

    def test_himalayas_in_adapters(self):
        assert 'Himalayas' in JobFetcher.ADAPTERS

    def test_all_five_sources_registered(self):
        expected = {'RemoteOK', 'Remotive', 'Arbeitnow', 'Jobicy', 'Himalayas'}
        assert expected.issubset(set(JobFetcher.ADAPTERS.keys()))
