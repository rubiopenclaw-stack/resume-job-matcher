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
        assert 'AI Engineer' in result['preferred_roles'] or 'Backend' in result['preferred_roles']

    def test_parse_extracts_preferred_locations(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        assert 'Remote' in result['preferred_locations']

    def test_parse_preferred_roles_no_leading_spaces(self, tmp_path):
        path = write_resume(tmp_path, 'test.md', SAMPLE_RESUME_MD)
        result = parse_resume(path)
        for role in result['preferred_roles']:
            assert role == role.strip(), f"Role has leading/trailing whitespace: {role!r}"

    def test_parse_empty_preferred_roles_returns_empty_list(self, tmp_path):
        content = "---\nname: Test\npreferred_roles: \n---\n## Skills\n- Python\n"
        path = write_resume(tmp_path, 'test.md', content)
        result = parse_resume(path)
        assert result['preferred_roles'] == []

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


# ===== Tests: AI 模型平台關鍵字 =====

class TestAIModelPlatformKeywords:

    def test_together_ai_detected(self):
        result = extract_skills("We use together.ai for inference")
        assert 'together.ai' in result

    def test_anyscale_detected(self):
        result = extract_skills("Deployed models on Anyscale platform")
        assert 'anyscale' in result

    def test_fireworks_detected(self):
        result = extract_skills("Fast inference via Fireworks API")
        assert 'fireworks' in result

    def test_replicate_detected(self):
        result = extract_skills("Hosted image generation models on Replicate")
        assert 'replicate' in result

    def test_modal_detected(self):
        result = extract_skills("Serverless GPU workloads with Modal")
        assert 'modal' in result

    def test_runpod_detected(self):
        result = extract_skills("Training runs on RunPod GPU cloud")
        assert 'runpod' in result

    def test_infergo_detected(self):
        result = extract_skills("Low-latency serving via infergo")
        assert 'infergo' in result

    def test_multiple_platforms_detected(self):
        result = extract_skills("Experience with together.ai, anyscale, and fireworks for LLM inference")
        assert 'together.ai' in result
        assert 'anyscale' in result
        assert 'fireworks' in result

    def test_platform_keywords_in_skill_keywords_set(self):
        platforms = {'together.ai', 'anyscale', 'infergo', 'fireworks', 'replicate', 'modal', 'runpod'}
        for platform in platforms:
            assert platform in SKILL_KEYWORDS, f"'{platform}' missing from SKILL_KEYWORDS"


# ===== Edge Case Tests =====

class TestEdgeCases:

    # 1) Special characters in skills
    def test_special_char_skills_detected(self):
        """Skills with special chars like c++, c#, ci/cd, node.js should be found."""
        text = "Expert in C++, C#, CI/CD pipelines, Node.js, and scikit-learn"
        result = extract_skills(text)
        assert 'c++' in result
        assert 'c#' in result
        assert 'ci/cd' in result
        assert 'node.js' in result
        assert 'scikit-learn' in result

    def test_skill_with_dot_in_platform_name(self):
        """together.ai contains a dot and should match exactly, not partially."""
        result_match = extract_skills("We use together.ai")
        result_no_match = extract_skills("We use together and ai separately")
        assert 'together.ai' in result_match
        assert 'together.ai' not in result_no_match

    # 2) Empty or malformed front matter
    def test_malformed_front_matter_no_closing_delimiter(self, tmp_path):
        """Front matter missing the closing --- should fall back to defaults."""
        content = "---\nname: Bob\nemail: bob@example.com\n## Skills\n- Python\n"
        path = (tmp_path / 'malformed.md')
        path.write_text(content, encoding='utf-8')
        result = parse_resume(str(path))
        # Without closing ---, parts split gives < 3 elements, so front_matter stays {}
        assert result['name'] == 'Anonymous'
        assert 'python' in result['skills']

    def test_front_matter_line_without_colon_is_skipped(self, tmp_path):
        """Lines in front matter without ':' should not crash the parser."""
        content = "---\nname: Carol\nthis line has no colon\nemail: carol@test.com\n---\n- React, TypeScript\n"
        path = (tmp_path / 'nocodon.md')
        path.write_text(content, encoding='utf-8')
        result = parse_resume(str(path))
        assert result['name'] == 'Carol'
        assert result['email'] == 'carol@test.com'

    def test_empty_front_matter_block(self, tmp_path):
        """An empty front matter block (--- immediately followed by ---) uses defaults."""
        content = "---\n---\n## Skills\n- Docker, Kubernetes\n"
        path = (tmp_path / 'empty_fm.md')
        path.write_text(content, encoding='utf-8')
        result = parse_resume(str(path))
        assert result['name'] == 'Anonymous'
        assert result['email'] == ''
        assert 'docker' in result['skills']

    # 3) Role inference with mixed case skills
    def test_infer_roles_mixed_case_skills_not_matched(self):
        """infer_roles compares lowercase; mixed-case inputs won't match and fall back to General Developer."""
        mixed_case_skills = ['Python', 'Machine Learning', 'LLM', 'GPT', 'NLP']
        result = infer_roles(mixed_case_skills)
        # Skills are uppercase so set membership fails → no role matches → General Developer
        assert result == ['General Developer']

    def test_infer_roles_lowercase_ai_skills_matched(self):
        """Lowercased skills (as produced by extract_skills) correctly infer ai engineer role."""
        lowercase_skills = ['python', 'machine learning', 'llm', 'gpt', 'nlp']
        result = infer_roles(lowercase_skills)
        assert 'ai engineer' in result
