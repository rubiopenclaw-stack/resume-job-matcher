"""
AI 評估器 - 增強版
支援：Anthropic Claude（優先）、OpenAI（fallback）
"""

import os
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Singleton clients，避免每次呼叫都建立新連線池
_anthropic_client = None
_openai_client = None
_client_lock = threading.Lock()


def get_anthropic_client():
    """取得 Anthropic client（singleton）"""
    global _anthropic_client

    if not ANTHROPIC_AVAILABLE:
        return None

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None

    with _client_lock:
        if _anthropic_client is None:
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
        return _anthropic_client


def get_openai_client():
    """取得 OpenAI client（singleton）"""
    global _openai_client

    if not OPENAI_AVAILABLE:
        return None

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None

    with _client_lock:
        if _openai_client is None:
            base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            _openai_client = openai.OpenAI(api_key=api_key, base_url=base_url)
        return _openai_client


def _build_prompt(resume: Dict, job: Dict) -> str:
    """建立評估 prompt"""
    resume_skills = ', '.join(resume.get('skills', []))
    job_title = job.get('title', '')
    job_company = job.get('company', '')
    job_description = job.get('description', '')[:1500]
    job_tags = ', '.join(job.get('tags', []))
    job_source = job.get('source', '')

    return f"""你是一個專業的履歷評估專家。候選人正在找工作，請評估他與以下職缺的匹配程度。

## 職缺資訊
- 職位：{job_title}
- 公司：{job_company}
- 標籤：{job_tags}
- 來源：{job_source}
- 描述：{job_description}

## 候選人資訊
- 姓名：{resume.get('name')}
- 技能：{resume_skills}
- 偏好角色：{', '.join(resume.get('preferred_roles', []))}

請以 JSON 格式回覆：
{{
    "match_reason": "一句話說明為什麼這個候選人適合這個職缺，重點說明具體匹配點",
    "strengths": ["優勢1", "優勢2", "優勢3"],
    "gaps": ["可能缺乏的技能或經驗"],
    "ai_score": 0-100 的匹配分數
}}

只回覆 JSON。"""


def _parse_ai_response(content: str) -> Dict:
    """解析 AI 回應的 JSON"""
    decoder = json.JSONDecoder()
    for i, char in enumerate(content):
        if char == '{':
            try:
                result, _ = decoder.raw_decode(content, i)
                return result
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("No JSON object found", content, 0)


def evaluate_match_with_ai(resume: Dict, job: Dict, model: str = None) -> Dict:
    """用 AI 評估履歷與職缺的匹配度（優先使用 Claude，fallback 到 OpenAI）"""
    prompt = _build_prompt(resume, job)

    # 優先嘗試 Anthropic Claude
    anthropic_client = get_anthropic_client()
    if anthropic_client:
        claude_model = model or os.environ.get('ANTHROPIC_MODEL', 'claude-haiku-4-5-20251001')
        try:
            response = anthropic_client.messages.create(
                model=claude_model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text.strip()
            result = _parse_ai_response(content)
            return {
                'reason': result.get('match_reason', ''),
                'strengths': result.get('strengths', []),
                'gaps': result.get('gaps', []),
                'ai_score': result.get('ai_score'),
                'model': claude_model,
            }
        except json.JSONDecodeError as e:
            print(f"Claude JSON parse error: {e}")
        except Exception as e:
            print(f"Claude evaluation error: {e}, falling back to OpenAI...")

    # Fallback：OpenAI
    openai_client = get_openai_client()
    if not openai_client:
        return {'reason': 'AI not available', 'strengths': [], 'gaps': [], 'ai_score': None}

    openai_model = model or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    try:
        response = openai_client.chat.completions.create(
            model=openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600
        )

        content = response.choices[0].message.content.strip()

        result = _parse_ai_response(content)
        return {
            'reason': result.get('match_reason', ''),
            'strengths': result.get('strengths', []),
            'gaps': result.get('gaps', []),
            'ai_score': result.get('ai_score'),
            'model': openai_model,
        }

    except json.JSONDecodeError as e:
        print(f"OpenAI JSON parse error: {e}")
        return {'reason': 'AI 評估失敗', 'strengths': [], 'gaps': [], 'ai_score': None}
    except Exception as e:
        print(f"OpenAI evaluation error: {e}")
        return {'reason': 'AI 評估失敗', 'strengths': [], 'gaps': [], 'ai_score': None}


def evaluate_batch(resume: Dict, jobs: List[Dict], top_n: int = 5) -> List[Dict]:
    """批量評估 (並行版)"""
    candidates = jobs[:top_n * 2]

    def _evaluate_one(job):
        evaluation = evaluate_match_with_ai(resume, job)
        return {
            'job': job,
            'evaluation': evaluation,
            'ai_score': evaluation.get('ai_score') or 0,
        }

    results = []
    with ThreadPoolExecutor(max_workers=min(len(candidates), 5)) as executor:
        futures = [executor.submit(_evaluate_one, job) for job in candidates]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"evaluate_batch error: {e}")

    results.sort(key=lambda x: x['ai_score'], reverse=True)
    return results[:top_n]


def format_ai_message(resume: Dict, matched_jobs: List[Dict]) -> str:
    """格式化 AI 評估訊息"""
    name = resume.get('name', '求職者')
    
    if not matched_jobs:
        return f"❌ {name}，今日沒有找到匹配的職缺"
    
    message = f"🎯 *{name}* 今日 AI 匹配 {len(matched_jobs)} 個職缺\n\n"
    
    for i, item in enumerate(matched_jobs, 1):
        job = item['job']
        eval_data = item['evaluation']
        score = item['ai_score']
        
        title = job.get('title', 'N/A')[:25]
        company = job.get('company', 'N/A')[:15]
        source = job.get('source', 'N/A')
        
        # 評分emoji
        if score >= 90:
            emoji = "🔥"
        elif score >= 75:
            emoji = "✅"
        elif score >= 50:
            emoji = "👍"
        else:
            emoji = "🤔"
        
        message += f"{i}. *{title}* @ {company}\n"
        message += f"   {emoji} AI匹配: {score}% | 🏷️ {source}\n"
        message += f"   💡 {eval_data.get('reason', '')[:50]}\n"
        
        if eval_data.get('strengths'):
            strengths = ' + '.join(eval_data['strengths'][:2])
            message += f"   ✨ {strengths}\n"
        
        message += f"   🔗 [申請]({job.get('url')})\n\n"
    
    message += "💡 完整資訊請查看 GitHub Repo"
    
    return message


# ========== 簡單評估（無 AI）==========

# 技能別名字典：key 為標準名，value 為所有別名（含標準名自身）
_SKILL_ALIASES: Dict[str, List[str]] = {
    'javascript': ['javascript', 'js', 'ecmascript', 'es6', 'es2015', 'es2016', 'es2017', 'es2018', 'es2019', 'es2020'],
    'typescript': ['typescript', 'ts'],
    'python': ['python', 'py', 'python3', 'python2'],
    'react': ['react', 'reactjs', 'react.js', 'react js'],
    'vue': ['vue', 'vuejs', 'vue.js', 'vue js', 'vue3', 'vue2'],
    'angular': ['angular', 'angularjs', 'angular.js', 'angular js', 'angular2'],
    'node': ['node', 'nodejs', 'node.js', 'node js'],
    'next': ['next', 'nextjs', 'next.js', 'next js'],
    'nuxt': ['nuxt', 'nuxtjs', 'nuxt.js'],
    'express': ['express', 'expressjs', 'express.js'],
    'fastapi': ['fastapi', 'fast api', 'fast-api'],
    'django': ['django'],
    'flask': ['flask'],
    'kubernetes': ['kubernetes', 'k8s'],
    'postgresql': ['postgresql', 'postgres', 'psql'],
    'mongodb': ['mongodb', 'mongo'],
    'mysql': ['mysql'],
    'redis': ['redis'],
    'docker': ['docker'],
    'aws': ['aws', 'amazon web services', 'amazon aws'],
    'gcp': ['gcp', 'google cloud', 'google cloud platform'],
    'azure': ['azure', 'microsoft azure'],
    'graphql': ['graphql', 'graph ql'],
    'rest': ['rest', 'restful', 'rest api'],
    'tailwind': ['tailwind', 'tailwindcss', 'tailwind css'],
    'git': ['git', 'github', 'gitlab', 'bitbucket'],
    'ci/cd': ['ci/cd', 'cicd', 'ci cd', 'github actions', 'gitlab ci', 'jenkins'],
    'tensorflow': ['tensorflow', 'tf'],
    'pytorch': ['pytorch', 'torch'],
    'llm': ['llm', 'large language model', 'gpt', 'claude', 'gemini'],
    'machine learning': ['machine learning', 'ml', 'deep learning', 'dl'],
    'c++': ['c++', 'cpp', 'c plus plus'],
    'c#': ['c#', 'csharp', 'c sharp', 'dotnet', '.net'],
    'golang': ['golang', 'go'],
    'rust': ['rust', 'rustlang'],
    'kotlin': ['kotlin'],
    'swift': ['swift'],
    'php': ['php'],
    'ruby': ['ruby', 'ruby on rails', 'rails', 'ror'],
    'java': ['java', 'java ee', 'jakarta'],
    'spring': ['spring', 'spring boot', 'springboot'],
    'linux': ['linux', 'unix', 'ubuntu', 'debian', 'centos'],
    'html': ['html', 'html5'],
    'css': ['css', 'css3', 'sass', 'scss', 'less'],
}

# 建立反查表：任意別名 → 標準名
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for _canonical, _aliases in _SKILL_ALIASES.items():
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias] = _canonical


def _normalize_skill(skill: str) -> str:
    """將技能名稱正規化為標準形式（小寫 + 別名解析）"""
    lower = skill.lower().strip()
    return _ALIAS_TO_CANONICAL.get(lower, lower)


def _tokenize_job_text(job_text: str) -> set:
    """將職缺文字拆成 token 集合，並對每個 token 正規化"""
    # 同時保留原始 token 和正規化後的版本
    raw_tokens = set(re.split(r'[\s,/|;()\[\]]+', job_text.lower()))
    normalized = set(_ALIAS_TO_CANONICAL.get(t, t) for t in raw_tokens if t)
    return raw_tokens | normalized


def _skill_matches_job(canonical_skill: str, job_raw_text: str, job_tokens: set) -> bool:
    """判斷單一技能（已正規化）是否出現在職缺中"""
    # 1. 正規化後的 token 直接命中
    if canonical_skill in job_tokens:
        return True

    # 2. 原始技能的所有別名逐一嘗試子字串比對（處理複合詞如 'reactjs'）
    aliases = _SKILL_ALIASES.get(canonical_skill, [canonical_skill])
    for alias in aliases:
        # 完整子字串比對（避免 'go' 匹配 'golang' 造成誤判，要求邊界）
        pattern = r'(?<![a-z0-9])' + re.escape(alias) + r'(?![a-z0-9])'
        if re.search(pattern, job_raw_text):
            return True

    return False


def simple_match(resume: Dict, job: Dict) -> int:
    """改進版關鍵字匹配：支援別名、詞根變化、大小寫忽略"""
    raw_skills = resume.get('skills', [])
    if not raw_skills:
        return 0

    # 正規化 resume 技能（去重）
    canonical_skills = set(_normalize_skill(s) for s in raw_skills)

    job_raw_text = (
        f"{job.get('title', '')} {job.get('description', '')} "
        f"{' '.join(job.get('tags', []))}"
    ).lower()
    job_tokens = _tokenize_job_text(job_raw_text)

    matches = sum(
        1 for skill in canonical_skills
        if _skill_matches_job(skill, job_raw_text, job_tokens)
    )

    return min(int(matches / len(canonical_skills) * 100), 100)


if __name__ == '__main__':
    # ---- AI 評估測試 ----
    test_resume = {'name': 'Test', 'skills': ['Python', 'AI', 'React']}
    test_job = {
        'title': 'AI Engineer',
        'company': 'TechCorp',
        'description': 'Looking for Python and AI developer',
        'tags': ['python', 'ai', 'machine learning']
    }
    result = evaluate_match_with_ai(test_resume, test_job)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # ---- simple_match 單元測試 ----
    print("\n===== simple_match 測試 =====")

    _test_cases = [
        # (說明, resume_skills, job_fields, 預期分數下限)
        ("完全命中", ['Python', 'React'], {'title': 'React Python Dev', 'description': '', 'tags': []}, 100),
        ("別名：JS → JavaScript", ['JS'], {'title': 'JavaScript Engineer', 'description': '', 'tags': []}, 100),
        ("別名：Py → Python", ['Py'], {'title': 'Python Developer', 'description': '', 'tags': []}, 100),
        ("詞根：React → ReactJS", ['React'], {'title': 'ReactJS Frontend', 'description': '', 'tags': []}, 100),
        ("詞根：Node → Node.js", ['Node'], {'title': 'Node.js Backend', 'description': '', 'tags': []}, 100),
        ("K8s → Kubernetes", ['Kubernetes'], {'title': 'k8s DevOps', 'description': '', 'tags': []}, 100),
        ("大小寫忽略", ['PYTHON'], {'title': 'python engineer', 'description': '', 'tags': []}, 100),
        ("部分命中 50%", ['Python', 'React'], {'title': 'Python Backend', 'description': '', 'tags': []}, 50),
        ("完全不命中", ['Rust'], {'title': 'JavaScript Engineer', 'description': '', 'tags': []}, 0),
        ("空技能列表", [], {'title': 'Python Dev', 'description': '', 'tags': []}, 0),
        ("tag 命中", ['Docker'], {'title': 'Backend Dev', 'description': '', 'tags': ['docker', 'kubernetes']}, 100),
        ("防止 go 誤判 golang", ['golang'], {'title': 'Golang developer', 'description': 'go programming', 'tags': []}, 100),
        ("C# 別名 csharp", ['C#'], {'title': 'C# .NET Developer', 'description': 'csharp backend', 'tags': []}, 100),
    ]

    passed = 0
    for desc, skills, job_fields, min_expected in _test_cases:
        resume_obj = {'name': 'Tester', 'skills': skills}
        job_obj = {**job_fields}
        score = simple_match(resume_obj, job_obj)
        ok = score >= min_expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] {desc}: score={score} (expected>={min_expected})")

    print(f"\n結果：{passed}/{len(_test_cases)} 通過")
