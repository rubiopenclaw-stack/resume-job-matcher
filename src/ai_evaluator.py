"""
AI 評估器 - 增強版
"""

import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def get_openai_client():
    """取得 OpenAI client"""
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    return openai.OpenAI(api_key=api_key, base_url=base_url)


def evaluate_match_with_ai(resume: Dict, job: Dict, model: str = None) -> Dict:
    """用 AI 評估履歷與職缺的匹配度"""
    client = get_openai_client()
    if not client:
        return {'reason': 'AI not available', 'strengths': [], 'gaps': [], 'ai_score': None}
    
    model = model or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    
    resume_skills = ', '.join(resume.get('skills', []))
    job_title = job.get('title', '')
    job_company = job.get('company', '')
    job_description = job.get('description', '')[:1500]
    job_tags = ', '.join(job.get('tags', []))
    job_source = job.get('source', '')
    
    # 增強版 prompt
    prompt = f"""你是一個專業的履歷評估專家。候選人正在找工作，請評估他與以下職缺的匹配程度。

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

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600
        )
        
        content = response.choices[0].message.content.strip()

        # 用 regex 擷取第一個 JSON 物件，容錯 markdown code block
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            raise json.JSONDecodeError("No JSON object found", content, 0)
        result = json.loads(match.group())
        
        return {
            'reason': result.get('match_reason', ''),
            'strengths': result.get('strengths', []),
            'gaps': result.get('gaps', []),
            'ai_score': result.get('ai_score')
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return {'reason': 'AI 評估失敗', 'strengths': [], 'gaps': [], 'ai_score': None}
    except Exception as e:
        print(f"AI evaluation error: {e}")
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
def simple_match(resume: Dict, job: Dict) -> int:
    """簡單關鍵字匹配"""
    resume_skills = set(s.lower() for s in resume.get('skills', []))
    job_text = f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
    
    matches = 0
    for skill in resume_skills:
        if skill in job_text:
            matches += 1
    
    if not resume_skills:
        return 0
    
    return min(int(matches / len(resume_skills) * 100), 100)


if __name__ == '__main__':
    test_resume = {'name': 'Test', 'skills': ['Python', 'AI', 'React']}
    test_job = {
        'title': 'AI Engineer',
        'company': 'TechCorp',
        'description': 'Looking for Python and AI developer',
        'tags': ['python', 'ai', 'machine learning']
    }
    
    result = evaluate_match_with_ai(test_resume, test_job)
    print(json.dumps(result, indent=2, ensure_ascii=False))
