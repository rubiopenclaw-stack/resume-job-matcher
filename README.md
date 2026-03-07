# Resume Job Matcher

🤖 AI-powered resume to job matching with daily Telegram notifications.

## 功能特色

- 📡 **多來源職缺** - RemoteOK + remote4me
- 🧠 **AI 智能評估** - GPT 分析匹配原因、優勢、缺口
- ⚖️ **加權匹配演算法** - 根據技能權重計算匹配度
- 🔍 **偏好過濾** - 根據角色、地點偏好篩選
- 📱 **Telegram 推送** - 每日自動發送到手機

## 工作流程

```
履歷解析 → 多來源抓取 → 偏好過濾 → AI 評估 → Telegram 推送
```

## 快速開始

### 1. Fork 此專案

### 2. 設定 Secrets

| Secret | 說明 | 必填 |
|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ✅ |
| `MESSAGE_TARGET` | 你的 Chat ID | ✅ |
| `OPENAI_API_KEY` | OpenAI API (可選) | 可選 |

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

## 架構

```
src/
├── parser.py          # 履歷解析
├── fetcher.py        # 多來源職缺抓取
├── matcher.py        # 加權匹配演算法
├── ai_evaluator.py   # AI 評估
└── main.py           # 主程式
```

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
