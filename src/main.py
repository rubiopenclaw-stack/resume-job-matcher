"""
主程式 - 整合所有模組
"""

import os
import sys
from pathlib import Path

# 確保可以 import src 目錄
sys.path.insert(0, str(Path(__file__).parent))

from parser import get_all_resumes
from fetcher import fetch_all_jobs, save_jobs, load_jobs
from matcher import match_jobs, get_summary_stats
from notifier import send_match_report, send_digest_email


def main():
    print("🚀 Resume Job Matcher Starting...")
    
    # 1. 解析履歷
    print("\n📄 Parsing resumes...")
    resumes = get_all_resumes('resumes')
    if not resumes:
        print("❌ No resumes found in resumes/ directory")
        print("   Please add your resume as {name}.md")
        return
    
    print(f"   Found {len(resumes)} resume(s)")
    for r in resumes:
        print(f"   - {r['name']}: {len(r['skills'])} skills")
    
    # 2. 獲取職缺
    print("\n💼 Fetching jobs...")
    jobs = load_jobs('jobs/latest.json')
    print(f"   Loaded {len(jobs)} jobs from cache")
    
    # 如果需要刷新
    if os.environ.get('FORCE_REFETCH'):
        print("   Force refetching jobs...")
        jobs = fetch_all_jobs()
        save_jobs(jobs)
        print(f"   Fetched {len(jobs)} jobs")
    
    if not jobs:
        print("❌ No jobs found")
        return
    
    # 3. 匹配並發送
    print("\n🎯 Matching jobs...")
    email_to = os.environ.get('EMAIL_TO')
    
    if not email_to:
        print("❌ EMAIL_TO not set")
        return
    
    # 為每個履歷匹配並發送
    for resume in resumes:
        print(f"\n   Processing {resume['name']}...")
        
        matched = match_jobs(resume, jobs, top_n=10)
        
        if matched:
            stats = get_summary_stats(matched)
            print(f"   Matched {stats['count']} jobs, avg score: {stats['avg_score']}%")
            
            # 發送郵件
            success = send_match_report(resume, matched, email_to)
            if success:
                print(f"   ✅ Email sent to {email_to}")
            else:
                print(f"   ❌ Failed to send email")
        else:
            print(f"   ⚠️ No matching jobs found")
    
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
