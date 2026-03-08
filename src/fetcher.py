"""
職缺獲取器 - 多來源 + Adapter 結構
支持：RemoteOK, remote4me, Remotive
"""

import os
import json
import requests
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# ========== Base Adapter ==========
class JobSourceAdapter(ABC):
    """職缺來源抽象基類"""
    
    name: str = "BaseAdapter"
    
    @abstractmethod
    def fetch(self, limit: int = 50) -> List[Dict]:
        """抓取職缺"""
        pass
    
    def normalize_job(self, job: Dict) -> Dict:
        """標準化職缺資料格式"""
        return {
            'id': job.get('id'),
            'title': job.get('title', 'Unknown'),
            'company': job.get('company', job.get('company_name', 'Unknown')),
            'url': job.get('url', job.get('apply_url', '')),
            'description': job.get('description', job.get('snippet', '')),
            'tags': job.get('tags', job.get('skills', [])),
            'location': job.get('location', 'Remote'),
            'source': self.name,
            'raw': job  # 保留原始資料
        }


# ========== RemoteOK Adapter ==========
class RemoteOKAdapter(JobSourceAdapter):
    """RemoteOK 職缺來源"""
    name = "RemoteOK"
    
    def fetch(self, limit: int = 50) -> List[Dict]:
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
                    job['source'] = self.name
                    filtered.append(job)
            
            return filtered[:limit]
        except Exception as e:
            print(f"  {self.name} error: {e}")
            return []


# ========== Remotive Adapter ==========
class RemotiveAdapter(JobSourceAdapter):
    """Remotive 職缺來源 (API 可用)"""
    name = "Remotive"
    
    def fetch(self, limit: int = 50) -> List[Dict]:
        try:
            response = requests.get(
                "https://remotive.com/api/remote-jobs",
                timeout=20
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            jobs = data.get('jobs', [])
            
            filtered = []
            for job in jobs:
                if job.get('title') and job.get('company_name'):
                    job['company'] = job.pop('company_name')
                    job['tags'] = job.get('tags', [])
                    job['source'] = self.name
                    filtered.append(job)
            
            return filtered[:limit]
        except Exception as e:
            print(f"  {self.name} error: {e}")
            return []


# ========== remote4me Adapter (API 已失效，返回 404) ==========
class Remote4MeAdapter(JobSourceAdapter):
    """remote4me 職缺來源 (API 已失效)"""
    name = "remote4me"
    
    def fetch(self, limit: int = 30) -> List[Dict]:
        # API 已失效，返回 404
        print(f"  {self.name}: API no longer available")
        return []


# ========== JustRemote Adapter (API 已失效) ==========
class JustRemoteAdapter(JobSourceAdapter):
    """JustRemote 職缺來源 (API 已失效，返回 HTML)"""
    name = "JustRemote"
    
    def fetch(self, limit: int = 30) -> List[Dict]:
        # API 已失效，返回 HTML 而非 JSON
        print(f"  {self.name}: API no longer available")
        return []


# ========== Job Fetcher (工廠模式) ==========
class JobFetcher:
    """職缺獲取器工廠"""
    
    # 可用的來源適配器
    ADAPTERS: Dict[str, JobSourceAdapter] = {
        'RemoteOK': RemoteOKAdapter(),
        'Remotive': RemotiveAdapter(),
        'remote4me': Remote4MeAdapter(),
        'JustRemote': JustRemoteAdapter(),
    }
    
    @classmethod
    def register_adapter(cls, name: str, adapter: JobSourceAdapter):
        """註冊新的來源適配器"""
        cls.ADAPTERS[name] = adapter
    
    @classmethod
    def fetch_from(cls, source_name: str, limit: int = 50) -> List[Dict]:
        """從指定來源抓取"""
        adapter = cls.ADAPTERS.get(source_name)
        if not adapter:
            print(f"  Unknown source: {source_name}")
            return []
        
        return adapter.fetch(limit)
    
    @classmethod
    def fetch_all(cls, sources: Optional[List[str]] = None, limit_per_source: int = 40) -> List[Dict]:
        """從多來源抓取職缺"""
        all_jobs = []
        seen_ids = set()
        
        # 如果沒指定來源，使用所有可用的
        if sources is None:
            sources = list(cls.ADAPTERS.keys())
        
        print("📡 Fetching jobs from multiple sources...")
        
        for name in sources:
            if name not in cls.ADAPTERS:
                print(f"   - {name}: unknown source (skipping)")
                continue
                
            try:
                jobs = cls.ADAPTERS[name].fetch(limit_per_source)
                print(f"   - {name}: {len(jobs)} jobs")
                
                for job in jobs:
                    unique_id = f"{job.get('source')}-{job.get('id', job.get('slug', ''))}"
                    if unique_id not in seen_ids:
                        seen_ids.add(unique_id)
                        all_jobs.append(job)
            except Exception as e:
                print(f"   - {name}: failed ({e})")
        
        print(f"   Total: {len(all_jobs)} unique jobs")
        return all_jobs


# ========== 便捷函數 (向後相容) ==========
def fetch_remoteok_jobs(limit: int = 50) -> List[Dict]:
    """從 RemoteOK 抓取職缺 (向後相容)"""
    return JobFetcher.fetch_from('RemoteOK', limit)


def fetch_remote4me_jobs(limit: int = 30) -> List[Dict]:
    """從 remote4me 抓取職缺 (向後相容)"""
    return JobFetcher.fetch_from('remote4me', limit)


def fetch_justremote_jobs(limit: int = 30) -> List[Dict]:
    """從 justremote.co 抓取職缺 (向後相容)"""
    return JobFetcher.fetch_from('JustRemote', limit)


def fetch_remotive_jobs(limit: int = 50) -> List[Dict]:
    """從 Remotive 抓取職缺 (新來源)"""
    return JobFetcher.fetch_from('Remotive', limit)


def fetch_all_jobs(limit_per_source: int = 40) -> List[Dict]:
    """從多來源抓取職缺"""
    return JobFetcher.fetch_all(limit_per_source=limit_per_source)


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


# ========== 主程式 ==========
if __name__ == '__main__':
    jobs = fetch_all_jobs()
    save_jobs(jobs)
    print(f"\n✅ Saved {len(jobs)} jobs")
    
    # 測試新增的 Remotive
    print("\n--- Testing new source: Remotive ---")
    remotive_jobs = fetch_remotive_jobs(10)
    print(f"Remotive fetched: {len(remotive_jobs)} jobs")
