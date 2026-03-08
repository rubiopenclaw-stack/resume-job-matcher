"""
FastAPI Server - 職缺獵人 API (優化版)
- 加入記憶體快取
- 改善搜尋邏輯
- 支援 description 搜尋
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from functools import lru_cache
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
import threading

app = FastAPI(title="職缺獵人 API", version="1.1.0")

# CORS 允許 React 開發伺服器
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
            # 檢查快取是否過期
            age = datetime.now() - _cache['timestamp']
            if age < timedelta(minutes=CACHE_TTL_MINUTES):
                return _cache['jobs'], _cache['timestamp']
        
        # 重新載入
        jobs = _load_jobs_from_file()
        _cache['jobs'] = jobs
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
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    source: Optional[str] = Query(None, description="篩選來源"),
    location: Optional[str] = Query(None, description="篩選地點"),
    limit: int = Query(50, description="回傳數量限制"),
    refresh: bool = Query(False, description="強制重新整理快取")
):
    """取得職缺列表 (含快取)"""
    
    if refresh:
        invalidate_cache()
    
    jobs, cached_at = get_jobs_cache()
    
    # 搜尋過濾 (改善版本)
    if search:
        jobs = search_jobs(jobs, search)
    else:
        # 來源過濾
        if source:
            jobs = [j for j in jobs if j.get('source') == source]
        
        # 地點過濾
        if location:
            location_lower = location.lower()
            jobs = [j for j in jobs if location_lower in j.get('location', '').lower()]
    
    # 限制數量
    jobs = jobs[:limit]
    
    # 計算快取年齡
    cache_age = (datetime.now() - cached_at).seconds // 60
    
    return {
        "count": len(jobs),
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
    from collections import Counter
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
