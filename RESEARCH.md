# 職缺來源研究報告

## 研究日期
2026-03-08

## 研究結果

### GitHub Jobs
- **狀態**: ❌ 已停止服務
- **原因**: GitHub Jobs API 於 2019 年停止服務
- **驗證**: 嘗試連線 `jobs.github.com` → 連線被拒絕

### Indeed
- **狀態**: ❌ 無法直接使用
- **原因**: 需要付費的 Indeed API 訂閱，直接 scraping 會返回 403 Forbidden
- **建議**: 如需 Indeed 資料，可考慮使用第三方服務如 Indeed API (付費)

### 正常運作的來源
|來源|狀態|職缺數|說明|
|---|---|---|---|
|RemoteOK|✅ 正常|~99|主要遠端職缺來源|
|Remotive|✅ 正常|~23|免費 API，品質不錯|

### 已失效的來源
|來源|狀態|說明|
|---|---|---|
|remote4me|❌ 404|API 已失效|
|JustRemote|❌ HTML|返回網頁而非 JSON|
|WeWorkRemotely|❌ 404|API 已失效|

## Adapter 結構

已在 `src/fetcher.py` 中實作 Adapter 模式：

```python
class JobSourceAdapter(ABC):
    """職缺來源抽象基類"""
    name: str = "BaseAdapter"
    
    @abstractmethod
    def fetch(self, limit: int = 50) -> List[Dict]:
        pass
```

新增來源只需：
1. 繼承 `JobSourceAdapter`
2. 實作 `fetch()` 方法
3. 註冊到 `JobFetcher.ADAPTERS`

## 使用方式

```python
from src.fetcher import fetch_all_jobs, JobFetcher

# 從所有來源抓取
jobs = fetch_all_jobs()

# 從特定來源抓取
remoteok_jobs = JobFetcher.fetch_from('RemoteOK')
remotive_jobs = JobFetcher.fetch_from('Remotive')

# 新增來源
JobFetcher.register_adapter('新來源', MyAdapter())
```
