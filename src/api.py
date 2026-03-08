"""
FastAPI Server - 職缺獵人 API
"""

import json
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

app = FastAPI(title="職缺獵人 API", version="1.0.0")

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


def load_jobs():
    """載入職缺資料"""
    if JOBS_FILE.exists():
        with open(JOBS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('jobs', [])
    return []


@app.get("/api/jobs")
async def get_jobs(
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    source: Optional[str] = Query(None, description="篩選來源"),
    location: Optional[str] = Query(None, description="篩選地點"),
    limit: int = Query(50, description="回傳數量限制")
):
    """取得職缺列表"""
    jobs = load_jobs()
    
    # 搜尋過濾
    if search:
        search_lower = search.lower()
        jobs = [
            j for j in jobs 
            if search_lower in j.get('title', '').lower()
            or search_lower in j.get('company', '').lower()
            or search_lower in ' '.join(j.get('tags', [])).lower()
        ]
    
    # 來源過濾
    if source:
        jobs = [j for j in jobs if j.get('source') == source]
    
    # 地點過濾
    if location:
        jobs = [j for j in jobs if location.lower() in j.get('location', '').lower()]
    
    # 限制數量
    jobs = jobs[:limit]
    
    return {
        "count": len(jobs),
        "jobs": jobs
    }


@app.get("/api/jobs/sources")
async def get_sources():
    """取得所有來源"""
    jobs = load_jobs()
    sources = list(set(j.get('source', 'Unknown') for j in jobs))
    return {"sources": sorted(sources)}


@app.get("/api/jobs/locations")
async def get_locations():
    """取得所有地點"""
    jobs = load_jobs()
    locations = list(set(j.get('location', 'Unknown') for j in jobs if j.get('location')))
    return {"locations": sorted(locations)[:20]}


@app.get("/api/jobs/tags")
async def get_tags():
    """取得熱門技能標籤"""
    jobs = load_jobs()
    from collections import Counter
    all_tags = []
    for job in jobs:
        all_tags.extend(job.get('tags', [])[:5])  # 每個 job 取前 5 個標籤
    tag_counts = Counter(all_tags)
    return {"tags": [tag for tag, _ in tag_counts.most_common(20)]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
