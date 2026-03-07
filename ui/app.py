"""
Streamlit UI - 職缺匹配測試界面
"""

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime

# 確保可以 import src
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from parser import get_all_resumes, parse_resume
from fetcher import fetch_all_jobs, load_jobs, save_jobs
from matcher import match_jobs, filter_by_preference
from ai_evaluator import evaluate_match_with_ai, simple_match

# 頁面配置
st.set_page_config(
    page_title="職缺獵人",
    page_icon="🎯",
    layout="wide"
)

# CSS 樣式
st.markdown("""
<style>
    .job-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .score-high { color: #28a745; font-weight: bold; }
    .score-medium { color: #ffc107; font-weight: bold; }
    .score-low { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 標題
st.title("🎯 職缺獵人 - Resume Job Matcher")
st.markdown("---")

# 側邊欄 - 設定
with st.sidebar:
    st.header("⚙️ 設定")
    
    # 刷新職缺
    if st.button("🔄 刷新職缺"):
        with st.spinner("正在抓取職缺..."):
            jobs = fetch_all_jobs()
            save_jobs(jobs)
            st.success(f"已抓取 {len(jobs)} 個職缺！")
    
    # 載入職缺
    jobs = load_jobs()
    st.info(f"📦 目前有 {len(jobs)} 個職缺")
    
    # 來源統計
    sources = {}
    for job in jobs:
        s = job.get('source', 'Unknown')
        sources[s] = sources.get(s, 0) + 1
    st.write("**來源：**")
    for source, count in sources.items():
        st.write(f"- {source}: {count}")

# 主界面 - 履歷管理
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📄 我的履歷")
    
    # 顯示現有履歷
    resumes = get_all_resumes()
    
    if resumes:
        selected_resume = st.selectbox(
            "選擇履歷",
            options=[r['name'] for r in resumes]
        )
        resume = next(r for r in resumes if r['name'] == selected_resume)
        
        st.write("**技能：**")
        st.write(", ".join(resume.get('skills', [])))
        
        st.write("**偏好角色：**")
        st.write(", ".join(resume.get('preferred_roles', [])))
        
        st.write("**偏好地點：**")
        st.write(", ".join(resume.get('preferred_locations', [])))
    else:
        st.warning("尚無履歷，請新增")
        resume = None

with col2:
    st.header("🔍 匹配的職缺")
    
    if resume and jobs:
        # 過濾選項
        st.subheader("篩選設定")
        col_a, col_b = st.columns(2)
        with col_a:
            use_ai = st.checkbox("🤖 使用 AI 評估", value=False)
        with col_b:
            top_n = st.slider("顯示數量", 5, 20, 10)
        
        # 匹配
        if st.button("🚀 開始匹配"):
            with st.spinner("匹配中..."):
                # 先用簡單匹配
                matched = match_jobs(resume, jobs, top_n=top_n * 2)
                
                # 如果開啟 AI
                if use_ai:
                    st.info("🤖 AI 評估中...")
                    ai_results = []
                    for m in matched[:top_n]:
                        eval_result = evaluate_match_with_ai(resume, m['job'])
                        ai_results.append({
                            'job': m['job'],
                            'score': eval_result.get('ai_score') or m['score'],
                            'evaluation': eval_result,
                            'matched_skills': m.get('matched_skills', [])
                        })
                    matched = ai_results[:top_n]
                
                # 顯示結果
                st.success(f"找到 {len(matched)} 個匹配職缺！")
                
                for i, item in enumerate(matched, 1):
                    job = item['job']
                    score = item.get('score', 0)
                    eval_data = item.get('evaluation', {})
                    
                    # 評分顏色
                    if score >= 80:
                        score_class = "score-high"
                        emoji = "🔥"
                    elif score >= 60:
                        score_class = "score-medium"
                        emoji = "✅"
                    else:
                        score_class = "score-low"
                        emoji = "👍"
                    
                    with st.expander(f"{i}. {job.get('title', 'N/A')} @ {job.get('company', 'N/A')} {emoji}"):
                        st.markdown(f"""
                        <div class="job-card">
                            <p><strong>匹配度：</strong><span class="{score_class}">{score}%</span></p>
                            <p><strong>來源：</strong>{job.get('source', 'N/A')}</p>
                            <p><strong>地點：</strong>{job.get('location', 'Remote')}</p>
                            <p><strong>技能標籤：</strong>{', '.join(job.get('tags', [])[:10])}</p>
                            <p><strong>匹配技能：</strong>{', '.join(item.get('matched_skills', []))}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if eval_data.get('reason'):
                            st.write(f"💡 **{eval_data.get('reason', '')}**")
                        
                        if eval_data.get('strengths'):
                            st.write(f"✨ **優勢：** {', '.join(eval_data.get('strengths', []))}")
                        
                        if eval_data.get('gaps'):
                            st.write(f"⚠️ **缺口：** {', '.join(eval_data.get('gaps', []))}")
                        
                        st.write(f"[🔗 申請連結]({job.get('url', '')})")
    
    elif not resume:
        st.info("請先選擇或新增履歷")
    else:
        st.info("請先刷新職缺")

# 底部 - 統計
st.markdown("---")
st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
