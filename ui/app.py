"""
Streamlit UI - 職缺匹配測試界面 (完整版)
"""

import streamlit as st
import json
import os
import csv
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

# 初始化
if 'favorites' not in st.session_state:
    st.session_state.favorites = []
if 'history' not in st.session_state:
    st.session_state.history = []
if 'current_matches' not in st.session_state:
    st.session_state.current_matches = []

# 確保歷史記錄文件存在
HISTORY_FILE = Path(__file__).parent.parent / 'data' / 'history.json'
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

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
    .tab-content {
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 標題
st.title("🎯 職缺獵人")
st.markdown("---")

# 分頁
tab1, tab2, tab3, tab4 = st.tabs(["🔍 職缺匹配", "📄 履歷管理", "⭐ 收藏", "📊 歷史記錄"])

# ========== Tab 1: 職缺匹配 ==========
with tab1:
    # 側邊欄
    with st.sidebar:
        st.header("⚙️ 設定")
        
        if st.button("🔄 刷新職缺"):
            with st.spinner("正在抓取職缺..."):
                jobs = fetch_all_jobs()
                save_jobs(jobs)
                st.success(f"已抓取 {len(jobs)} 個職缺！")
        
        jobs = load_jobs()
        st.info(f"📦 目前有 {len(jobs)} 個職缺")
        
        sources = {}
        for job in jobs:
            s = job.get('source', 'Unknown')
            sources[s] = sources.get(s, 0) + 1
        st.write("**來源：**")
        for source, count in sources.items():
            st.write(f"- {source}: {count}")
    
    # 主界面
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📄 我的履歷")
        resumes = get_all_resumes()
        
        if resumes:
            selected_resume = st.selectbox("選擇履歷", [r['name'] for r in resumes])
            resume = next(r for r in resumes if r['name'] == selected_resume)
            
            st.write("**技能：**")
            skills = resume.get('skills', [])
            if skills:
                cols = st.columns(3)
                for i, skill in enumerate(skills[:12]):
                    with cols[i % 3]:
                        st.caption(f"• {skill}")
            
            st.write("**偏好角色：**")
            st.write(", ".join(resume.get('preferred_roles', [])))
            
            st.write("**偏好地點：**")
            st.write(", ".join(resume.get('preferred_locations', [])))
        else:
            st.warning("尚無履歷")
            resume = None
    
    with col2:
        st.header("🔍 匹配的職缺")
        
        if resume and jobs:
            st.subheader("篩選設定")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                all_sources = list(set(j.get('source', 'Unknown') for j in jobs))
                selected_sources = st.multiselect("來源", options=all_sources, default=all_sources)
            
            with col_b:
                top_n = st.slider("顯示數量", 5, 30, 10)
            
            with col_c:
                use_ai = st.checkbox("🤖 AI 評估", value=False)
            
            filtered_jobs = [j for j in jobs if j.get('source') in selected_sources]
            
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
                    else:
                        for m in matched:
                            m['evaluation'] = {'reason': '關鍵字匹配'}
                    
                    # 儲存到歷史
                    history = load_history()
                    history.append({
                        'date': datetime.now().isoformat(),
                        'resume': resume['name'],
                        'matched_count': len(matched),
                        'matches': matched
                    })
                    save_history(history)
                    
                    st.session_state.current_matches = matched
                    st.session_state.history = history
                    
                    st.success(f"找到 {len(matched)} 個匹配職缺！")
            
            # 顯示結果
            if st.session_state.current_matches:
                # 匯出按鈕
                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    # CSV 匯出
                    csv_data = []
                    for m in st.session_state.current_matches:
                        job = m['job']
                        csv_data.append({
                            'title': job.get('title'),
                            'company': job.get('company'),
                            'location': job.get('location'),
                            'source': job.get('source'),
                            'url': job.get('url'),
                            'score': m.get('score', 0)
                        })
                    csv_json = json.dumps(csv_data, ensure_ascii=False)
                    st.download_button(
                        label="📥 匯出 JSON",
                        data=csv_json,
                        file_name=f"jobs_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
                
                matched = st.session_state.current_matches
                
                for i, item in enumerate(matched, 1):
                    job = item['job']
                    score = item.get('score', 0)
                    eval_data = item.get('evaluation', {})
                    
                    if score >= 80:
                        emoji = "🔥"
                    elif score >= 60:
                        emoji = "✅"
                    else:
                        emoji = "👍"
                    
                    salary = job.get('salary', '') or job.get('salary_min', 0) or job.get('salary_max', 0)
                    
                    with st.expander(f"{i}. {job.get('title', 'N/A')} @ {job.get('company', 'N/A')} {emoji}"):
                        st.markdown(f"""
                        <div class="job-card">
                            <p><strong>匹配度：</strong>{score}%</p>
                            <p><strong>來源：</strong>{job.get('source', 'N/A')}</p>
                            <p><strong>地點：</strong>{job.get('location', 'Remote')}</p>
                            <p><strong>薪資：</strong><span class="salary-tag">{salary if salary else '未公開'}</span></p>
                            <p><strong>匹配技能：</strong>{', '.join(item.get('matched_skills', []))}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if eval_data.get('reason'):
                            st.write(f"💡 {eval_data.get('reason', '')}")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.markdown(f"[🔗 申請]({job.get('url', '')})")
                        with col_btn2:
                            if st.button(f"⭐ 收藏 {i}", key=f"fav_{i}"):
                                st.session_state.favorites.append({
                                    'title': job.get('title'),
                                    'company': job.get('company'),
                                    'url': job.get('url'),
                                    'score': score,
                                    'date': datetime.now().isoformat()
                                })
                                st.success("已收藏!")

# ========== Tab 2: 履歷管理 ==========
with tab2:
    st.header("📄 履歷管理")
    
    # 顯示現有履歷
    resumes = get_all_resumes()
    
    if resumes:
        st.subheader("現有履歷")
        for r in resumes:
            with st.expander(f"📄 {r['name']}"):
                st.write(f"**Email:** {r.get('email', 'N/A')}")
                st.write(f"**偏好角色:** {', '.join(r.get('preferred_roles', []))}")
                st.write(f"**偏好地點:** {', '.join(r.get('preferred_locations', []))}")
                st.write(f"**技能:** {', '.join(r.get('skills', []))}")
    
    st.markdown("---")
    st.subheader("✏️ 新增/編輯履歷")
    
    with st.form("resume_form"):
        name = st.text_input("名字")
        email = st.text_input("Email")
        preferred_roles = st.text_input("偏好角色 (用逗號分隔)", "Data Engineer, AI Engineer")
        preferred_locations = st.text_input("偏好地點 (用逗號分隔)", "Remote, US")
        skills = st.text_area("技能 (用逗號分隔)", "Python, SQL, BigQuery, dbt, GCP, AI")
        
        submitted = st.form_submit_button("💾 儲存履歷")
        
        if submitted and name:
            # 轉換為列表
            roles_list = [r.strip() for r in preferred_roles.split(',')]
            locations_list = [l.strip() for l in preferred_locations.split(',')]
            skills_list = [s.strip() for s in skills.split(',')]
            
            # 建立履歷
            resume_content = f"""---
name: {name}
email: {email}
preferred_roles: {', '.join(roles_list)}
preferred_locations: {', '.join(locations_list)}
---

# 技能

{chr(10).join(f'- {s}' for s in skills_list)}

# 經驗

新增...
"""
            
            # 寫入文件
            resume_path = Path(__file__).parent.parent / 'resumes' / f'{name.lower().replace(" ", "_")}.md'
            resume_path.write_text(resume_content, encoding='utf-8')
            
            st.success(f"履歷已儲存: {resume_path.name}")
            st.rerun()

# ========== Tab 3: 收藏 ==========
with tab3:
    st.header("⭐ 收藏的職缺")
    
    if st.session_state.favorites:
        # 匯出收藏
        col_exp, col_clear = st.columns(2)
        with col_exp:
            fav_json = json.dumps(st.session_state.favorites, ensure_ascii=False, indent=2)
            st.download_button("📥 匯出收藏", fav_json, "favorites.json", "application/json")
        with col_clear:
            if st.button("🗑️ 清空收藏"):
                st.session_state.favorites = []
                st.rerun()
        
        for i, fav in enumerate(st.session_state.favorites):
            with st.expander(f"{i+1}. {fav.get('title')} @ {fav.get('company')}"):
                st.write(f"**匹配度:** {fav.get('score')}%")
                st.write(f"**收藏時間:** {fav.get('date', 'N/A')}")
                st.markdown(f"[🔗 申請]({fav.get('url')})")
    else:
        st.info("還沒有收藏的職缺")

# ========== Tab 4: 歷史記錄 ==========
with tab4:
    st.header("📊 歷史記錄")
    
    history = load_history()
    
    if history:
        # 匯出歷史
        st.download_button(
            "📥 匯出全部歷史",
            json.dumps(history, ensure_ascii=False, indent=2),
            f"history_{datetime.now().strftime('%Y%m%d')}.json",
            "application/json"
        )
        
        st.subheader("最近匹配記錄")
        for i, h in enumerate(reversed(history[-10:])):
            with st.expander(f"📅 {h['date'][:10]} - {h['resume']} - {h['matched_count']} 個職缺"):
                st.write(f"**時間:** {h['date']}")
                st.write(f"**履歷:** {h['resume']}")
                st.write(f"**匹配數:** {h['matched_count']}")
                
                # 顯示前5個
                if 'matches' in h:
                    st.write("**前5個職缺:**")
                    for m in h['matches'][:5]:
                        job = m.get('job', {})
                        st.write(f"- {job.get('title')} @ {job.get('company')} ({m.get('score')}%)")
    else:
        st.info("還沒有歷史記錄，請先進行匹配")

# 底部
st.markdown("---")
st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
