"""
職缺獲取器 - 從 RemoteOK API 抓取職缺
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

REMOTEOK_API = "https://remoteok.com/api"


def fetch_remoteok_jobs(tag: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """從 RemoteOK 抓取職缺"""
    url = REMOTEOK_API
    if tag:
        url = f"{REMOTEOK_API}?tag={tag}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        jobs = response.json()
        
        # 過濾掉 legal 和無效數據
        filtered = []
        for job in jobs:
            if job.get('slug') and job.get('company') and job.get('position'):
                job['title'] = job.pop('position')  # 統一欄位名
                # 優先使用 apply_url，否則用 url
                job['url'] = job.get('apply_url') or f"https://remoteok.com/l/{job['slug']}"
                filtered.append(job)
        
        return filtered[:limit]
    except Exception as e:
        print(f"Error fetching RemoteOK: {e}")
        return []


def fetch_ai_jobs(limit: int = 30) -> List[Dict]:
    """抓取 AI 相關職缺"""
    return fetch_remoteok_jobs('ai', limit)


def fetch_dev_jobs(limit: int = 30) -> List[Dict]:
    """抓取開發者職缺"""
    return fetch_remoteok_jobs('dev', limit)


def fetch_all_jobs(limit_per_tag: int = 20) -> List[Dict]:
    """抓取多標籤職缺"""
    tags = ['ai', 'python', 'javascript', 'react', 'golang', 'rust', 'devops', 'data', 'remote']
    all_jobs = []
    seen_ids = set()
    
    for tag in tags:
        jobs = fetch_remoteok_jobs(tag, limit_per_tag)
        for job in jobs:
            if job.get('id') not in seen_ids:
                seen_ids.add(job.get('id'))
                job['tag'] = tag
                all_jobs.append(job)
    
    return all_jobs


def save_jobs(jobs: List[Dict], filepath: str = 'jobs/latest.json'):
    """保存職缺到文件"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'fetched_at': datetime.now().isoformat(),
        'count': len(jobs),
        'jobs': jobs
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_jobs(filepath: str = 'jobs/latest.json') -> List[Dict]:
    """從文件加載職缺"""
    if not Path(filepath).exists():
        return fetch_all_jobs()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 檢查是否需要刷新（超過 6 小時）
    fetched_at = datetime.fromisoformat(data['fetched_at'])
    if datetime.now() - fetched_at > timedelta(hours=6):
        print("Jobs cache expired, refetching...")
        return fetch_all_jobs()
    
    return data.get('jobs', [])


def get_job_tags() -> List[str]:
    """取得熱門職缺標籤"""
    return [
        'ai', 'python', 'javascript', 'typescript', 'react', 
        'golang', 'rust', 'java', 'devops', 'data', 'machine-learning',
        'docker', 'kubernetes', 'aws', 'gcp', 'fullstack', 'remote'
    ]


if __name__ == '__main__':
    jobs = fetch_all_jobs()
    save_jobs(jobs)
    print(f"Fetched {len(jobs)} jobs")
