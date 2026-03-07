"""
Streamlit UI - 職缺匹配測試界面 (增強版)
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

# 初始化收藏
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

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
    .salary-tag {
        background: #e6f7ff;
        color: #1890ff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
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
    
    st.markdown("---")
    st.header("⭐ 收藏的職缺")
    if st.session_state.favorites:
        for i, fav in enumerate(st.session_state.favorites):
            st.write(f"{i+1}. {fav['title'][:20]}...")
        if st.button("🗑️ 清空收藏"):
            st.session_state.favorites = []
            st.rerun()
    else:
        st.info("還沒有收藏的職缺")

# 主界面
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📄 我的履歷")
    
    resumes = get_all_resumes()
    
    if resumes:
        selected_resume = st.selectbox(
            "選擇履歷",
            options=[r['name'] for r in resumes]
        )
        resume = next(r for r in resumes if r['name'] == selected_resume)
        
        st.write("**技能：**")
        skills = resume.get('skills', [])
        if skills:
            # 分行顯示技能標籤
            cols = st.columns(3)
            for i, skill in enumerate(skills[:12]):
                with cols[i % 3]:
                    st.caption(f"• {skill}")
        
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
        # 篩選設定
        st.subheader("篩選設定")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            # 來源篩選
            all_sources = list(set(j.get('source', 'Unknown') for j in jobs))
            selected_sources = st.multiselect(
                "來源",
                options=all_sources,
                default=all_sources
            )
        
        with col_b:
            top_n = st.slider("顯示數量", 5, 30, 10)
        
        with col_c:
            use_ai = st.checkbox("🤖 AI 評估", value=False)
        
        # 過濾jobs
        filtered_jobs = [j for j in jobs if j.get('source') in selected_sources]
        
        # 匹配
        if st.button("🚀 開始匹配"):
            with st.spinner("匹配中..."):
                matched = match_jobs(resume, filtered_jobs, top_n=top_n * 2)
                
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
                    
                    # 薪資
                    salary = job.get('salary', '')
                    if not salary:
                        salary = job.get('salary_min', 0) or job.get('salary_max', 0)
                    
                    with st.expander(f"{i}. {job.get('title', 'N/A')} @ {job.get('company', 'N/A')} {emoji}"):
                        st.markdown(f"""
                        <div class="job-card">
                            <p><strong>匹配度：</strong><span class="{score_class}">{score}%</span></p>
                            <p><strong>來源：</strong>{job.get('source', 'N/A')}</p>
                            <p><strong>地點：</strong>{job.get('location', 'Remote')}</p>
                            <p><strong>薪資：</strong><span class="salary-tag">{salary if salary else '未公開'}</span></p>
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
                        
                        # 按鈕列
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.markdown(f"[🔗 申請連結]({job.get('url', '')})")
                        with col_btn2:
                            if st.button(f"⭐ 收藏 {i}", key=f"fav_{i}"):
                                st.session_state.favorites.append({
                                    'title': job.get('title'),
                                    'company': job.get('company'),
                                    'url': job.get('url'),
                                    'score': score
                                })
                                st.success("已收藏!")
    
    elif not resume:
        st.info("請先選擇或新增履歷")
    else:
        st.info("請先刷新職缺")

# 底部
st.markdown("---")
st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 收藏數：{len(st.session_state.favorites)}")
