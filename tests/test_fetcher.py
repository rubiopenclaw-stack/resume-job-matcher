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
    Remote4MeAdapter,
    JustRemoteAdapter,
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

    def test_normalize_job_preserves_raw(self):
        adapter = RemoteOKAdapter()
        raw = {'id': 'x', 'custom_field': 'value'}
        result = adapter.normalize_job(raw)
        assert 'raw' in result
        assert result['raw']['custom_field'] == 'value'


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


# ===== Tests: Dead Adapters =====

class TestDeadAdapters:

    def test_remote4me_returns_empty(self):
        adapter = Remote4MeAdapter()
        assert adapter.fetch() == []

    def test_justremote_returns_empty(self):
        adapter = JustRemoteAdapter()
        assert adapter.fetch() == []


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
