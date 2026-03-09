# 職缺獵人優化提案

> 日期：2026-03-10
> 狀態：等待 Allen 決定

---

## 已完成的小修正

1. **Bug Fix：薪資顯示錯誤**（`src/matcher.py`）
   - 問題：`generate_email_content` 使用 `job.get('salary')` 但標準化後的職缺格式是 `salary_min` / `salary_max`，導致薪資永遠顯示「未公開」
   - 修復：改用 `salary_min` / `salary_max` 計算並格式化薪資

2. **UI 改善：新增「更新職缺」按鈕 + 快取年齡顯示**（`ui/src/App.jsx`）
   - 加入 Header 的 Refresh 按鈕，呼叫 `POST /api/jobs/refresh`
   - 顯示快取建立時間（幾分鐘前）

3. **Bug Fix：Remote 職缺角色過濾**（`src/matcher.py`）- 2026-03-10 已修復
   - 問題：Remote 職缺完全 bypass 角色過濾，設定 `preferred_roles: AI Engineer` 仍會出現遠端 Java/iOS 職缺
   - 修復：Remote 職缺改為通過角色過濾，但仍 bypass 地點過濾

---

## ~~提案一：切換 AI 評估引擎至 Anthropic Claude~~ ✅ 已完成 (2026-03-10)

**已完成**：`ai_evaluator.py` 新增 Anthropic Claude 作為 primary evaluator，OpenAI 降為 fallback。
使用模型：`claude-haiku-4-5-20251001`（可透過 `ANTHROPIC_MODEL` 覆蓋）。

---

## ~~提案二：新增職缺來源~~ ✅ 已完成 (2026-03-10)

**已完成**：新增 `ArbeitnowAdapter`（免費，無需 API Key），職缺來源從 2 個擴展至 3 個。
待評估：Himalayas、We Work Remotely (RSS) 仍可後續新增。

---

## ~~提案三：UI 新增履歷匹配分數顯示~~ ✅ 已完成 (2026-03-10)

**已完成**：
- 後端新增 `GET /api/resumes`（列出履歷）和 `GET /api/match?resume=allen.md`（匹配結果）端點
- 前端 Header 新增履歷選擇下拉（從 `/api/resumes` 動態載入）
- 選擇履歷後出現「🎯 匹配結果」分頁，職缺依分數排序
- 職缺卡片顯示彩色匹配分數 badge（綠/橙/灰）+ 匹配技能列表

---

## ~~提案四：改善 Remote 職缺過濾邏輯~~ ✅ 已完成 (2026-03-10)

**問題描述**
`matcher.py:filter_by_preference` 對所有 Remote 職缺 bypass 角色過濾，導致即使設定 `preferred_roles: AI Engineer`，仍會出現遠端 Java / iOS 職缺。

**已修復**：Remote 職缺改為通過角色過濾，但仍 bypass 地點過濾。

---

## ~~提案五：fetcher.py 快取 TTL 與 api.py 不一致~~ ✅ 已完成 (2026-03-10)

**問題描述**
- `fetcher.py:load_jobs()` 的快取 TTL 是 **6 小時**
- `api.py` 的記憶體快取 TTL 是 **10 分鐘**

兩者不一致，呼叫 `load_jobs()` 的路徑（如 GitHub Actions main.py）會使用到 6 小時前的舊資料，但 API 路徑每 10 分鐘就會刷新。

**已完成**：新增 `FILE_CACHE_TTL_HOURS = 6` 常數，並加入兩層快取設計說明的 comment。

---

## ~~Bug Fix：main.py use_ai 未檢查 ANTHROPIC_API_KEY~~ ✅ 已修復 (2026-03-10)

**問題描述**
`main.py` 以 `bool(os.environ.get('OPENAI_API_KEY'))` 決定是否啟用 AI 評估，但 `ai_evaluator.py` 已升級為優先使用 Claude。若只設定 `ANTHROPIC_API_KEY`（不設 `OPENAI_API_KEY`），AI 評估會被跳過。

**已修復**：改為 `bool(os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY'))`

---

## ~~Bug Fix：parser.py 缺少 RAG/Vector DB 等 AI 技能關鍵字~~ ✅ 已修復 (2026-03-10)

**問題描述**
`matcher.py` 的 `SKILL_WEIGHTS` 對 `rag`、`vector db`、`pinecone`、`weaviate` 等給予高權重 (3-4x)，但 `parser.py` 的 `SKILL_KEYWORDS` 沒有這些詞。導致履歷提到 RAG 等技術也不會被解析為技能，匹配分數偏低。

**已修復**：在 `parser.py` 的 `SKILL_KEYWORDS` 新增 `rag`、`vector db`、`pinecone`、`weaviate`、`chroma`、`embedding`、`claude`、`gemma`、`llama`、`mistral`、`fine-tuning`、`prompt engineering`。

---

## ~~Bug Fix：fetcher.py unique_id 在 id=None 時碰撞~~ ✅ 已修復 (2026-03-10)

**問題描述**
`JobFetcher.fetch_all()` 的去重邏輯：
```python
unique_id = f"{job.get('source')}-{job.get('id', job.get('slug', ''))}"
```
當 `id` 在 dict 中存在但值為 `None` 時（`normalize_job` 中 `'id': job.get('id')` 可能為 None），
`job.get('id', fallback)` 不會使用 fallback（fallback 只在 key 不存在時才觸發），
導致 unique_id 變成 `"RemoteOK-None"` 這種字串，多個無 ID 職缺互相碰撞，只有第一個能進列表。

**已修復**：改用 `id or url` 作為 fallback，URL 具全局唯一性：
```python
unique_id = f"{job.get('source')}-{job.get('id') or job.get('url', '')}"
```

---

## 待確認提案（需 Allen 決定）

### 提案六：requirements.txt 加入版本鎖定

**問題描述**
`requirements.txt` 完全沒有版本限制，`pip install` 時會拉最新版，可能造成兼容性問題。
例如 `anthropic` SDK 有時有 breaking changes（message API 格式變化）。

**建議方案**
```
anthropic>=0.40.0,<1.0
openai>=1.50.0,<2.0
fastapi>=0.110.0,<1.0
uvicorn[standard]>=0.27.0
requests>=2.31.0
python-dotenv>=1.0.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

**預估影響**：低。只影響開發環境一致性，不影響現有功能。

---

### 提案七：新增職缺來源（Himalayas / We Work Remotely）

**問題描述**
目前 3 個來源（RemoteOK, Remotive, Arbeitnow）中，Arbeitnow 偏歐洲、需簽證，
對台灣求職者效益有限。

**建議方案**
新增 Himalayas（himalayas.app/jobs.json，免費，高品質遠端職缺）作為第四來源。

**預估影響**：中。需要測試 API 穩定性，新增 Adapter class。等 Allen 決定。

---

## 優先級建議

| 優先 | 提案 | 原因 | 狀態 |
|------|------|------|------|
| ✅ | 提案四（Remote 過濾）| 直接影響匹配品質 | 已完成 |
| ✅ | 提案一（Claude API）| 環境一致性 + 品質 | 已完成 |
| ✅ | 提案二（新來源：Arbeitnow）| 擴大職缺池 | 已完成 |
| ✅ | 提案五（快取 TTL 文件）| 維護性 | 已完成 |
| ✅ | Bug Fix（use_ai 判斷）| Claude API key 被忽略 | 已完成 |
| ✅ | Bug Fix（parser 技能庫）| RAG/向量 DB 技能無法被解析 | 已完成 |
| ✅ | 提案三（UI 匹配分數）| 功能完整性，使用者體驗核心 | 已完成 |
| ✅ | Bug Fix（unique_id 碰撞）| 職缺去重失效，影響資料完整性 | 已完成 |
| ❓ | 提案六（版本鎖定）| 環境穩定性 | 等 Allen 決定 |
| ❓ | 提案七（Himalayas 來源）| 更多台灣適合的職缺 | 等 Allen 決定 |
