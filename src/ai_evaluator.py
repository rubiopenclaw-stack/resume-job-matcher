"""
AI 評估器 - 用 GPT 分析履歷與職缺的匹配度
"""

import os
import json
from typing import Dict, List, Optional

# 嘗試導入 OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def get_openai_client() -> Optional[object]:
    """取得 OpenAI client"""
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENAI_BASE_URL')
    if not api_key:
        return None
    
    # 支援 OpenAI 兼容 API（如 DeepSeek, Azure）
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    
    return openai.OpenAI(api_key=api_key, base_url=base_url)


def evaluate_match_with_ai(resume: Dict, job: Dict, model: str = None) -> Dict:
    """
    用 AI 評估履歷與職缺的匹配度
    返回：match_reason, strengths, gaps, score
    """
    client = get_openai_client()
    if not client:
        return {
            'reason': 'AI not available',
            'strengths': [],
            'gaps': [],
            'ai_score': None
        }
    
    model = model or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    
    # 構建 prompt
    resume_skills = ', '.join(resume.get('skills', []))
    job_title = job.get('title', '')
    job_company = job.get('company', '')
    job_description = job.get('description', '')[:2000]  # 限制長度
    job_tags = ', '.join(job.get('tags', []))
    
    prompt = f"""你是一個專業的履歷評估專家。請分析以下履歷與職缺的匹配程度。

## 職缺資訊
- 職位：{job_title}
- 公司：{job_company}
- 標籤：{job_tags}
- 描述：{job_description}

## 履歷資訊
- 候選人：{resume.get('name')}
- 技能：{resume_skills}

請以 JSON 格式回覆：
{{
    "match_reason": "一句話說明為什麼這個候選人適合這個職位",
    "strengths": ["優勢1", "優勢2"],
    "gaps": ["可能缺乏的技能或經驗"],
    "ai_score": 0-100 的匹配分數
}}

只回覆 JSON，不要其他文字。"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        
        # 解析 JSON
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        result = json.loads(content.strip())
        
        return {
            'reason': result.get('match_reason', ''),
            'strengths': result.get('strengths', []),
            'gaps': result.get('gaps', []),
            'ai_score': result.get('ai_score')
        }
        
    except Exception as e:
        print(f"AI evaluation error: {e}")
        return {
            'reason': 'AI 評估失敗',
            'strengths': [],
            'gaps': [],
            'ai_score': None
        }


def evaluate_batch(resume: Dict, jobs: List[Dict], top_n: int = 5) -> List[Dict]:
    """
    批量評估取高分的職缺
    """
    results = []
    
    for job in jobs[:top_n * 2]:  # 評估更多，選高分
        evaluation = evaluate_match_with_ai(resume, job)
        
        results.append({
            'job': job,
            'evaluation': evaluation,
            'ai_score': evaluation.get('ai_score') or 0
        })
    
    # 按 AI 分數排序
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
        
        message += f"{i}. *{title}* @ {company}\n"
        message += f"   📊 AI匹配: {score}% | 🏷️ {source}\n"
        message += f"   💡 {eval_data.get('reason', '')[:60]}\n"
        
        if eval_data.get('strengths'):
            strengths = ' + '.join(eval_data['strengths'][:2])
            message += f"   ✅ {strengths}\n"
        
        message += f"   🔗 [申請]({job.get('url')})\n\n"
    
    return message


# ========== 備用：無 AI 的簡單評估 ==========
def simple_match(resume: Dict, job: Dict) -> int:
    """簡單關鍵字匹配"""
    resume_skills = set(resume.get('skills', []))
    job_text = f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
    
    matches = 0
    for skill in resume_skills:
        if skill.lower() in job_text:
            matches += 1
    
    if not resume_skills:
        return 0
    
    return min(int(matches / len(resume_skills) * 100), 100)


if __name__ == '__main__':
    # Test
    test_resume = {'name': 'Test', 'skills': ['Python', 'AI', 'React']}
    test_job = {
        'title': 'AI Engineer',
        'company': 'TechCorp',
        'description': 'Looking for Python and AI developer',
        'tags': ['python', 'ai', 'machine learning']
    }
    
    result = evaluate_match_with_ai(test_resume, test_job)
    print(json.dumps(result, indent=2, ensure_ascii=False))
