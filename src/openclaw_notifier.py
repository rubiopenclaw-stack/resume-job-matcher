"""
OpenClaw / Telegram 通知器
"""

import os
import json
import requests
from typing import Dict, List, Optional


# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('MESSAGE_TARGET') or os.environ.get('TELEGRAM_CHAT_ID')


def send_telegram_message(message: str, chat_id: str = None, parse_mode: str = 'Markdown') -> bool:
    """直接透過 Telegram Bot API 發送訊息"""
    token = TELEGRAM_BOT_TOKEN
    if not token:
        # 嘗試從 OpenClaw config 获取
        token = os.environ.get('OPENCLAW_TELEGRAM_TOKEN')
    
    if not token:
        print("❌ No Telegram bot token available")
        return False
    
    chat_id = chat_id or TELEGRAM_CHAT_ID
    if not chat_id:
        print("❌ No chat ID specified")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            print(f"✅ Telegram message sent: {response.json()}")
            return True
        else:
            print(f"❌ Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending Telegram: {e}")
        return False


def send_via_gateway(message: str, to: str = None) -> bool:
    """嘗試透過 OpenClaw Gateway 發送"""
    # 先嘗試 Telegram Bot（更可靠）
    if TELEGRAM_BOT_TOKEN or os.environ.get('OPENCLAW_TELEGRAM_TOKEN'):
        return send_telegram_message(message, to)
    
    # 如果沒有 Bot Token，嘗試 Gateway（需要 webhook 設定）
    print("⚠️ Gateway webhook not configured, skipping")
    return False


def format_job_message(resume: Dict, matched_jobs: List[Dict]) -> str:
    """格式化職缺訊息為簡短版本"""
    name = resume.get('name', '求職者')
    
    if not matched_jobs:
        return f"❌ {name}，今日沒有找到匹配的職缺"
    
    # 取前 5 個
    top_jobs = matched_jobs[:5]
    
    message = f"🎯 *{name}* 今日匹配 {len(matched_jobs)} 個職缺\n\n"
    
    for i, item in enumerate(top_jobs, 1):
        job = item['job']
        score = item['score']
        
        title = job.get('title', 'N/A')[:30]
        company = job.get('company', 'N/A')[:20]
        
        # 薪資
        salary = job.get('salary', '')
        if not salary:
            salary = '💰'
        
        # 連結
        url = job.get('url', '')
        
        message += f"{i}. *{title}*\n"
        message += f"   🏢 {company} | {salary}\n"
        message += f"   🎯 {score}% | [申請]({url})\n\n"
    
    if len(matched_jobs) > 5:
        message += f"⋯ 還有 {len(matched_jobs) - 5} 個職缺"
    
    message += "\n\n💡 完整職缺清單請查看 Email"
    
    return message


def send_to_openclaw(resume: Dict, matched_jobs: List[Dict], target: str = None) -> bool:
    """發送到 OpenClaw/Telegram"""
    message = format_job_message(resume, matched_jobs)
    return send_telegram_message(message, target)


if __name__ == '__main__':
    # Test
    test_resume = {'name': 'Test User', 'skills': ['python', 'ai']}
    test_jobs = [
        {'title': 'AI Engineer', 'company': 'TestCorp', 'url': 'https://example.com', 'salary': '$100k'},
    ]
    test_matched = [{'job': test_jobs[0], 'score': 95, 'matched_skills': ['python', 'ai']}]
    
    print("Testing Telegram notification...")
    # Uncomment to test:
    # send_to_openclaw(test_resume, test_matched, '6702902886')
