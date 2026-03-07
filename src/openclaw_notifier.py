"""
OpenClaw 通知器 - 透過 OpenClaw Gateway 發送訊息
"""

import os
import json
import requests
from typing import Dict, List, Optional


# OpenClaw Gateway 配置
GATEWAY_URL = os.environ.get('GATEWAY_URL', 'http://localhost:3000')
GATEWAY_TOKEN = os.environ.get('GATEWAY_TOKEN', '')
MESSAGE_CHANNEL = os.environ.get('MESSAGE_CHANNEL', 'telegram')  # telegram, discord, whatsapp


def get_status():
    """檢查 OpenClaw Gateway 狀態"""
    try:
        response = requests.get(f"{GATEWAY_URL}/api/status", timeout=5)
        return response.json() if response.ok else None
    except:
        return None


def send_via_gateway(message: str, to: str = None, channel: str = None) -> bool:
    """透過 OpenClaw Gateway 發送訊息"""
    if not GATEWAY_TOKEN:
        print("⚠️ GATEWAY_TOKEN not set")
        return False
    
    channel = channel or MESSAGE_CHANNEL
    
    payload = {
        "channel": channel,
        "message": message,
    }
    
    if to:
        payload["to"] = to
    
    # 嘗試不同的 API 端點
    endpoints = [
        f"{GATEWAY_URL}/api/message",
        f"{GATEWAY_URL}/api/send",
    ]
    
    headers = {
        "Authorization": f"Bearer {GATEWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for endpoint in endpoints:
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
            if response.ok:
                print(f"✅ Message sent via OpenClaw: {response.json()}")
                return True
            else:
                print(f"❌ Failed to {endpoint}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error sending to {endpoint}: {e}")
            continue
    
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
        salary = job.get('salary', '💰')[:15]
        
        message += f"{i}. *{title}*\n"
        message += f"   🏢 {company} | {salary}\n"
        message += f"   🎯 {score}% | [申請]({job.get('url', '')})\n\n"
    
    if len(matched_jobs) > 5:
        message += f"⋯ 還有 {len(matched_jobs) - 5} 個職缺"
    
    return message


def send_to_openclaw(resume: Dict, matched_jobs: List[Dict], target: str = None) -> bool:
    """發送到 OpenClaw"""
    message = format_job_message(resume, matched_jobs)
    return send_via_gateway(message, to=target)


def interactive_query(user_question: str) -> str:
    """處理用戶的互動查詢（預留給未來對話功能）"""
    # 這是一個預留接口，未來可以對接 LLM 來回答問題
    return f"收到問題：{user_question}\n\n請到網頁版查看完整職缺列表"


# ========== 以下為可選的 Webhook 伺服器 ==========

def create_webhook_handler(jobs_path: str = 'jobs/latest.json', resumes_path: str = 'resumes'):
    """建立 webhook 處理器（需要在外部 server 運行）"""
    from flask import Flask, request, jsonify
    from parser import get_all_resumes, parse_resume
    from matcher import match_jobs
    
    app = Flask(__name__)
    
    @app.route('/webhook/job-query', methods=['POST'])
    def query_jobs():
        data = request.json
        user_skills = data.get('skills', [])
        preferred_roles = data.get('roles', [])
        
        # 解析所有履歷
        resumes = get_all_resumes(resumes_path)
        
        # 載入職缺
        import json
        from pathlib import Path
        jobs_data = json.load(open(jobs_path))
        jobs = jobs_data.get('jobs', [])
        
        # 創建臨時履歷進行匹配
        temp_resume = {
            'name': data.get('name', 'Query User'),
            'skills': user_skills,
            'preferred_roles': preferred_roles,
            'preferred_locations': ['Remote']
        }
        
        matched = match_jobs(temp_resume, jobs, top_n=10)
        
        return jsonify({
            'matches': [
                {
                    'title': m['job'].get('title'),
                    'company': m['job'].get('company'),
                    'score': m['score'],
                    'url': m['job'].get('url')
                }
                for m in matched
            ]
        })
    
    return app


if __name__ == '__main__':
    # Test
    status = get_status()
    if status:
        print(f"✅ OpenClaw Gateway: {status}")
    else:
        print("❌ OpenClaw Gateway not reachable")
