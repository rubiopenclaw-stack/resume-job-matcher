"""
FastAPI Server - 職缺獵人 API (優化版)
- 加入記憶體快取
- 改善搜尋邏輯
- 支援 description 搜尋
"""

import json
import os
from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
import threading

app = FastAPI(title="職缺獵人 API", version="1.2.0")

# CORS：預設允許本地開發伺服器，可透過環境變數擴充（如 Cloudflare Tunnel）
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_cors_origins = os.environ.get('CORS_ORIGINS', _default_origins).split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 資料路徑
JOBS_FILE = Path(__file__).parent.parent / "jobs" / "latest.json"

# 快取配置
CACHE_TTL_MINUTES = 10  # 快取有效時間
_cache: Dict = {}
_cache_lock = threading.Lock()


def _load_jobs_from_file() -> List[Dict]:
    """從檔案載入職缺資料"""
    if JOBS_FILE.exists():
        with open(JOBS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('jobs', [])
    return []


def get_jobs_cache() -> tuple[List[Dict], datetime]:
    """取得快取的職缺資料與時間"""
    with _cache_lock:
        if 'jobs' in _cache and 'timestamp' in _cache:
            age = datetime.now() - _cache['timestamp']
            if age < timedelta(minutes=CACHE_TTL_MINUTES):
                return _cache['jobs'], _cache['timestamp']

        # 重新載入並建立 id 索引（O(1) 查詢）
        jobs = _load_jobs_from_file()
        _cache['jobs'] = jobs
        _cache['jobs_by_id'] = {str(j.get('id', '')): j for j in jobs if j.get('id')}
        _cache['timestamp'] = datetime.now()
        return jobs, _cache['timestamp']


def invalidate_cache():
    """清除快取"""
    with _cache_lock:
        _cache.clear()


def search_jobs(jobs: List[Dict], search: str) -> List[Dict]:
    """搜尋職缺 - 改善版本
    
    搜尋範圍：
    - title (權重高)
    - company (權重高)
    - tags (權重中)
    - description (權重低)
    """
    if not search:
        return jobs
    
    search_lower = search.lower()
    results = []
    
    for job in jobs:
        score = 0
        title = job.get('title', '').lower()
        company = job.get('company', '').lower()
        tags = ' '.join(job.get('tags', [])).lower()
        description = job.get('description', '').lower()[:500]  # 限制長度優化效能
        
        # 權重計算
        if search_lower in title:
            score += 10
            if title.startswith(search_lower):
                score += 5  # 標題開頭匹配加分
        if search_lower in company:
            score += 8
        if search_lower in tags:
            score += 3
        if search_lower in description:
            score += 1
        
        if score > 0:
            results.append((score, job))
    
    # 按分數排序
    results.sort(key=lambda x: x[0], reverse=True)
    return [job for _, job in results]


@app.get("/api/jobs")
async def get_jobs(
    search: Optional[str] = Query(None, max_length=100, description="搜尋關鍵字"),
    source: Optional[str] = Query(None, description="篩選來源"),
    location: Optional[str] = Query(None, description="篩選地點"),
    salary_min: Optional[int] = Query(None, description="最低薪資過濾"),
    salary_max: Optional[int] = Query(None, description="最高薪資過濾"),
    limit: int = Query(50, ge=1, le=200, description="回傳數量限制"),
    offset: int = Query(0, ge=0, description="分頁偏移量"),
    refresh: bool = Query(False, description="強制重新整理快取")
):
    """取得職缺列表 (含快取)"""

    if refresh:
        invalidate_cache()

    jobs, cached_at = get_jobs_cache()

    # 來源過濾（先套用，再搜尋）
    if source:
        jobs = [j for j in jobs if j.get('source') == source]

    # 地點過濾
    if location:
        location_lower = location.lower()
        jobs = [j for j in jobs if location_lower in j.get('location', '').lower()]

    # 薪資過濾（單次迭代同時套用 min/max）
    if salary_min is not None or salary_max is not None:
        jobs = [
            j for j in jobs
            if (salary_min is None or (j.get('salary_max') or 0) >= salary_min)
            and (salary_max is None or (j.get('salary_min') or 0) <= salary_max)
        ]

    # 搜尋過濾
    if search:
        jobs = search_jobs(jobs, search)

    # 計算總數（分頁前）
    total = len(jobs)

    # 分頁
    jobs = jobs[offset:offset + limit]

    # 計算快取年齡
    cache_age = (datetime.now() - cached_at).seconds // 60

    return {
        "total": total,
        "count": len(jobs),
        "offset": offset,
        "limit": limit,
        "cache_age_minutes": cache_age,
        "jobs": jobs
    }


@app.get("/api/jobs/sources")
async def get_sources():
    """取得所有來源"""
    jobs, _ = get_jobs_cache()
    sources = list(set(j.get('source', 'Unknown') for j in jobs))
    return {"sources": sorted(sources)}


@app.get("/api/jobs/locations")
async def get_locations():
    """取得所有地點"""
    jobs, _ = get_jobs_cache()
    locations = list(set(j.get('location', 'Unknown') for j in jobs if j.get('location')))
    return {"locations": sorted(locations)[:20]}


@app.get("/api/jobs/tags")
async def get_tags():
    """取得熱門技能標籤"""
    jobs, _ = get_jobs_cache()
    all_tags = []
    for job in jobs:
        all_tags.extend(job.get('tags', [])[:5])
    tag_counts = Counter(all_tags)
    return {"tags": [tag for tag, _ in tag_counts.most_common(20)]}



@app.post("/api/jobs/refresh")
async def refresh_jobs():
    """手動觸發職缺重新整理"""
    try:
        invalidate_cache()
        from src.fetcher import fetch_all_jobs, save_jobs
        jobs = fetch_all_jobs()
        save_jobs(jobs)
        invalidate_cache()  # 重新載入新資料
        return {"status": "success", "count": len(jobs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """取得單一職缺詳情（O(1) 索引查詢）"""
    get_jobs_cache()  # 確保快取已建立
    with _cache_lock:
        jobs_by_id = _cache.get('jobs_by_id', {})
    job = jobs_by_id.get(job_id)
    if job:
        return job
    raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")


@app.get("/api/health")
async def health_check():
    """健康檢查"""
    jobs, cached_at = get_jobs_cache()
    return {
        "status": "healthy",
        "jobs_count": len(jobs),
        "cached_at": cached_at.isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
