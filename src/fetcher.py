"""
職缺獲取器 - 多來源
支持：RemoteOK, remote4me (WeWorkRemotely API 已失效)
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta


# ========== RemoteOK ==========
def fetch_remoteok_jobs(limit: int = 50) -> List[Dict]:
    """從 RemoteOK 抓取職缺"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Accept': 'application/json',
    }
    
    try:
        response = requests.get("https://remoteok.com/api", headers=headers, timeout=30)
        jobs = response.json()
        
        filtered = []
        for job in jobs:
            if job.get('slug') and job.get('company') and job.get('position'):
                job['title'] = job.pop('position')
                job['url'] = job.get('apply_url') or f"https://remoteok.com/l/{job['slug']}"
                job['source'] = 'RemoteOK'
                filtered.append(job)
        
        return filtered[:limit]
    except Exception as e:
        print(f"RemoteOK error: {e}")
        return []


# ========== remote4me ==========
def fetch_remote4me_jobs(limit: int = 30) -> List[Dict]:
    """從 remote4me 抓取職缺"""
    try:
        response = requests.get("https://remote4me.com/api/v1/jobs", timeout=15)
        if response.status_code != 200:
            return []
        
        jobs = response.json()
        
        filtered = []
        for job in jobs[:limit]:
            if job.get('title') and job.get('company'):
                filtered.append({
                    'id': job.get('id'),
                    'title': job.get('title'),
                    'company': job.get('company'),
                    'url': job.get('url', ''),
                    'description': job.get('description', ''),
                    'tags': job.get('tags', []),
                    'location': job.get('location') or 'Remote',
                    'source': 'remote4me'
                })
        
        return filtered
    except:
        return []


# ========== JustRemote ==========
def fetch_justremote_jobs(limit: int = 30) -> List[Dict]:
    """從 justremote.co 抓取職缺"""
    try:
        response = requests.get("https://justremote.co/api/v1/jobs", timeout=15)
        jobs = response.json()
        
        filtered = []
        for job in jobs[:limit]:
            if job.get('title'):
                filtered.append({
                    'id': job.get('id'),
                    'title': job.get('title'),
                    'company': job.get('company', {}).get('name') if isinstance(job.get('company'), dict) else job.get('company'),
                    'url': job.get('url'),
                    'description': job.get('description', ''),
                    'tags': job.get('tags', []),
                    'location': job.get('location') or 'Remote',
                    'source': 'JustRemote'
                })
        
        return filtered
    except:
        return []


# ========== Main ==========
def fetch_all_jobs(limit_per_source: int = 40) -> List[Dict]:
    """從多來源抓取職缺"""
    all_jobs = []
    seen_ids = set()
    
    sources = [
        ('RemoteOK', fetch_remoteok_jobs),
        ('remote4me', fetch_remote4me_jobs),
    ]
    
    print("📡 Fetching jobs from multiple sources...")
    
    for name, fetcher in sources:
        try:
            jobs = fetcher(limit_per_source)
            print(f"   - {name}: {len(jobs)} jobs")
            
            for job in jobs:
                unique_id = f"{job.get('source')}-{job.get('id')}"
                if unique_id not in seen_ids:
                    seen_ids.add(unique_id)
                    all_jobs.append(job)
        except Exception as e:
            print(f"   - {name}: failed ({e})")
    
    print(f"   Total: {len(all_jobs)} unique jobs")
    return all_jobs


def save_jobs(jobs: List[Dict], filepath: str = 'jobs/latest.json'):
    """保存職缺"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'fetched_at': datetime.now().isoformat(),
        'count': len(jobs),
        'jobs': jobs,
        'sources': list(set(j.get('source') for j in jobs))
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_jobs(filepath: str = 'jobs/latest.json') -> List[Dict]:
    """加載職缺"""
    if not Path(filepath).exists():
        return fetch_all_jobs()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fetched_at = datetime.fromisoformat(data['fetched_at'])
    if datetime.now() - fetched_at > timedelta(hours=6):
        print("Cache expired, refetching...")
        return fetch_all_jobs()
    
    return data.get('jobs', [])


if __name__ == '__main__':
    jobs = fetch_all_jobs()
    save_jobs(jobs)
    print(f"\n✅ Saved {len(jobs)} jobs")
