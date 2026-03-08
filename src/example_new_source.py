"""
範例：如何新增職缺來源

此檔案展示如何為職缺獵人專案新增新的資料來源。
"""

# ========== 範例：新增 Landing.Jobs ==========
# 注意：這是假設的 API，實際可能不存在
# 如要使用真實 API，請替換為實際的 URL

from src.fetcher import JobSourceAdapter, JobFetcher
from typing import List, Dict
import requests


class LandingJobsAdapter(JobSourceAdapter):
    """
    Landing.jobs 職缺來源範例
    
    使用方式：
    1. 複製此類別並修改為實際的 API
    2. 在 JobFetcher.ADAPTERS 中註冊
    
    例如：
        JobFetcher.register_adapter('LandingJobs', LandingJobsAdapter())
        jobs = JobFetcher.fetch_from('LandingJobs', 30)
    """
    name = "LandingJobs"
    api_url = "https://landing.jobs/api/v1/jobs"  # 假設的 API
    
    def fetch(self, limit: int = 50) -> List[Dict]:
        try:
            response = requests.get(
                self.api_url,
                params={'limit': limit},
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"  {self.name}: API returned {response.status_code}")
                return []
            
            data = response.json()
            jobs = data.get('jobs', [])
            
            filtered = []
            for job in jobs:
                if job.get('title') and job.get('company'):
                    filtered.append({
                        'id': job.get('id'),
                        'title': job.get('title'),
                        'company': job.get('company'),
                        'url': job.get('url'),
                        'description': job.get('description', ''),
                        'tags': job.get('tags', []),
                        'location': job.get('location') or 'Remote',
                        'source': self.name
                    })
            
            return filtered[:limit]
            
        except Exception as e:
            print(f"  {self.name} error: {e}")
            return []


# ========== 測試範例 ==========
if __name__ == '__main__':
    # 註冊新來源
    JobFetcher.register_adapter('LandingJobs', LandingJobsAdapter())
    
    # 使用新來源
    jobs = JobFetcher.fetch_from('LandingJobs', 10)
    print(f"LandingJobs fetched: {len(jobs)} jobs")
    
    # 或從所有來源抓取（包括新註冊的）
    all_jobs = JobFetcher.fetch_all()
    print(f"Total jobs from all sources: {len(all_jobs)}")
