"""
職缺獲取器 - 多來源 + Adapter 結構
支持：RemoteOK, Remotive, Arbeitnow
"""

import json
import requests
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# 絕對路徑，不受工作目錄影響
JOBS_DIR = Path(__file__).parent.parent / 'jobs'

# 兩層快取設計：
#   File Cache (fetcher.py): 6 小時，供 GitHub Actions main.py 使用
#   Memory Cache (api.py): 10 分鐘，供 FastAPI 端點使用，避免頻繁讀磁碟
FILE_CACHE_TTL_HOURS = 6


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
            'salary_min': job.get('salary_min') or 0,
            'salary_max': job.get('salary_max') or 0,
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
                    filtered.append(self.normalize_job(job))

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
                    filtered.append(self.normalize_job(job))

            return filtered[:limit]
        except Exception as e:
            print(f"  {self.name} error: {e}")
            return []


# ========== Arbeitnow Adapter ==========
class ArbeitnowAdapter(JobSourceAdapter):
    """Arbeitnow 職缺來源（免費，無需 API Key，歐洲遠端職缺）"""
    name = "Arbeitnow"

    def fetch(self, limit: int = 50) -> List[Dict]:
        try:
            response = requests.get(
                "https://arbeitnow.com/api/job-board-api",
                timeout=20
            )

            if response.status_code != 200:
                return []

            data = response.json()
            jobs = data.get('data', [])

            filtered = []
            for job in jobs:
                if job.get('title') and job.get('company_name'):
                    normalized = self.normalize_job({
                        'id': job.get('slug', ''),
                        'title': job.get('title', ''),
                        'company': job.get('company_name', ''),
                        'url': job.get('url', ''),
                        'description': job.get('description', ''),
                        'tags': job.get('tags', []),
                        'location': 'Remote' if job.get('remote') else job.get('location', ''),
                        'salary_min': 0,
                        'salary_max': 0,
                    })
                    filtered.append(normalized)

            return filtered[:limit]
        except Exception as e:
            print(f"  {self.name} error: {e}")
            return []


# ========== Job Fetcher (工廠模式) ==========
class JobFetcher:
    """職缺獲取器工廠"""
    
    # 可用的來源適配器（只保留有效的）
    ADAPTERS: Dict[str, JobSourceAdapter] = {
        'RemoteOK': RemoteOKAdapter(),
        'Remotive': RemotiveAdapter(),
        'Arbeitnow': ArbeitnowAdapter(),
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
        """從多來源並行抓取職缺"""
        all_jobs = []
        seen_ids = set()

        # 如果沒指定來源，使用所有可用的
        if sources is None:
            sources = list(cls.ADAPTERS.keys())

        valid_sources = [name for name in sources if name in cls.ADAPTERS]
        unknown_sources = [name for name in sources if name not in cls.ADAPTERS]
        for name in unknown_sources:
            print(f"   - {name}: unknown source (skipping)")

        print("📡 Fetching jobs from multiple sources (parallel)...")

        def _fetch_one(name: str):
            try:
                jobs = cls.ADAPTERS[name].fetch(limit_per_source)
                print(f"   - {name}: {len(jobs)} jobs")
                return name, jobs
            except Exception as e:
                print(f"   - {name}: failed ({e})")
                return name, []

        with ThreadPoolExecutor(max_workers=len(valid_sources) or 1) as executor:
            futures = {executor.submit(_fetch_one, name): name for name in valid_sources}
            results = [future.result() for future in as_completed(futures)]

        for _, jobs in results:
            for job in jobs:
                unique_id = f"{job.get('source')}-{job.get('id', job.get('slug', ''))}"
                if unique_id not in seen_ids:
                    seen_ids.add(unique_id)
                    all_jobs.append(job)

        print(f"   Total: {len(all_jobs)} unique jobs")
        return all_jobs


# ========== 便捷函數 ==========
def fetch_all_jobs(limit_per_source: int = 40) -> List[Dict]:
    """從多來源抓取職缺"""
    return JobFetcher.fetch_all(limit_per_source=limit_per_source)


def save_jobs(jobs: List[Dict], filepath: Path = None):
    """保存職缺（預設使用絕對路徑）"""
    filepath = Path(filepath) if filepath else JOBS_DIR / 'latest.json'
    filepath.parent.mkdir(parents=True, exist_ok=True)

    data = {
        'fetched_at': datetime.now().isoformat(),
        'count': len(jobs),
        'jobs': jobs,
        'sources': sorted({j.get('source') for j in jobs if j.get('source')}),
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_jobs(filepath: Path = None) -> List[Dict]:
    """加載職缺（預設使用絕對路徑）"""
    filepath = Path(filepath) if filepath else JOBS_DIR / 'latest.json'

    if not filepath.exists():
        return fetch_all_jobs()

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fetched_at = datetime.fromisoformat(data['fetched_at'])
    if datetime.now() - fetched_at > timedelta(hours=FILE_CACHE_TTL_HOURS):
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
    remotive_jobs = JobFetcher.fetch_from('Remotive', 10)
    print(f"Remotive fetched: {len(remotive_jobs)} jobs")
