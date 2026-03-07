"""
職缺匹配器 - 根據履歷技能匹配職缺
"""

import os
import json
import re
from typing import List, Dict, Tuple
from datetime import datetime


# 從履歷解析引入
try:
    from parser import extract_skills
except ImportError:
    # 內聯備用
    SKILL_KEYWORDS = {
        'python', 'javascript', 'typescript', 'java', 'go', 'rust', 'c++', 'ruby', 'php',
        'react', 'vue', 'angular', 'node.js', 'django', 'flask',
        'ai', 'ml', 'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp', 'llm',
        'aws', 'gcp', 'docker', 'kubernetes', 'devops',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
        'git', 'github', 'rest api', 'graphql',
    }
    def extract_skills(text):
        text_lower = text.lower()
        return [s for s in SKILL_KEYWORDS if s in text_lower]


def calculate_match_score(resume_skills: List[str], job: Dict) -> float:
    """計算履歷與職缺的匹配度"""
    job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('tags', '')}".lower()
    job_skills = extract_skills(job_text)
    
    if not job_skills:
        return 0.0
    
    resume_skills_set = set(resume_skills)
    job_skills_set = set(job_skills)
    
    # 計算重疊
    overlap = resume_skills_set & job_skills_set
    score = len(overlap) / len(job_skills_set)
    
    #加分：職缺標題有提到關鍵字
    title = job.get('title', '').lower()
    for skill in resume_skills:
        if skill in title:
            score += 0.1
    
    return min(score, 1.0)


def filter_by_location(jobs: List[Dict], preferred_locations: List[str]) -> List[Dict]:
    """根據偏好的地點篩選職缺"""
    if not preferred_locations:
        return jobs
    
    filtered = []
    for job in jobs:
        location = job.get('location', '').lower()
        # 遠端優先
        if 'remote' in location or job.get('remote'):
            filtered.append(job)
        else:
            # 檢查是否符合偏好
            for pref in preferred_locations:
                if pref.lower() in location:
                    filtered.append(job)
                    break
    
    return filtered


def match_jobs(resume: Dict, jobs: List[Dict], top_n: int = 10) -> List[Dict]:
    """匹配職缺並返回排名列表"""
    resume_skills = resume.get('skills', [])
    preferred_roles = resume.get('preferred_roles', [])
    preferred_locations = resume.get('preferred_locations', ['Remote'])
    
    matched_jobs = []
    
    for job in jobs:
        # 計算匹配度
        score = calculate_match_score(resume_skills, job)
        
        # 角色權重
        title_lower = job.get('title', '').lower()
        role_bonus = 0
        for role in preferred_roles:
            if role.lower() in title_lower:
                role_bonus += 0.2
                break
        
        total_score = score + role_bonus
        
        if total_score > 0.1:  # 最低門檻
            matched_jobs.append({
                'job': job,
                'score': round(total_score * 100, 1),
                'matched_skills': list(set(extract_skills(title_lower + ' ' + job.get('description', ''))) & set(resume_skills)),
            })
    
    # 按分數排序
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
    """取得統計摘要"""
    if not matched_jobs:
        return {'count': 0, 'avg_score': 0, 'top_skills': []}
    
    scores = [item['score'] for item in matched_jobs]
    all_skills = []
    for item in matched_jobs:
        all_skills.extend(item['matched_skills'])
    
    from collections import Counter
    skill_counts = Counter(all_skills)
    
    return {
        'count': len(matched_jobs),
        'avg_score': round(sum(scores) / len(scores), 1),
        'top_skills': skill_counts.most_common(5),
    }


if __name__ == '__main__':
    # Test
    test_resume = {
        'name': 'Test User',
        'skills': ['python', 'ai', 'react', 'typescript'],
        'preferred_roles': ['AI Engineer', 'Fullstack'],
        'preferred_locations': ['Remote', 'US']
    }
    
    test_jobs = [
        {'title': 'AI Engineer', 'company': 'TechCorp', 'location': 'Remote', 'tags': ['ai', 'python']},
        {'title': 'React Developer', 'company': 'WebInc', 'location': 'US', 'tags': ['react', 'javascript']},
    ]
    
    matched = match_jobs(test_resume, test_jobs)
    print(f"Matched: {len(matched)} jobs")
    for m in matched:
        print(f"  - {m['job']['title']}: {m['score']}%")
