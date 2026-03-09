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
from openclaw_notifier import send_telegram_message

# 絕對路徑，不受工作目錄影響
RESUMES_DIR = Path(__file__).parent.parent / 'resumes'
JOBS_FILE = Path(__file__).parent.parent / 'jobs' / 'latest.json'

# 通知方式：telegram（預設）或其他
NOTIFY_METHOD = os.environ.get('NOTIFY_METHOD', 'telegram')
MESSAGE_TARGET = os.environ.get('MESSAGE_TARGET')


def send_notification(message: str) -> bool:
    """依 NOTIFY_METHOD 發送通知"""
    if NOTIFY_METHOD in ('telegram', 'openclaw'):
        return send_telegram_message(message, MESSAGE_TARGET)
    else:
        print(f"⚠️  未知的 NOTIFY_METHOD: {NOTIFY_METHOD}，跳過通知")
        return False


def main():
    print("🚀 Resume Job Matcher Starting...")
    
    # 1. 解析履歷
    print("\n📄 Parsing resumes...")
    resumes = get_all_resumes(str(RESUMES_DIR))
    if not resumes:
        print("❌ No resumes found")
        return

    print(f"   Found {len(resumes)} resume(s)")

    # 2. 獲取職缺
    print("\n💼 Fetching jobs from multiple sources...")
    jobs = load_jobs(JOBS_FILE)
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
        
        # AI 評估（需要 ANTHROPIC_API_KEY 或 OPENAI_API_KEY 才能啟用）
        use_ai = bool(os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY'))
        
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
        if send_notification(message):
            print(f"   ✅ Notification sent")
        else:
            print(f"   ❌ Failed to send")
    
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
