"""
Streamlit UI - 職缺匹配測試界面 (優化版)
"""

import streamlit as st
import json
import os
import base64
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
    page_title="🎯 職缺獵人",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
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

# 自定義 CSS
st.markdown("""
<style>
    /* 主題色 */
    :root {
        --primary: #4F46E5;
        --secondary: #10B981;
        --background: #F9FAFB;
        --card-bg: #FFFFFF;
    }
    
    /* 隱藏預設 header */
    .stHeader {
        display: none;
    }
    
    /* 自定義標題 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    
    /* 卡片樣式 */
    .job-card {
        background: var(--card-bg);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid #E5E7EB;
        transition: all 0.2s;
    }
    .job-card:hover {
        border-color: var(--primary);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15);
    }
    
    /* 評分標籤 */
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .score-high { background: #D1FAE5; color: #059669; }
    .score-medium { background: #FEF3C7; color: #D97706; }
    .score-low { background: #FEE2E2; color: #DC2626; }
    
    /* 來源標籤 */
    .source-tag {
        background: #EEF2FF;
        color: #4F46E5;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
    }
    
    /* 技能標籤 */
    .skill-tag {
        background: #F3F4F6;
        color: #374151;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        margin: 2px;
        display: inline-block;
    }
    
    /* 按鈕樣式 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* 側邊欄樣式 */
    .sidebar-content {
        background: #F9FAFB;
    }
    
    /* Tab 樣式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
    }
    
    /* 自定義 containers */
    .feature-card {
        background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# 標題
st.markdown('<p class="main-title">🎯 職缺獵人</p>', unsafe_allow_html=True)
st.markdown("AI-powered 履歷與職缺智能匹配系統")
st.markdown("---")

# 分頁
tab1, tab2, tab3, tab4 = st.tabs(["🏠 首頁", "📄 履歷管理", "⭐ 收藏", "📊 歷史"])

# ========== Tab 1: 首頁 ==========
with tab1:
    # 側邊欄
    with st.sidebar:
        st.image("https://img.icons8.com/fluent/48/000000/briefcase.png", width=48)
        st.header("⚙️ 控制面板")
        
        # 刷新按鈕
        if st.button("🔄 刷新職缺", use_container_width=True):
            with st.spinner("正在抓取職缺..."):
                jobs = fetch_all_jobs()
                save_jobs(jobs)
                st.success(f"✅ 已抓取 {len(jobs)} 個職缺！")
        
        jobs = load_jobs()
        
        # 統計卡片
        st.markdown("### 📊 統計")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("職缺", len(jobs))
        with col2:
            resumes = get_all_resumes()
            st.metric("履歷", len(resumes))
        
        # 來源分布
        st.markdown("### 📡 來源分布")
        sources = {}
        for job in jobs:
            s = job.get('source', 'Unknown')
            sources[s] = sources.get(s, 0) + 1
        
        for source, count in sources.items():
            st.progress(count / len(jobs) if jobs else 0, f"{source}: {count}")
        
        st.markdown("---")
        
        # 快速操作
        st.markdown("### ⚡ 快速操作")
        if st.button("📤 匯出所有職缺", use_container_width=True):
            jobs_json = json.dumps(jobs, ensure_ascii=False, indent=2)
            st.downloadButton(
                "💾 下載 JSON",
                jobs_json,
                f"jobs_{datetime.now().strftime('%Y%m%d')}.json",
                "application/json",
                key="download_jobs"
            )
    
    # 主界面
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📄 選擇履歷")
        resumes = get_all_resumes()
        
        if resumes:
            # 履歷選擇卡片
            selected_resume = st.selectbox(
                "選擇要使用的履歷",
                [r['name'] for r in resumes],
                label_visibility="collapsed"
            )
            resume = next(r for r in resumes if r['name'] == selected_resume)
            
            # 履歷資訊卡片
            with st.container():
                st.markdown(f"""
                <div class="job-card">
                    <h3>👤 {resume['name']}</h3>
                    <p>📧 {resume.get('email', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**🎯 偏好角色**")
                st.write(", ".join(resume.get('preferred_roles', [])) or "未設定")
                
                st.markdown("**📍 偏好地點**")
                st.write(", ".join(resume.get('preferred_locations', [])) or "Remote")
                
                st.markdown("**🛠️ 技能**")
                skills = resume.get('skills', [])
                if skills:
                    cols = st.columns(2)
                    for i, skill in enumerate(skills[:8]):
                        with cols[i % 2]:
                            st.caption(f"• {skill}")
                else:
                    st.warning("尚未設定技能")
        else:
            st.warning("⚠️ 尚無履歷，請先新增")
            resume = None
    
    with col2:
        st.markdown("### 🔍 匹配設定")
        
        if resume and jobs:
            # 篩選選項
            col_a, col_b = st.columns(2)
            
            with col_a:
                all_sources = list(set(j.get('source', 'Unknown') for j in jobs))
                selected_sources = st.multiselect(
                    "選擇來源",
                    options=all_sources,
                    default=all_sources,
                    label_visibility="collapsed"
                )
            
            with col_b:
                top_n = st.select_slider(
                    "顯示數量",
                    options=[5, 10, 15, 20, 30],
                    value=10
                )
            
            # 選項
            col_opt1, col_opt2, col_opt3 = st.columns(3)
            with col_opt1:
                use_ai = st.toggle("🤖 AI 評估", value=False)
            with col_opt2:
                show_salary = st.toggle("💰 顯示薪資", value=True)
            with col_opt3:
                auto_save = st.toggle("💾 自動存檔", value=True)
            
            # 匹配按鈕
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 開始智能匹配", type="primary", use_container_width=True):
                filtered_jobs = [j for j in jobs if j.get('source') in selected_sources]
                
                with st.spinner("🤔 AI 分析中..."):
                    matched = match_jobs(resume, filtered_jobs, top_n=top_n * 2)
                    
                    if use_ai:
                        st.info("🤖 GPT 評估中，請稍候...")
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
                    
                    if auto_save:
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
                    
                    st.rerun()
            
            # 結果顯示
            if st.session_state.current_matches:
                st.markdown("---")
                st.markdown(f"### 🎯 匹配結果 ({len(st.session_state.current_matches)} 個)")
                
                for i, item in enumerate(st.session_state.current_matches, 1):
                    job = item['job']
                    score = item.get('score', 0)
                    eval_data = item.get('evaluation', {})
                    
                    # 評分顏色
                    if score >= 80:
                        score_class = "score-high"
                        icon = "🔥"
                    elif score >= 60:
                        score_class = "score-medium"
                        icon = "✅"
                    else:
                        score_class = "score-low"
                        icon = "👍"
                    
                    # 展開式卡片
                    with st.expander(f"{icon} {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}"):
                        # 標題行
                        col_title1, col_title2, col_title3 = st.columns([2, 1, 1])
                        with col_title1:
                            st.markdown(f"**{job.get('title', 'N/A')}**")
                            st.caption(job.get('company', 'N/A'))
                        with col_title2:
                            st.markdown(f'<span class="score-badge {score_class}">{score}% 匹配</span>', unsafe_allow_html=True)
                        with col_title3:
                            st.markdown(f'<span class="source-tag">{job.get("source", "N/A")}</span>', unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # 詳細資訊
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.markdown(f"**📍 地點**")
                            st.write(job.get('location', 'Remote') or "Remote")
                        with col_info2:
                            if show_salary:
                                salary = job.get('salary', '') or job.get('salary_min', 0) or job.get('salary_max', 0)
                                st.markdown(f"**💰 薪資**")
                                st.write(salary if salary else "未公開")
                        
                        # 技能標籤
                        st.markdown("**🏷️ 技能標籤**")
                        tags = job.get('tags', [])[:8]
                        for tag in tags:
                            st.markdown(f'<span class="skill-tag">{tag}</span>', unsafe_allow_html=True)
                        
                        # 匹配技能
                        matched_skills = item.get('matched_skills', [])
                        if matched_skills:
                            st.markdown("**✨ 匹配技能**")
                            for skill in matched_skills:
                                st.markdown(f'<span class="skill-tag" style="background:#D1FAE5;color:#059669">{skill}</span>', unsafe_allow_html=True)
                        
                        # AI 評估
                        if eval_data.get('reason'):
                            st.markdown("---")
                            st.markdown(f"💡 **{eval_data.get('reason', '')}**")
                        
                        if eval_data.get('strengths'):
                            st.success(f"✨ 優勢: {', '.join(eval_data.get('strengths', []))}")
                        
                        if eval_data.get('gaps'):
                            st.warning(f"⚠️ 建議加強: {', '.join(eval_data.get('gaps', []))}")
                        
                        # 按鈕行
                        st.markdown("---")
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        with col_btn1:
                            st.markdown(f"[🔗 申請連結]({job.get('url', '')})")
                        with col_btn2:
                            if st.button(f"⭐ 收藏", key=f"fav_{i}"):
                                st.session_state.favorites.append({
                                    'title': job.get('title'),
                                    'company': job.get('company'),
                                    'url': job.get('url'),
                                    'score': score,
                                    'date': datetime.now().isoformat()
                                })
                                st.toast("✅ 已收藏!")
                        with col_btn3:
                            if use_ai:
                                st.caption(f"🤖 AI 評估")
                            else:
                                st.caption(f"📊 關鍵字匹配")
        
        elif not resume:
            st.info("👈 請先選擇履歷")
        else:
            st.info("👈 請先刷新職缺")

# ========== Tab 2: 履歷管理 ==========
with tab2:
    st.markdown("### 📄 履歷管理")
    
    # 顯示現有履歷
    resumes = get_all_resumes()
    
    if resumes:
        st.markdown("#### 現有履歷")
        for r in resumes:
            with st.expander(f"📄 {r['name']} ({len(r.get('skills', []))} 技能)"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Email:** {r.get('email', 'N/A')}")
                    st.write(f"**角色:** {', '.join(r.get('preferred_roles', []))}")
                    st.write(f"**地點:** {', '.join(r.get('preferred_locations', []))}")
                with col2:
                    st.write("**技能:**")
                    for skill in r.get('skills', [])[:10]:
                        st.caption(f"• {skill}")
    
    st.markdown("---")
    st.markdown("#### ✏️ 新增履歷")
    
    with st.form("resume_form", clear_on_submit=True):
        col_form1, col_form2 = st.columns(2)
        
        with col_form1:
            name = st.text_input("名字 *", placeholder="例如: Allen")
            email = st.text_input("Email", placeholder="your@email.com")
        
        with col_form2:
            preferred_roles = st.text_input("偏好角色 (逗號分隔)", placeholder="Data Engineer, AI Engineer")
            preferred_locations = st.text_input("偏好地點 (逗號分隔)", placeholder="Remote, US, Singapore")
        
        skills = st.text_area("技能 (逗號分隔) *", placeholder="Python, SQL, BigQuery, dbt, GCP", height=100)
        
        submitted = st.form_submit_button("💾 儲存履歷", type="primary", use_container_width=True)
        
        if submitted and name and skills:
            roles_list = [r.strip() for r in preferred_roles.split(',') if r.strip()]
            locations_list = [l.strip() for l in preferred_locations.split(',') if l.strip()]
            skills_list = [s.strip() for s in skills.split(',') if s.strip()]
            
            resume_content = f"""---
name: {name}
email: {email}
preferred_roles: {', '.join(roles_list)}
preferred_locations: {', '.join(locations_list)}
---

# 技能

{chr(10).join(f'- {s}' for s in skills_list)}

# 經驗

新增經驗...
"""
            
            resume_path = Path(__file__).parent.parent / 'resumes' / f'{name.lower().replace(" ", "_")}.md'
            resume_path.write_text(resume_content, encoding='utf-8')
            
            st.success(f"✅ 履歷已儲存: {resume_path.name}")
            st.rerun()

# ========== Tab 3: 收藏 ==========
with tab3:
    st.markdown("### ⭐ 收藏的職缺")
    
    if st.session_state.favorites:
        # 操作列
        col_act1, col_act2 = st.columns([1, 4])
        with col_act1:
            fav_json = json.dumps(st.session_state.favorites, ensure_ascii=False, indent=2)
            st.downloadButton("📥 匯出收藏", fav_json, "favorites.json", "application/json")
        with col_act2:
            if st.button("🗑️ 清空收藏"):
                st.session_state.favorites = []
                st.rerun()
        
        st.markdown("---")
        
        # 收藏列表
        for i, fav in enumerate(st.session_state.favorites):
            with st.expander(f"⭐ {fav.get('title')} @ {fav.get('company')}"):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    st.metric("匹配度", f"{fav.get('score', 0)}%")
                with col_f2:
                    st.write(f"**收藏時間**")
                    st.caption(fav.get('date', 'N/A')[:10])
                with col_f3:
                    st.write(f"**連結**")
                    st.markdown(f"[🔗 申請]({fav.get('url')})")
    else:
        st.info("💡 還沒有收藏的職缺，去首頁匹配一些吧！")

# ========== Tab 4: 歷史 ==========
with tab4:
    st.markdown("### 📊 歷史記錄")
    
    history = load_history()
    
    if history:
        # 匯出
        st.downloadButton(
            "📥 匯出全部歷史",
            json.dumps(history, ensure_ascii=False, indent=2),
            f"history_{datetime.now().strftime('%Y%m%d')}.json",
            "application/json"
        )
        
        st.markdown("---")
        
        # 統計
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("總匹配次數", len(history))
        with col_stat2:
            total_jobs = sum(h.get('matched_count', 0) for h in history)
            st.metric("總職缺數", total_jobs)
        with col_stat3:
            if history:
                last_date = history[-1].get('date', '')[:10]
                st.metric("最後更新", last_date)
        
        st.markdown("---")
        
        # 歷史列表
        for i, h in enumerate(reversed(history[-10:])):
            with st.expander(f"📅 {h['date'][:10]} | {h['resume']} | {h['matched_count']} 個職缺"):
                st.write(f"**時間:** {h['date']}")
                st.write(f"**履歷:** {h['resume']}")
                st.write(f"**匹配數:** {h['matched_count']}")
                
                if 'matches' in h and h['matches']:
                    st.markdown("**前5個職缺:**")
                    for m in h['matches'][:5]:
                        job = m.get('job', {})
                        st.caption(f"- {job.get('title')} @ {job.get('company')} ({m.get('score')}%)")
    else:
        st.info("💡 還沒有歷史記錄，去首頁進行匹配吧！")

# 底部
st.markdown("---")
st.caption(f"🎉 職缺獵人 v1.0.0 | 最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
