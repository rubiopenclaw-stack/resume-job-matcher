"""
履歷解析器 - 從 Markdown 履歷中提取技能關鍵字
"""

import re
import os
from pathlib import Path
from typing import Dict, List

# 技能關鍵字庫
SKILL_KEYWORDS = {
    # 程式語言
    'python', 'javascript', 'typescript', 'java', 'go', 'rust', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'scala',
    # 前端框架
    'react', 'vue', 'angular', 'next.js', 'nextjs', 'svelte', 'tailwind', 'html', 'css',
    # 後端框架
    'node.js', 'nodejs', 'django', 'flask', 'fastapi', 'spring', 'express', 'rails', 'laravel',
    # 數據/AI
    'ai', 'ml', 'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp', 'llm', 'gpt', 'chatgpt',
    'data science', 'data analysis', 'pandas', 'numpy', 'scikit-learn', 'keras',
    # 雲/DevOps
    'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'k8s', 'terraform', 'ci/cd', 'devops', 'linux',
    # 資料庫
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb',
    # 行動端
    'react native', 'flutter', 'ios', 'android', 'mobile',
    # 其他
    'git', 'github', 'rest api', 'graphql', 'microservices', 'agile', 'scrum',
    # AI Agent 相關
    'agent', 'agentic', 'langchain', 'autogen', 'crewai', 'tool use', 'multi-step',
    # AI 進階技術
    'rag', 'vector db', 'pinecone', 'weaviate', 'chroma', 'embedding', 'embeddings',
    'claude', 'gemma', 'llama', 'mistral', 'fine-tuning', 'prompt engineering',
    # AI 模型
    'deepseek', 'gemini', 'grok', 'minimax', 'megatron', 'o1', 'o3', 'o4',
    # AI 搜尋/推理工具
    'deepsearch', 'operator', 'haystack', 'openui', 'jina', 'reader',
    # AI 編碼 IDE/編輯器
    'cursor', 'windsurf', 'zed', 'zeditor', 'hyper', 'warptime',
    # AI 編碼助手
    'copilot', 'copilot-x', 'cody', 'tabnine', 'blackbox', 'amazon-q', 'aws-q',
    'gemini-code-assist', 'sourcegraph', 'qodo',
    # AI 程式生成工具
    'devin', 'v0', 'bolt', 'replit', 'replite', 'lovable', 'loveable', 'anysphere', 'cline',
    # 設計/生產力工具
    'figma', 'framer', 'raycast', 'noteable', 'excel', 'observable', 'julius',
    # 其他新興 AI 工具
    'roo', 'dot', 'saas', 'aisle', 'bolaval', 'sagehood', 'ivy', 'reverie',
    'goover', 'quey', 'ayfie', 'quillman', 'airtry', 'continents', 'polynomial', 'immutable',
    # AI 模型平台
    'together.ai', 'anyscale', 'infergo', 'fireworks', 'replicate', 'modal', 'runpod',
}

# 角色關鍵字
ROLE_KEYWORDS = {
    'ai engineer': ['ai', 'ml', 'machine learning', 'gpt', 'llm', 'nlp', 'deep learning'],
    'fullstack': ['react', 'node', 'python', 'javascript', 'typescript', 'fullstack'],
    'backend': ['python', 'java', 'go', 'rust', 'backend', 'api', 'microservices'],
    'frontend': ['react', 'vue', 'angular', 'javascript', 'typescript', 'frontend'],
    'devops': ['docker', 'kubernetes', 'aws', 'gcp', 'devops', 'ci/cd', 'terraform'],
    'data engineer': ['python', 'sql', 'data', 'etl', 'spark', 'airflow'],
}


def parse_resume(resume_path: str) -> Dict:
    """解析履歷文件"""
    with open(resume_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析 front matter
    front_matter = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    front_matter[key.strip()] = value.strip()
            content = parts[2]

    # 提取技能
    skills = extract_skills(content)
    
    # 推斷角色
    roles = infer_roles(skills)

    return {
        'name': front_matter.get('name', 'Anonymous'),
        'email': front_matter.get('email', ''),
        'preferred_roles': [r.strip() for r in front_matter.get('preferred_roles', '').split(',') if r.strip()],
        'preferred_locations': [l.strip() for l in front_matter.get('preferred_locations', 'Remote').split(',') if l.strip()],
        'skills': skills,
        'roles': roles,
        'raw_content': content,
    }


def extract_skills(text: str) -> List[str]:
    """從文字中提取技能關鍵字"""
    text_lower = text.lower()
    found_skills = set()
    
    for skill in SKILL_KEYWORDS:
        if skill in text_lower:
            found_skills.add(skill)
    
    return sorted(list(found_skills))


def infer_roles(skills: List[str]) -> List[str]:
    """根據技能推斷適合的角色"""
    skills_set = set(skills)
    matched_roles = []
    
    for role, required_skills in ROLE_KEYWORDS.items():
        # 如果有超過一半的技能匹配
        matches = sum(1 for s in required_skills if s in skills_set)
        if matches >= len(required_skills) / 2:
            matched_roles.append(role)
    
    return matched_roles if matched_roles else ['General Developer']


def parse_resume_content(text: str, filename: str = 'uploaded') -> Dict:
    """從文字內容解析履歷（供 API 上傳使用，不需要存檔）"""
    content = text
    front_matter = {}

    if content.strip().startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    front_matter[key.strip()] = value.strip()
            content = parts[2]

    skills = extract_skills(content)
    roles = infer_roles(skills)
    name = front_matter.get('name') or Path(filename).stem or 'Anonymous'

    return {
        'name': name,
        'email': front_matter.get('email', ''),
        'preferred_roles': [r.strip() for r in front_matter.get('preferred_roles', '').split(',') if r.strip()],
        'preferred_locations': [l.strip() for l in front_matter.get('preferred_locations', 'Remote').split(',') if l.strip()],
        'skills': skills,
        'roles': roles,
        'raw_content': content,
    }


def get_all_resumes(resumes_dir: str = 'resumes') -> List[Dict]:
    """取得所有履歷"""
    resumes = []
    resumes_path = Path(resumes_dir)
    
    if not resumes_path.exists():
        return []
    
    for resume_file in resumes_path.glob('*.md'):
        if resume_file.name == 'README.md':
            continue
        try:
            resume = parse_resume(str(resume_file))
            resume['filename'] = resume_file.name
            resumes.append(resume)
        except Exception as e:
            print(f"Error parsing {resume_file}: {e}")
    
    return resumes


if __name__ == '__main__':
    # Test
    resumes = get_all_resumes()
    for r in resumes:
        print(f"Name: {r['name']}")
        print(f"Skills: {r['skills']}")
        print(f"Roles: {r['roles']}")
        print()
