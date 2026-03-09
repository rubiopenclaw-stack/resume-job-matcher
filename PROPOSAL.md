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

---

## 提案一：切換 AI 評估引擎至 Anthropic Claude

**問題描述**
目前 `ai_evaluator.py` 只支援 OpenAI API。但專案本身是在 Claude Code 環境中運行，且 SKILL_WEIGHTS 中甚至列了 `claude` 為高權重技能，理應優先使用 Claude。

**建議方案**
- 新增 `ANTHROPIC_API_KEY` 環境變數支援
- 在 `evaluate_match_with_ai` 中加入 Anthropic Claude 作為 primary，OpenAI 作為 fallback
- 推薦模型：`claude-haiku-4-5-20251001`（速度快、成本低，適合批量評估）

**預估影響**
- 評估品質提升（Claude 對中文 prompt 的理解更好）
- 成本可能更低（Haiku vs GPT-4o-mini）
- 需要用戶設定 `ANTHROPIC_API_KEY`

---

## 提案二：新增職缺來源

**問題描述**
目前只有 RemoteOK (~99 職缺) 和 Remotive (~23 職缺)，職缺總量有限。

**建議方案**
可考慮新增以下免費 API 來源（按可行性排序）：

| 來源 | API | 說明 |
|------|-----|------|
| Arbeitnow | `https://arbeitnow.com/api/job-board-api` | 免費，無需 Key，歐洲遠端職缺 |
| Himalayas | `https://himalayas.app/jobs/api` | 免費，無需 Key，遠端職缺 |
| We Work Remotely (RSS) | RSS Feed | 可解析 RSS，無需 API Key |

**預估影響**
- 職缺總量可提升至 300-500 筆
- 需驗證 API 穩定性（建議先在 RESEARCH.md 補充）

---

## 提案三：UI 新增履歷匹配分數顯示

**問題描述**
前端目前只顯示所有職缺，沒有呈現「與使用者履歷的匹配分數」，失去了後端匹配算法的價值。

**建議方案**
- 後端新增 `GET /api/match?resume={name}` 端點，回傳帶有匹配分數的職缺列表
- 前端新增「匹配模式」切換，在職缺卡片上顯示匹配百分比 + 匹配技能標籤
- 或在現有職缺列表中，當 resume 存在時自動顯示匹配分數

**預估影響**
- 使用者體驗大幅提升
- 需要 `resumes/` 目錄中有對應的 `.md` 檔案
- 後端 API 變動中等

---

## 提案四：改善 Remote 職缺過濾邏輯

**問題描述**
`matcher.py:filter_by_preference` 目前對所有 Remote 職缺 bypass 角色過濾，導致即使設定 `preferred_roles: AI Engineer`，仍會出現遠端 Java / iOS 職缺。

**現有邏輯**
```python
# Remote 職缺永遠納入（bypass role & location 過濾）
if 'remote' in location:
    filtered.append(job)
    continue
```

**建議方案**
改為 Remote 職缺仍需通過角色過濾，但 bypass 地點過濾：
```python
if 'remote' in location:
    role_match = not preferred_roles or any(role in title for role in preferred_roles)
    if role_match:
        filtered.append(job)
    continue
```

**預估影響**
- 匹配結果精準度提升
- 職缺總數會減少（但更相關）
- 可能影響現有使用者習慣的行為

---

## 優先級建議

| 優先 | 提案 | 原因 |
|------|------|------|
| 高 | 提案四（Remote 過濾）| 直接影響匹配品質 |
| 中 | 提案一（Claude API）| 環境一致性 + 品質 |
| 中 | 提案二（新來源） | 擴大職缺池 |
| 低 | 提案三（UI 匹配分數）| 功能完整性 |
