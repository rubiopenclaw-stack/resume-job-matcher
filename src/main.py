"""
主程式 - 整合所有模組
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from parser import get_all_resumes
from fetcher import fetch_all_jobs, save_jobs, load_jobs
from matcher import match_jobs, get_summary_stats
from ai_evaluator import evaluate_batch, format_ai_message, simple_match

# 通知方式
NOTIFY_METHOD = os.environ.get('NOTIFY_METHOD', 'openclaw')

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
MESSAGE_TARGET = os.environ.get('MESSAGE_TARGET')


def send_telegram(message: str) -> bool:
    """發送 Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return False
    
    if not MESSAGE_TARGET:
        print("❌ MESSAGE_TARGET not set")
        return False
    
    import requests
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": MESSAGE_TARGET,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            print(f"✅ Telegram sent")
            return True
        else:
            print(f"❌ Telegram error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("🚀 Resume Job Matcher Starting...")
    
    # 1. 解析履歷
    print("\n📄 Parsing resumes...")
    resumes = get_all_resumes('resumes')
    if not resumes:
        print("❌ No resumes found")
        return
    
    print(f"   Found {len(resumes)} resume(s)")
    
    # 2. 獲取職缺
    print("\n💼 Fetching jobs from multiple sources...")
    jobs = load_jobs('jobs/latest.json')
    print(f"   Loaded {len(jobs)} jobs")
    
    if os.environ.get('FORCE_REFETCH'):
        jobs = fetch_all_jobs()
        save_jobs(jobs)
        print(f"   Refetched {len(jobs)} jobs")
    
    if not jobs:
        print("❌ No jobs found")
        return
    
    # 顯示來源統計
    sources = {}
    for job in jobs:
        s = job.get('source', 'Unknown')
        sources[s] = sources.get(s, 0) + 1
    print(f"   Sources: {sources}")
    
    # 3. 匹配並發送
    print("\n🎯 Matching & AI evaluation...")
    
    for resume in resumes:
        print(f"\n   Processing {resume['name']}...")
        
        # 先用簡單匹配取候選
        basic_matches = match_jobs(resume, jobs, top_n=20)
        
        if not basic_matches:
            print(f"   ⚠️ No matches")
            continue
        
        # AI 評估（如果沒有 API key 會用簡單匹配）
        use_ai = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENAI_BASE_URL')
        
        if use_ai:
            print(f"   🤖 Running AI evaluation...")
            ai_matches = evaluate_batch(resume, [m['job'] for m in basic_matches], top_n=10)
            message = format_ai_message(resume, ai_matches)
        else:
            # 用基本匹配結果
            ai_matches = basic_matches[:10]
            # 添加簡單分數和評估
            for m in ai_matches:
                m['ai_score'] = simple_match(resume, m['job'])
                m['evaluation'] = {
                    'reason': '基於關鍵字匹配',
                    'strengths': [],
                    'gaps': []
                }
            message = format_ai_message(resume, ai_matches)
        
        print(f"   Matched {len(ai_matches)} jobs")
        
        # 發送
        if send_telegram(message):
            print(f"   ✅ Notification sent")
        else:
            print(f"   ❌ Failed to send")
    
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
