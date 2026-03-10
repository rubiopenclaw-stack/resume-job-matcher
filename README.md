# 職缺獵人 (Resume Job Matcher)

🤖 AI-powered resume to job matching with daily Telegram notifications.

## 功能特色

- 📡 **多來源職缺** - RemoteOK + Remotive 自動抓取
- 🧠 **雙 AI 評估** - Claude（優先）/ OpenAI（fallback）分析匹配原因、優勢、缺口
- ⚖️ **加權匹配演算法** - 根據技能權重計算匹配度
- 🔍 **偏好過濾** - 根據角色、地點偏好篩選，Remote 職缺永遠保留
- 📱 **Telegram 推送** - 每日自動發送匹配結果到手機
- ⚡ **記憶體快取** - 10 分鐘 TTL，UI 顯示快取年齡
- 🎯 **UI 即時匹配** - 在網頁選擇履歷，立即看到匹配分數排行
- 💰 **薪資篩選** - 支援薪資上下限過濾
- 📄 **分頁瀏覽** - 每頁 20 筆，支援首/尾頁快速跳轉

## 技術棧

| 層面 | 技術 |
|------|------|
| 前端 | React + Vite |
| 後端 | FastAPI (Python) |
| AI 評估 | Anthropic Claude / OpenAI（fallback）|
| 職缺來源 | RemoteOK, Remotive |
| 資料格式 | JSON |

## 快速開始

### 1. Fork 此專案

### 2. 設定 Secrets / 環境變數

| 變數 | 說明 | 必填 |
|------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ✅ |
| `MESSAGE_TARGET` | 你的 Chat ID | ✅ |
| `ANTHROPIC_API_KEY` | Anthropic API Key（優先使用 Claude） | 可選 |
| `OPENAI_API_KEY` | OpenAI API Key（Claude 不可用時 fallback） | 可選 |
| `ANTHROPIC_MODEL` | Claude 模型 (預設 claude-haiku-4-5-20251001) | 可選 |
| `OPENAI_BASE_URL` | 自訂 OpenAI Base URL (預設 api.openai.com) | 可選 |
| `OPENAI_MODEL` | OpenAI 模型 (預設 gpt-4o-mini) | 可選 |
| `NOTIFY_METHOD` | 通知方式：`telegram` 或 `openclaw` (預設 telegram) | 可選 |
| `CORS_ORIGINS` | 允許的 CORS 來源，逗號分隔 (預設 localhost:5173) | 可選 |

> AI 評估為可選功能。兩個 API Key 都不設定時，自動使用關鍵字匹配。

### 3. 上傳履歷

在 `resumes/` 目錄新增 `{名字}.md`：

```markdown
---
name: 你的名字
email: your@email.com
preferred_roles: AI Engineer, Fullstack Developer
preferred_locations: Remote, US
---

# 技能
- Python
- JavaScript
- React
- AI/ML
- TypeScript

# 經驗
5+ 年開發經驗...
```

### 4. 觸發執行

Actions → Match Jobs Daily → Run workflow

> Workflow 失敗時會自動發送 Telegram 通知。

---

## 🖥️ 本地開發

### 後端 (FastAPI)

```bash
cd resume-job-matcher
source .venv/bin/activate
python -m src.api
```

API 伺服器在 `http://localhost:8000` 啟動

### 前端 (React + Vite)

```bash
cd resume-job-matcher/ui
npm install   # 首次
npm run dev
```

前端在 `http://localhost:5173` 啟動

### 完整工作流程

```bash
# 終端機 1 - 後端
cd resume-job-matcher && source .venv/bin/activate && python -m src.api

# 終端機 2 - 前端
cd resume-job-matcher/ui && npm run dev
```

瀏覽器打開 `http://localhost:5173`，右上角選擇履歷即可看到匹配結果。

---

## API 端點

### 職缺相關

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/jobs` | 取得職缺列表 (支援搜尋/篩選/分頁) |
| GET | `/api/jobs/{id}` | 取得單一職缺詳情 |
| GET | `/api/jobs/sources` | 取得所有來源 |
| GET | `/api/jobs/locations` | 取得所有地點 |
| GET | `/api/jobs/tags` | 取得熱門技能標籤 |
| POST | `/api/jobs/refresh` | 手動觸發職缺重新整理 |

### 履歷匹配

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/resumes` | 取得所有可用履歷檔案 |
| GET | `/api/match?resume={檔名}` | 取得履歷與職缺匹配結果（含匹配分數） |

### 查詢參數（`/api/jobs`）

| 參數 | 類型 | 說明 |
|------|------|------|
| `search` | string | 搜尋關鍵字 (title/company/tags/description) |
| `source` | string | 篩選來源 (RemoteOK, Remotive) |
| `location` | string | 篩選地點 |
| `salary_min` | int | 最低薪資過濾 |
| `salary_max` | int | 最高薪資過濾 |
| `limit` | int | 回傳數量限制 (預設 50，最大 200) |
| `offset` | int | 分頁偏移量 (預設 0) |
| `refresh` | bool | 強制重新整理快取 |

### 健康檢查

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/health` | API 健康狀態與快取資訊 |

### 範例請求

```bash
# 取得所有職缺
curl http://localhost:8000/api/jobs

# 搜尋 Python 職缺（第 2 頁）
curl "http://localhost:8000/api/jobs?search=python&offset=20&limit=20"

# 薪資篩選
curl "http://localhost:8000/api/jobs?salary_min=80000&salary_max=150000"

# 取得可用履歷列表
curl http://localhost:8000/api/resumes

# 取得 allen.md 的匹配結果
curl "http://localhost:8000/api/match?resume=allen.md&limit=20"

# 強制刷新職缺資料
curl -X POST "http://localhost:8000/api/jobs/refresh"
```

---

## 最新功能

### 🎯 UI 即時匹配

在網頁右上角選擇履歷後，自動出現「匹配結果」分頁：
- 依匹配分數排序，顯示匹配百分比徽章（綠/黃/灰）
- 顯示每個職缺匹配到的具體技能
- 點擊技能標籤直接搜尋相關職缺

### 🧠 雙 AI 引擎

AI 評估優先使用 Claude（`ANTHROPIC_API_KEY`），不可用時自動 fallback 到 OpenAI（`OPENAI_API_KEY`）。兩者都未設定時改用關鍵字匹配，不影響基本功能。

### ⚡ 記憶體快取

- 10 分鐘 TTL，UI 右上角顯示快取年齡
- 支援一鍵手動更新職缺（右上角「更新職缺」按鈕）
- POST `/api/jobs/refresh` 觸發重新抓取

### 🎯 權重搜尋

搜尋結果根據匹配位置給予不同權重：

| 欄位 | 權重 |
|------|------|
| title（標題開頭） | 15 分 |
| title（標題含） | 10 分 |
| company（公司） | 8 分 |
| tags（技能標籤） | 3 分 |
| description（描述） | 1 分 |

---

## 架構

```
resume-job-matcher/
├── src/                       # 後端程式碼
│   ├── api.py                # FastAPI 伺服器 (v1.3.0，含快取、搜尋、分頁、履歷匹配)
│   ├── fetcher.py            # 職缺抓取 (RemoteOK + Remotive，Adapter 模式)
│   ├── matcher.py            # 匹配演算法 (加權評分 + 偏好過濾)
│   ├── parser.py             # 履歷解析 (Markdown frontmatter)
│   ├── ai_evaluator.py      # AI 評估 (Claude 優先 / OpenAI fallback，並行批次)
│   ├── openclaw_notifier.py # Telegram 通知封裝
│   └── main.py              # 主程式 (GitHub Actions 排程入口)
├── ui/                        # 前端程式碼 (React + Vite)
│   ├── src/
│   │   ├── App.jsx          # React 主元件 (分頁、分頁、匹配、收藏)
│   │   └── index.css        # 樣式
│   ├── index.html
│   └── vite.config.js
├── resumes/                   # 履歷存放 (.md 格式)
├── jobs/                      # 職缺資料快取 (latest.json)
└── tests/                     # 測試套件 (253 tests)
```

---

## 匹配演算法

### 技能權重

- **高權重** (3-4x): AI/ML, LLM, Agent, LangChain, RAG, CrewAI, AutoGen
- **中權重** (2x): Python, JavaScript, React, Next.js, AWS, Docker, Kubernetes
- **基本權重** (1x): SQL, 其他基礎技能

### 偏好過濾

- 根據 `preferred_roles` 過濾職缺類型
- 根據 `preferred_locations` 過濾地點
- Remote 職缺永遠保留（bypass 角色與地點過濾）

---

## License

MIT
