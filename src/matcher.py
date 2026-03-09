"""
職缺匹配器 - 增強版
"""

import re
from collections import Counter
from typing import List, Dict, Tuple


SKILL_WEIGHTS = {
    # AI 相關 - 高權重
    'ai': 3, 'ml': 3, 'machine learning': 3, 'deep learning': 3,
    'llm': 4, 'gpt': 3, 'nlp': 3, 'gemma': 3, 'claude': 3,
    'langchain': 4, 'autogen': 4, 'crewai': 4, 'agent': 3,
    'rag': 4, 'vector db': 3, 'pinecone': 3, 'weaviate': 3,
    
    # 語言 - 中等權重
    'python': 2, 'javascript': 2, 'typescript': 2, 'java': 2,
    'go': 2, 'rust': 2, 'c++': 2, 'ruby': 2, 'php': 2,
    
    # 前端
    'react': 2, 'vue': 2, 'angular': 2, 'next.js': 3,
    'svelte': 2, 'tailwind': 2,
    
    # 後端
    'node.js': 2, 'django': 2, 'flask': 2, 'fastapi': 2,
    'spring': 2, 'express': 2, 'rails': 2,
    
    # 雲/DevOps
    'aws': 2, 'gcp': 2, 'azure': 2, 'docker': 2,
    'kubernetes': 3, 'terraform': 2, 'ci/cd': 2,
    
    # 數據庫
    'sql': 1, 'mysql': 1, 'postgresql': 2, 'mongodb': 2,
    'redis': 2, 'elasticsearch': 2,
}


def build_job_text(job: Dict) -> str:
    """建立職缺文字（用於匹配）"""
    return f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()


def calculate_match_score(resume_skills: List[str], job: Dict, job_text: str = None) -> float:
    """計算加權匹配分數"""
    if job_text is None:
        job_text = build_job_text(job)

    total_weight = 0
    matched_weight = 0

    for skill in resume_skills:
        skill_lower = skill.lower()

        # 檢查是否有權重（先直接查找，再做子字串掃描）
        weight = SKILL_WEIGHTS.get(skill_lower)
        if weight is None:
            for key, w in SKILL_WEIGHTS.items():
                if key in skill_lower or skill_lower in key:
                    weight = w
                    break
            else:
                weight = 1

        total_weight += weight

        if skill_lower in job_text:
            matched_weight += weight

    if total_weight == 0:
        return 0.0

    score = matched_weight / total_weight

    # 標題加成
    title = job.get('title', '').lower()
    for skill in resume_skills:
        if skill.lower() in title:
            score += 0.15

    return min(score, 1.0)


def filter_by_preference(resume: Dict, jobs: List[Dict]) -> List[Dict]:
    """根據偏好過濾職缺

    規則：
    - Remote 職缺永遠通過（bypass role & location 過濾）
    - 非 Remote 職缺需同時符合角色與地點偏好
    - 偏好未設定（空清單）視為全部通過
    """
    preferred_roles = [r.strip().lower() for r in resume.get('preferred_roles', []) if r.strip()]
    preferred_locations = [l.strip().lower() for l in resume.get('preferred_locations', []) if l.strip()]

    filtered = []

    for job in jobs:
        location = job.get('location', '').lower()

        # Remote 職缺永遠納入
        if 'remote' in location:
            filtered.append(job)
            continue

        title = job.get('title', '').lower()
        role_match = not preferred_roles or any(role in title for role in preferred_roles)
        location_match = (
            not preferred_locations
            or any(loc in location for loc in preferred_locations if loc != 'remote')
        )

        if role_match and location_match:
            filtered.append(job)

    return filtered


def match_jobs(resume: Dict, jobs: List[Dict], top_n: int = 10) -> List[Dict]:
    """匹配職缺"""
    resume_skills = resume.get('skills', [])
    resume_roles = resume.get('preferred_roles', [])
    
    # 先過濾
    filtered_jobs = filter_by_preference(resume, jobs)
    
    matched_jobs = []

    for job in filtered_jobs:
        job_text = build_job_text(job)
        score = calculate_match_score(resume_skills, job, job_text=job_text)

        if score > 0.05:  # 最低門檻
            matched_skills = [s for s in resume_skills if s.lower() in job_text]

            matched_jobs.append({
                'job': job,
                'score': round(score * 100, 1),
                'matched_skills': matched_skills
            })
    
    matched_jobs.sort(key=lambda x: x['score'], reverse=True)
    return matched_jobs[:top_n]


def generate_email_content(resume: Dict, matched_jobs: List[Dict]) -> str:
    """生成 Email 內容"""
    name = resume.get('name', '求職者')
    
    content = f"""# 🎯 今日職缺匹配報告

你好 {name}！

根據你的履歷技能，以下是今日精選職缺：

"""
    
    for i, item in enumerate(matched_jobs, 1):
        job = item['job']
        score = item['score']
        matched = item['matched_skills']
        
        content += f"""
## {i}. {job.get('title', 'N/A')}
- 🏢 公司：{job.get('company', 'N/A')}
- 💰 薪資：{job.get('salary', '未公開')}
- 📍 地點：{job.get('location', 'Remote')}
- 🔗 連結：{job.get('url', '')}
- 🎯 匹配度：{score}%
- ✨ 匹配技能：{', '.join(matched[:5]) if matched else 'N/A'}
"""
    
    content += """
---
💡 提示：請直接點擊連結申請，建議在申請時提及匹配的技能與經驗。

祝求職順利！🍀
"""
    
    return content


def get_summary_stats(matched_jobs: List[Dict]) -> Dict:
    """統計摘要"""
    if not matched_jobs:
        return {'count': 0, 'avg_score': 0, 'top_skills': []}
    
    scores = [item['score'] for item in matched_jobs]
    all_skills = []
    for item in matched_jobs:
        all_skills.extend(item['matched_skills'])
    
    skill_counts = Counter(all_skills)
    
    return {
        'count': len(matched_jobs),
        'avg_score': round(sum(scores) / len(scores), 1),
        'top_skills': skill_counts.most_common(5),
    }
