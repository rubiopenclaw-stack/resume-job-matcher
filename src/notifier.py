"""
郵件通知器 - 發送匹配結果到 Email
"""

import os
import resend
from typing import Dict, List


def send_email(to: str, subject: str, html: str, from_email: str = None) -> bool:
    """使用 Resend 發送郵件"""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        print("RESEND_API_KEY not set")
        return False
    
    resend.api_key = api_key
    
    # 預設發件人
    if not from_email:
        from_email = os.environ.get('EMAIL_FROM', 'jobs@resend.dev')
    
    try:
        params = {
            'from': from_email,
            'to': [to],
            'subject': subject,
            'html': html,
        }
        
        response = resend.Emails.send(params)
        print(f"Email sent: {response}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def markdown_to_html(markdown: str) -> str:
    """簡單的 Markdown 到 HTML 轉換"""
    html = markdown
    
    # 標題
    html = html.replace('# ', '<h1>').replace('\n# ', '</h1><h1>')
    html = html.replace('## ', '<h2>').replace('\n## ', '</h2><h2>')
    html = html.replace('### ', '<h3>').replace('\n### ', '</h3><h3>')
    
    # 粗體
    html = html.replace('**', '<strong>', 1)
    html = html.replace('**', '</strong>', 1)
    
    # 連結
    import re
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # 換行
    html = html.replace('\n\n', '</p><p>')
    html = html.replace('\n', '<br>')
    
    # 包裝
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a1a; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 24px; }}
        h3 {{ color: #666; margin: 16px 0 8px; }}
        a {{ color: #0066cc; }}
        .job {{ background: #f5f5f5; border-radius: 8px; padding: 16px; margin: 16px 0; }}
        .score {{ background: #0066cc; color: white; padding: 4px 12px; border-radius: 12px; font-size: 14px; }}
        .skills {{ color: #666; font-size: 14px; }}
        .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #eee; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
{html}
<div class="footer">
    <p>此郵件由 Resume Job Matcher 自動發送</p>
</div>
</body>
</html>"""
    
    return html


def send_match_report(resume: Dict, matched_jobs: List[Dict], to: str) -> bool:
    """發送匹配報告"""
    from matcher import generate_email_content, get_summary_stats
    
    name = resume.get('name', '求職者')
    stats = get_summary_stats(matched_jobs)
    
    # 生成 Markdown 內容
    markdown = generate_email_content(resume, matched_jobs)
    
    # 轉換為 HTML
    html = markdown_to_html(markdown)
    
    # Subject
    subject = f"🎯 今日匹配 {stats['count']} 個職缺 | {name}"
    
    return send_email(to, subject, html)


def send_digest_email(resumes: List[Dict], jobs: List[Dict], to: str) -> bool:
    """發送匯總郵件（多個履歷）"""
    from matcher import match_jobs, generate_email_content
    
    all_content = "# 🎯 每日職缺匹配報告\n\n"
    
    for resume in resumes:
        matched = match_jobs(resume, jobs, top_n=5)
        if matched:
            all_content += f"\n---\n\n## 👤 {resume.get('name', 'Anonymous')}\n\n"
            all_content += generate_email_content(resume, matched)
    
    html = markdown_to_html(all_content)
    subject = f"🎯 每日職缺匹配報告 - {len(resumes)} 位求職者"
    
    return send_email(to, subject, html)


if __name__ == '__main__':
    # Test (需要設定環境變數)
    test_resume = {
        'name': 'Test User',
        'skills': ['python', 'ai'],
    }
    test_jobs = [
        {'title': 'AI Engineer', 'company': 'TestCorp', 'location': 'Remote', 'url': 'https://example.com', 'salary': '$100k'},
    ]
    
    print("Test: Use GitHub Actions to run full workflow")
