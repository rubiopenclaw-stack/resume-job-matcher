# Resume Job Matcher

AI-powered resume to job matching with daily notifications.

## 工作流程

```
用戶上傳履歷 → 解析技能 → 每日比對職缺 → 通知推送 (Email / OpenClaw)
```

## 支援的通知方式

| 方式 | 說明 |
|------|------|
| **Resend** | Email 寄送 |
| **OpenClaw** | 透過 OpenClaw Gateway 發送到 Telegram/Discord/WhatsApp |
| **Both** | 兩者都發送 |

## 快速開始

### 1. Fork 此專案

### 2. 設定 Secrets (Settings → Secrets and variables → Actions)

#### 通用
| Secret | 說明 | 必填 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API (用於智能匹配) | 可選 |

#### Resend (Email)
| Secret | 說明 | 必填 |
|--------|------|------|
| `RESEND_API_KEY` | Resend API Key | ✅ |
| `EMAIL_TO` | 收件人 Email | ✅ |
| `EMAIL_FROM` | 發件人 Email | ✅ |

#### OpenClaw (Telegram/Discord)
| Secret | 說明 | 必填 |
|--------|------|------|
| `OPENCLAW_GATEWAY_URL` | OpenClaw Gateway URL | ✅ |
| `OPENCLAW_GATEWAY_TOKEN` | OpenClaw Gateway Token | ✅ |
| `MESSAGE_TARGET` | 目標 ID (如 Telegram Chat ID) | ✅ |

#### 設定 NOTIFY_METHOD
在 workflow 中選擇：`resend` | `openclaw` | `both`

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
│   ├── parser.py            # 解析履歷技能
│   ├── fetcher.py          # 抓 RemoteOK 職缺
│   ├── matcher.py          # 技能比對 + 排名
│   ├── notifier.py        # Resend Email 發送
│   └── openclaw_notifier.py  # OpenClaw 通知
├── resumes/                # 履歷存放
├── jobs/                   # 職缺快取
└── .github/workflows/
    └── daily-match.yml
```

---

## OpenClaw 整合

### 取得 OpenClaw Gateway 設定

1. **Gateway URL**: OpenClaw 運行的網址
   - 本地：`http://localhost:3000`
   - 雲端：你的部署網址

2. **Gateway Token**: 
   - 在 OpenClaw config 中設定 `gateway.token`

3. **MESSAGE_TARGET**:
   - Telegram: 你的 Chat ID (@userinfobot 機器人查詢)
   - Discord: Channel ID

### 範例輸出 (Telegram)

```
🎯 Allen 今日匹配 8 個職缺

1. *AI Engineer*
   🏢 TechCorp | 💰 $100k
   🎯 95% | [申請](url)

2. *Senior Fullstack Developer*
   🏢 WebInc | 💰 $150k
   🎯 88% | [申請](url)
...
```

---

## License

MIT
