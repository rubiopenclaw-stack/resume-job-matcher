"""
Unit tests for parser.py - resume parsing and skill extraction
"""
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.parser import (
    parse_resume,
    extract_skills,
    infer_roles,
    get_all_resumes,
    SKILL_KEYWORDS,
    ROLE_KEYWORDS,
)


# ===== Helpers =====

def write_resume(tmp_path, filename, content):
    f = tmp_path / filename
    f.write_text(content, encoding='utf-8')
    return str(f)


SAMPLE_RESUME_MD = """\
---
name: Alice Chen
email: alice@example.com
preferred_roles: AI Engineer, Backend
preferred_locations: Remote, Taipei
---

## 技能

- Python, FastAPI, Docker
- LLM, LangChain, RAG
- PostgreSQL, Redis
- AWS, Kubernetes
"""

MINIMAL_RESUME_MD = """\
## 技能
- JavaScript, React
"""


# ===== Tests: extract_skills =====

class TestExtractSkills:

    def test_returns_list(self):
        result = extract_skills("python react aws")
        assert isinstance(result, list)

    def test_finds_known_skill(self):
        result = extract_skills("I know Python very well")
        assert 'python' in result

    def test_case_insensitive(self):
        result = extract_skills("REACT and TypeScript")
        assert 'react' in result
        assert 'typescript' in result

    def test_no_skills_returns_empty(self):
        result = extract_skills("hello world no tech here xyz")
        assert result == []

    def test_multi_word_skill(self):
        result = extract_skills("machine learning is great")
        assert 'machine learning' in result

    def test_result_is_sorted(self):
        result = extract_skills("python react aws docker")
        assert result == sorted(result)

    def test_no_duplicates(self):
        result = extract_skills("python python python")
        assert len(result) == len(set(result))

    def test_all_returned_skills_are_in_keyword_set(self):
        result = extract_skills("python react kubernetes faketech999")
        for skill in result:
            assert skill in SKILL_KEYWORDS


# ===== Tests: infer_roles =====

class TestInferRoles:

    def test_returns_list(self):
        result = infer_roles(['python', 'react'])
        assert isinstance(result, list)

    def test_empty_skills_returns_general(self):
        result = infer_roles([])
        assert result == ['General Developer']

    def test_ai_skills_infer_ai_role(self):
        result = infer_roles(['python', 'machine learning', 'llm', 'gpt', 'nlp'])
        assert 'ai engineer' in result

    def test_frontend_skills_infer_frontend_role(self):
        result = infer_roles(['react', 'javascript', 'typescript', 'frontend'])
        assert 'frontend' in result

    def test_devops_skills_infer_devops_role(self):
        result = infer_roles(['docker', 'kubernetes', 'aws', 'terraform', 'ci/cd'])
        assert 'devops' in result

    def test_unmatched_skills_return_general(self):
        result = infer_roles(['ruby', 'rails'])
        assert 'General Developer' in result

    def test_multiple_roles_possible(self):
        # Enough backend skills + enough ai engineer skills to trigger both roles
        result = infer_roles(['python', 'java', 'go', 'rust', 'api', 'microservices', 'machine learning', 'llm', 'gpt', 'nlp'])
        assert len(result) >= 2


# ===== Tests: parse_resume =====

class TestParseResume:

    def test_parse_returns_dict(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        assert isinstance(result, dict)

    def test_parse_extracts_name_from_front_matter(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        assert result['name'] == 'Alice Chen'

    def test_parse_extracts_email(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        assert result['email'] == 'alice@example.com'

    def test_parse_extracts_preferred_roles(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        roles = [r.strip() for r in result['preferred_roles']]
        assert 'AI Engineer' in roles or 'Backend' in roles

    def test_parse_extracts_preferred_locations(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        locs = [l.strip() for l in result['preferred_locations']]
        assert 'Remote' in locs

    def test_parse_extracts_skills(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        assert isinstance(result['skills'], list)
        assert 'python' in result['skills']

    def test_parse_infers_roles(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        assert isinstance(result['roles'], list)
        assert len(result['roles']) > 0

    def test_parse_includes_raw_content(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        assert 'raw_content' in result

    def test_parse_no_front_matter_uses_defaults(self, tmp_path):
        path = write_resume(tmp_path, 'minimal.md', MINIMAL_RESUME_MD)
        result = parse_resume(path)
        assert result['name'] == 'Anonymous'
        assert result['email'] == ''

    def test_parse_no_front_matter_still_extracts_skills(self, tmp_path):
        path = write_resume(tmp_path, 'minimal.md', MINIMAL_RESUME_MD)
        result = parse_resume(path)
        assert 'javascript' in result['skills']
        assert 'react' in result['skills']

    def test_required_keys_present(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        for key in ('name', 'email', 'preferred_roles', 'preferred_locations', 'skills', 'roles', 'raw_content'):
            assert key in result


# ===== Tests: get_all_resumes =====

class TestGetAllResumes:

    def test_empty_dir_returns_empty(self, tmp_path):
        result = get_all_resumes(str(tmp_path))
        assert result == []

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        result = get_all_resumes(str(tmp_path / 'nonexistent'))
        assert result == []

    def test_returns_parsed_resumes(self, tmp_path):
        write_resume(tmp_path, 'alice.md', SAMPLE_RESUME_MD)
        result = get_all_resumes(str(tmp_path))
        assert len(result) == 1

    def test_multiple_resumes(self, tmp_path):
        write_resume(tmp_path, 'alice.md', SAMPLE_RESUME_MD)
        write_resume(tmp_path, 'bob.md', MINIMAL_RESUME_MD)
        result = get_all_resumes(str(tmp_path))
        assert len(result) == 2

    def test_readme_is_excluded(self, tmp_path):
        write_resume(tmp_path, 'README.md', '# readme')
        write_resume(tmp_path, 'alice.md', SAMPLE_RESUME_MD)
        result = get_all_resumes(str(tmp_path))
        # README.md excluded
        assert len(result) == 1

    def test_each_result_has_filename(self, tmp_path):
        write_resume(tmp_path, 'alice.md', SAMPLE_RESUME_MD)
        result = get_all_resumes(str(tmp_path))
        assert result[0].get('filename') == 'alice.md'

    def test_only_md_files_parsed(self, tmp_path):
        write_resume(tmp_path, 'alice.md', SAMPLE_RESUME_MD)
        (tmp_path / 'notes.txt').write_text('not a resume')
        result = get_all_resumes(str(tmp_path))
        assert len(result) == 1
