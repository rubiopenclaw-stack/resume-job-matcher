# Resume Job Matcher

AI-powered resume to job matching with daily email notifications.

## 工作流程

```
用戶上傳履歷 → 解析技能 → 每日比對職缺 → Email 推送
```

## 快速開始

### 1. Fork 此專案

### 2. 設定 Secrets (Settings → Secrets and variables → Actions)

| Secret | 說明 | 必填 |
|--------|------|------|
| `RESEND_API_KEY` | Resend API Key | ✅ |
| `EMAIL_TO` | 收件人 Email | ✅ |
| `EMAIL_FROM` | 發件人 Email | ✅ |
| `OPENAI_API_KEY` | OpenAI API (用于智能匹配) | 可選 |
| `REMOTEOK_API_TOKEN` | RemoteOK API Token | 可選 |

### 3. 上傳履歷

在 `resumes/` 目錄下建立 `{你的名字}.md`，格式：

```markdown
---
name: 你的名字
email: your@email.com
preferred_roles: AI Engineer, Fullstack Developer
preferred_locations: Remote, US, Europe
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

### 4. 手動觸發

Settings → Actions → Match Jobs → Run workflow

---

## 架構

```
├── src/
│   ├── parser.py       # 解析履歷技能
│   ├── fetcher.py     # 抓 RemoteOK 職缺
│   ├── matcher.py     # 技能比對 + 排名
│   └── notifier.py    # Email 發送
├── resumes/           # 履歷存放
├── jobs/              # 職缺快取
└── .github/workflows/
    └── daily-match.yml
```

---

## License

MIT
