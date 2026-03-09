# 職缺獵人 (Resume Job Matcher)

🤖 AI-powered resume to job matching with daily Telegram notifications.

## 功能特色

- 📡 **多來源職缺** - RemoteOK + Remotive
- 🧠 **AI 智能評估** - GPT 分析匹配原因、優勢、缺口
- ⚖️ **加權匹配演算法** - 根據技能權重計算匹配度
- 🔍 **偏好過濾** - 根據角色、地點偏好篩選
- 📱 **Telegram 推送** - 每日自動發送到手機
- ⚡ **快速回應** - 記憶體快取 (10分鐘 TTL)
- 🎯 **權重搜尋** - 智慧搜尋演算法

## 技術棧

| 層面 | 技術 |
|------|------|
| 前端 | React + Vite |
| 後端 | FastAPI (Python) |
| 職缺來源 | RemoteOK, Remotive |
| 資料格式 | JSON |

## 快速開始

### 1. Fork 此專案

### 2. 設定 Secrets / 環境變數

| 變數 | 說明 | 必填 |
|------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ✅ |
| `MESSAGE_TARGET` | 你的 Chat ID | ✅ |
| `OPENAI_API_KEY` | OpenAI API Key | 可選 |
| `OPENAI_BASE_URL` | 自訂 OpenAI Base URL (預設 api.openai.com) | 可選 |
| `OPENAI_MODEL` | 使用的模型 (預設 gpt-4o-mini) | 可選 |
| `NOTIFY_METHOD` | 通知方式：`telegram` 或 `openclaw` (預設 telegram) | 可選 |
| `CORS_ORIGINS` | 允許的 CORS 來源，逗號分隔 (預設 localhost:5173) | 可選 |

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

---

## 🖥️ 本地開發

### 後端 (FastAPI)

```bash
# 進入專案目錄
cd resume-job-matcher

# 啟動虛擬環境
source .venv/bin/activate

# 啟動 API 伺服器
python -m src.api
```

API 伺服器會在 `http://localhost:8000` 啟動

### 前端 (React + Vite)

```bash
# 進入 UI 目錄
cd resume-job-matcher/ui

# 安裝依賴 (首次)
npm install

# 啟動開發伺服器
npm run dev
```

前端會在 `http://localhost:5173` 啟動

### 完整工作流程

```bash
# 終端機 1 - 啟動後端
cd resume-job-matcher
source .venv/bin/activate
python -m src.api

# 終端機 2 - 啟動前端
cd resume-job-matcher/ui
npm run dev
```

然後在瀏覽器打開 `http://localhost:5173`

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

### 查詢參數

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
| GET | `/api/health` | API 健康狀態 |

### 範例請求

```bash
# 取得所有職缺
curl http://localhost:8000/api/jobs

# 搜尋 Python 職缺
curl "http://localhost:8000/api/jobs?search=python"

# 篩選特定來源
curl "http://localhost:8000/api/jobs?source=RemoteOK"

# 強制刷新快取
curl -X POST "http://localhost:8000/api/jobs/refresh"
```

---

## 最新功能

### ⚡ 記憶體快取

- 10 分鐘 TTL (Time To Live)
- API 回應快速穩定
- 支援手動清除快取

### 🎯 權重搜尋

搜尋結果會根據匹配位置給予不同權重：

| 欄位 | 權重 |
|------|------|
| title (標題) | 10 分 (開頭額外 +5) |
| company (公司) | 8 分 |
| tags (技能標籤) | 3 分 |
| description (描述) | 1 分 |

---

## 架構

```
resume-job-matcher/
├── src/                    # 後端程式碼
│   ├── api.py             # FastAPI 伺服器 (含快取、搜尋、分頁)
│   ├── fetcher.py         # 職缺抓取 (RemoteOK + Remotive)
│   ├── matcher.py         # 匹配演算法 (加權評分 + 偏好過濾)
│   ├── parser.py          # 履歷解析
│   ├── ai_evaluator.py   # AI 評估 (OpenAI 批量並行評估)
│   ├── openclaw_notifier.py # Telegram 通知封裝
│   └── main.py           # 主程式 (排程入口)
├── ui/                     # 前端程式碼 (React + Vite)
│   ├── src/
│   │   └── App.jsx       # React 主元件
│   ├── index.html
│   └── vite.config.js
├── resumes/                # 履歷存放 (.md 格式)
├── jobs/                   # 職缺資料快取 (latest.json)
└── tests/                  # 測試套件 (251 tests)
```

---

## 匹配演算法

### 技能權重

- **高權重** (3-4x): AI/ML, LLM, Agent, LangChain, RAG
- **中權重** (2x): Python, JavaScript, React, AWS, Docker
- **基本權重** (1x): SQL, 其他基礎技能

### 偏好過濾

- 根據 `preferred_roles` 過濾職缺類型
- 根據 `preferred_locations` 過濾地點
- Remote 職缺永遠保留

---

## License

MIT
