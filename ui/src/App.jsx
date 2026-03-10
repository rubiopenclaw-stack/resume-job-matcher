import { useState, useEffect, useRef, useCallback, useMemo } from 'react'

const PAGE_SIZE = 20
const ACCEPT_TYPES = '.md,.txt,.pdf'

function App() {
  const [jobs, setJobs] = useState([])
  const [total, setTotal] = useState(0)
  const [favorites, setFavorites] = useState([])
  const [sources, setSources] = useState([])
  const [resumes, setResumes] = useState([])
  const [selectedResume, setSelectedResume] = useState('')
  const [matchJobs, setMatchJobs] = useState([])
  const [matchResumeName, setMatchResumeName] = useState('')
  const [matchLoading, setMatchLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('jobs')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selectedSource, setSelectedSource] = useState('')
  const [salaryMin, setSalaryMin] = useState('')
  const [salaryMax, setSalaryMax] = useState('')
  const [currentPage, setCurrentPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cacheAge, setCacheAge] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshTick, setRefreshTick] = useState(0)
  // 上傳履歷狀態
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)  // { name, skills, roles, jobs }
  const [uploadError, setUploadError] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef(null)
  const debounceTimer = useRef(null)

  useEffect(() => {
    try {
      const saved = localStorage.getItem('job-favorites')
      if (saved) setFavorites(JSON.parse(saved))
    } catch {}
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem('job-favorites', JSON.stringify(favorites))
    } catch {}
  }, [favorites])

  useEffect(() => {
    fetch('/api/jobs/sources')
      .then(r => r.json())
      .then(d => setSources(d.sources || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch('/api/resumes')
      .then(r => r.json())
      .then(d => setResumes(d.resumes || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedResume) { setMatchJobs([]); setMatchResumeName(''); return }
    setMatchLoading(true)
    fetch(`/api/match?resume=${encodeURIComponent(selectedResume)}&limit=100`)
      .then(r => r.json())
      .then(d => { setMatchJobs(d.jobs || []); setMatchResumeName(d.resume || selectedResume); setMatchLoading(false) })
      .catch(() => setMatchLoading(false))
  }, [selectedResume, refreshTick])

  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => { setCurrentPage(0); setDebouncedSearch(search) }, 300)
    return () => clearTimeout(debounceTimer.current)
  }, [search])

  useEffect(() => { setCurrentPage(0) }, [selectedSource, salaryMin, salaryMax])

  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset: currentPage * PAGE_SIZE })
    if (debouncedSearch) params.set('search', debouncedSearch)
    if (selectedSource) params.set('source', selectedSource)
    if (salaryMin) params.set('salary_min', salaryMin)
    if (salaryMax) params.set('salary_max', salaryMax)

    fetch(`/api/jobs?${params}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(data => { setJobs(data.jobs || []); setTotal(data.total || 0); setCacheAge(data.cache_age_minutes ?? null); setLoading(false) })
      .catch(() => { setError('無法載入職缺，請確認後端服務是否運行'); setLoading(false) })
  }, [debouncedSearch, selectedSource, salaryMin, salaryMax, currentPage, refreshTick])

  const toggleFavorite = (job) => {
    setFavorites(prev => {
      const isFav = prev.some(f => f.id === job.id)
      if (isFav) return prev.filter(f => f.id !== job.id)
      return [...prev, { id: job.id, title: job.title, company: job.company, url: job.url, location: job.location, source: job.source, tags: job.tags, salary_min: job.salary_min, salary_max: job.salary_max, savedAt: new Date().toISOString() }]
    })
  }

  const favoriteIds = useMemo(() => new Set(favorites.map(f => f.id)), [favorites])
  const isFavorite = useCallback((jobId) => favoriteIds.has(jobId), [favoriteIds])

  const clearFilters = () => { setSearch(''); setSelectedSource(''); setSalaryMin(''); setSalaryMax(''); setCurrentPage(0) }

  const handleRefresh = async () => {
    setRefreshing(true)
    try { await fetch('/api/jobs/refresh', { method: 'POST' }); setCurrentPage(0); setRefreshTick(t => t + 1) } catch {}
    setRefreshing(false)
  }

  const handleUploadFile = async (file) => {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['md', 'txt', 'pdf'].includes(ext)) {
      setUploadError('只支援 .md、.txt、.pdf 格式')
      return
    }
    setUploadLoading(true)
    setUploadError(null)
    setUploadResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/upload-resume', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '上傳失敗')
      setUploadResult(data)
      setActiveTab('upload')
    } catch (e) {
      setUploadError(e.message || '上傳失敗，請再試一次')
    }
    setUploadLoading(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleUploadFile(file)
  }

  const hasFilters = search || selectedSource || salaryMin || salaryMax
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div>
      <header className="header">
        <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1>🎯 職缺獵人</h1>
            <p>AI-powered 履歷與職缺智能匹配系統</p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
            {resumes.length > 0 && (
              <select
                value={selectedResume}
                onChange={e => setSelectedResume(e.target.value)}
                style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.4)', borderRadius: '6px', padding: '6px 10px', fontSize: '14px', cursor: 'pointer' }}
              >
                <option value="" style={{ color: '#333' }}>🧑 選擇履歷以查看匹配</option>
                {resumes.map(r => <option key={r} value={r} style={{ color: '#333' }}>{r.replace('.md', '')}</option>)}
              </select>
            )}
            <button
              className="btn"
              onClick={handleRefresh}
              disabled={refreshing}
              style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.4)', padding: '6px 12px', borderRadius: '6px', cursor: refreshing ? 'not-allowed' : 'pointer', fontSize: '13px' }}
            >
              {refreshing ? '⟳ 更新中...' : '⟳ 更新職缺'}
            </button>
            {cacheAge !== null && <span style={{ fontSize: '12px', opacity: 0.75 }}>快取：{cacheAge} 分鐘前</span>}
          </div>
        </div>
      </header>

      <div className="container">
        {/* 統計卡片 */}
        <div className="stats">
          <div className="stat-card">
            <div className="number">{total.toLocaleString()}</div>
            <div className="label">總職缺數</div>
          </div>
          <div className="stat-card">
            <div className="number">{jobs.length}</div>
            <div className="label">本頁顯示</div>
          </div>
          <div className="stat-card">
            <div className="number">{favorites.length}</div>
            <div className="label">收藏數</div>
          </div>
          <div className="stat-card">
            <div className="number">{sources.length}</div>
            <div className="label">來源數</div>
          </div>
        </div>

        {/* 分頁標籤 */}
        <div className="tabs">
          <button className={`tab ${activeTab === 'jobs' ? 'active' : ''}`} onClick={() => setActiveTab('jobs')}>
            🏠 職缺列表
          </button>
          <button className={`tab ${activeTab === 'upload' ? 'active' : ''}`} onClick={() => setActiveTab('upload')}>
            📄 上傳履歷{uploadResult ? ` (${uploadResult.total})` : ''}
          </button>
          {selectedResume && (
            <button className={`tab ${activeTab === 'match' ? 'active' : ''}`} onClick={() => setActiveTab('match')}>
              🎯 匹配結果 {matchJobs.length > 0 ? `(${matchJobs.length})` : ''}
            </button>
          )}
          <button className={`tab ${activeTab === 'favorites' ? 'active' : ''}`} onClick={() => setActiveTab('favorites')}>
            ⭐ 收藏 ({favorites.length})
          </button>
        </div>

        {/* 職缺列表 */}
        {activeTab === 'jobs' && (
          <>
            <div className="filters">
              <input type="text" placeholder="搜尋職缺、公司或技能..." value={search} onChange={e => setSearch(e.target.value)} />
              <select value={selectedSource} onChange={e => { setSelectedSource(e.target.value); setCurrentPage(0) }}>
                <option value="">所有來源</option>
                {sources.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <input type="number" placeholder="薪資下限 $" value={salaryMin} onChange={e => setSalaryMin(e.target.value)} className="salary-input" min="0" />
              <input type="number" placeholder="薪資上限 $" value={salaryMax} onChange={e => setSalaryMax(e.target.value)} className="salary-input" min="0" />
              {hasFilters && <button className="btn btn-secondary" onClick={clearFilters}>✕ 清除篩選</button>}
            </div>

            <div className="source-chips" style={{ marginBottom: '20px' }}>
              <span className={`source-chip ${selectedSource === '' ? 'active' : ''}`} onClick={() => { setSelectedSource(''); setCurrentPage(0) }}>全部</span>
              {sources.map(s => (
                <span key={s} className={`source-chip ${selectedSource === s ? 'active' : ''}`} onClick={() => { setSelectedSource(s === selectedSource ? '' : s); setCurrentPage(0) }}>{s}</span>
              ))}
            </div>

            {error && (
              <div className="error-state">
                <span>⚠️ {error}</span>
                <button className="btn btn-primary" onClick={() => window.location.reload()}>重試</button>
              </div>
            )}

            {loading && !error && <div className="job-list">{[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}</div>}

            {!loading && !error && (
              <>
                {total > 0 && (
                  <div className="result-info">
                    找到 <strong>{total.toLocaleString()}</strong> 個職缺
                    {hasFilters && ' (已套用篩選)'}
                    {totalPages > 1 && `，第 ${currentPage + 1} / ${totalPages} 頁`}
                  </div>
                )}
                <div className="job-list">
                  {jobs.map(job => (
                    <JobCard key={job.id} job={job} isFavorite={isFavorite(job.id)} onToggleFavorite={() => toggleFavorite(job)} onTagClick={tag => { setSearch(tag); setCurrentPage(0) }} />
                  ))}
                  {jobs.length === 0 && (
                    <div className="empty-state">
                      <h3>沒有找到職缺</h3>
                      <p>試試調整搜尋條件</p>
                      {hasFilters && <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={clearFilters}>清除所有篩選</button>}
                    </div>
                  )}
                </div>
                {totalPages > 1 && (
                  <div className="pagination">
                    <button className="page-btn" disabled={currentPage === 0} onClick={() => setCurrentPage(0)}>«</button>
                    <button className="page-btn" disabled={currentPage === 0} onClick={() => setCurrentPage(p => p - 1)}>‹ 上一頁</button>
                    <span className="page-info">{currentPage + 1} / {totalPages}</span>
                    <button className="page-btn" disabled={currentPage >= totalPages - 1} onClick={() => setCurrentPage(p => p + 1)}>下一頁 ›</button>
                    <button className="page-btn" disabled={currentPage >= totalPages - 1} onClick={() => setCurrentPage(totalPages - 1)}>»</button>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* 上傳履歷頁面 */}
        {activeTab === 'upload' && (
          <div>
            {/* 拖曳上傳區 */}
            <div
              className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPT_TYPES}
                style={{ display: 'none' }}
                onChange={e => handleUploadFile(e.target.files[0])}
              />
              {uploadLoading ? (
                <div className="upload-loading">
                  <div className="upload-spinner" />
                  <p>分析中，請稍候...</p>
                </div>
              ) : (
                <>
                  <div className="upload-icon">📄</div>
                  <p className="upload-title">拖曳履歷到此，或點擊上傳</p>
                  <p className="upload-hint">支援 .md、.txt、.pdf 格式</p>
                </>
              )}
            </div>

            {uploadError && (
              <div className="error-state" style={{ marginTop: '16px' }}>
                <span>⚠️ {uploadError}</span>
              </div>
            )}

            {/* 解析結果 */}
            {uploadResult && !uploadLoading && (
              <>
                <div className="upload-result-card">
                  <div className="upload-result-header">
                    <div>
                      <h3>👤 {uploadResult.name}</h3>
                      {uploadResult.roles?.length > 0 && (
                        <p className="upload-roles">推測角色：{uploadResult.roles.join('、')}</p>
                      )}
                    </div>
                    <span className="upload-match-count">匹配 {uploadResult.total} 個職缺</span>
                  </div>

                  {uploadResult.skills?.length > 0 && (
                    <div className="upload-skills">
                      <p className="upload-skills-label">偵測到的技能（{uploadResult.skills.length} 項）</p>
                      <div className="skill-chips">
                        {uploadResult.skills.map(skill => (
                          <span key={skill} className="skill-chip">{skill}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 匹配職缺列表 */}
                {uploadResult.jobs?.length > 0 && (
                  <>
                    <div className="result-info" style={{ marginTop: '24px' }}>
                      依匹配分數排序，共 <strong>{uploadResult.total}</strong> 個職缺
                    </div>
                    <div className="job-list">
                      {uploadResult.jobs.map(job => (
                        <JobCard
                          key={job.id}
                          job={job}
                          isFavorite={isFavorite(job.id)}
                          onToggleFavorite={() => toggleFavorite(job)}
                          onTagClick={tag => { setSearch(tag); setActiveTab('jobs') }}
                          matchScore={job.match_score}
                          matchedSkills={job.matched_skills}
                        />
                      ))}
                    </div>
                  </>
                )}

                {uploadResult.jobs?.length === 0 && (
                  <div className="empty-state" style={{ marginTop: '24px' }}>
                    <h3>沒有找到匹配職缺</h3>
                    <p>試試更新職缺資料，或在履歷中加入更多技能關鍵字</p>
                  </div>
                )}
              </>
            )}

            {!uploadResult && !uploadLoading && !uploadError && (
              <div className="upload-tips">
                <h4>💡 履歷格式建議</h4>
                <ul>
                  <li>Markdown (.md) — 支援 frontmatter 自動解析姓名、偏好角色</li>
                  <li>純文字 (.txt) — 直接掃描技能關鍵字</li>
                  <li>PDF (.pdf) — 自動萃取文字後分析</li>
                </ul>
                <p style={{ marginTop: '12px', color: 'var(--text-light)', fontSize: '0.85rem' }}>
                  支援技能關鍵字：Python、React、AI/ML、AWS、Docker、LangChain... 等 {' '}
                  <strong>40+</strong> 種技術棧
                </p>
              </div>
            )}
          </div>
        )}

        {/* 匹配結果頁面（從 resumes/ 目錄選取） */}
        {activeTab === 'match' && (
          <div>
            {matchLoading && <div className="job-list">{[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}</div>}
            {!matchLoading && matchJobs.length > 0 && (
              <>
                <div className="result-info">
                  <strong>{matchResumeName}</strong> 共匹配 <strong>{matchJobs.length}</strong> 個職缺，依匹配分數排序
                </div>
                <div className="job-list">
                  {matchJobs.map(job => (
                    <JobCard key={job.id} job={job} isFavorite={isFavorite(job.id)} onToggleFavorite={() => toggleFavorite(job)} onTagClick={tag => { setSearch(tag); setActiveTab('jobs') }} matchScore={job.match_score} matchedSkills={job.matched_skills} />
                  ))}
                </div>
              </>
            )}
            {!matchLoading && matchJobs.length === 0 && (
              <div className="empty-state">
                <h3>沒有找到匹配職缺</h3>
                <p>試試更新職缺資料，或調整履歷中的技能</p>
              </div>
            )}
          </div>
        )}

        {/* 收藏頁面 */}
        {activeTab === 'favorites' && (
          <div className="favorites-list">
            {favorites.length > 0 ? favorites.map(fav => (
              <div key={fav.id} className="favorite-item">
                <div className="favorite-item-info">
                  <h4>{fav.title}</h4>
                  <p>{fav.company} • {fav.location}</p>
                  {fav.salary_min > 0 && <p className="salary-tag">💰 {formatSalary(fav.salary_min, fav.salary_max)}</p>}
                  <div className="job-card-tags" style={{ marginTop: '8px' }}>
                    {fav.tags?.slice(0, 5).map(tag => <span key={tag} className="tag">{tag}</span>)}
                  </div>
                </div>
                <div className="favorite-item-actions">
                  <span className="job-card-source">{fav.source}</span>
                  <a href={fav.url} target="_blank" rel="noopener noreferrer" className="btn btn-primary" style={{ textDecoration: 'none' }}>申請</a>
                  <button className="favorite-btn active" onClick={() => toggleFavorite({ id: fav.id })} aria-label="取消收藏">❤️</button>
                </div>
              </div>
            )) : (
              <div className="empty-state">
                <h3>還沒有收藏</h3>
                <p>去職缺列表收藏一些職缺吧！</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="job-card skeleton-card">
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-company" />
      <div className="skeleton skeleton-tags" />
    </div>
  )
}

function JobCard({ job, isFavorite, onToggleFavorite, onTagClick, matchScore, matchedSkills }) {
  const salary = formatSalary(job.salary_min, job.salary_max)
  const scoreColor = matchScore >= 60 ? '#22c55e' : matchScore >= 35 ? '#f59e0b' : '#94a3b8'

  return (
    <div className="job-card">
      <div className="job-card-header">
        <div>
          <h3 className="job-card-title">{job.title}</h3>
          <p className="job-card-company">{job.company}</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
          {matchScore !== undefined && (
            <span style={{ background: scoreColor, color: 'white', borderRadius: '12px', padding: '2px 10px', fontSize: '13px', fontWeight: 600 }}>
              {matchScore}% 匹配
            </span>
          )}
          <span className="job-card-source">{job.source}</span>
        </div>
      </div>

      <div className="job-card-body">
        <span className="job-card-info">📍 {job.location || 'Remote'}</span>
        {salary && <span className="job-card-info salary-info">💰 {salary}</span>}
      </div>

      {matchedSkills && matchedSkills.length > 0 && (
        <div style={{ marginBottom: '6px', fontSize: '12px', color: '#64748b' }}>
          ✨ 匹配技能：{matchedSkills.slice(0, 6).join(' · ')}
        </div>
      )}

      <div className="job-card-tags">
        {job.tags?.slice(0, 8).map(tag => (
          <span key={tag} className="tag tag-clickable" onClick={() => onTagClick(tag)} title={`搜尋 "${tag}"`}>{tag}</span>
        ))}
      </div>

      <div className="job-card-footer">
        <a href={job.url} target="_blank" rel="noopener noreferrer" className="job-card-link">🔗 申請連結 →</a>
        <button className={`favorite-btn ${isFavorite ? 'active' : ''}`} onClick={e => { e.stopPropagation(); onToggleFavorite() }} aria-label={isFavorite ? '取消收藏' : '加入收藏'}>
          {isFavorite ? '❤️' : '🤍'}
        </button>
      </div>
    </div>
  )
}

function formatSalary(min, max) {
  if (!min && !max) return null
  const fmt = n => `$${Number(n).toLocaleString()}`
  if (min && max) return `${fmt(min)} - ${fmt(max)}`
  if (min) return `${fmt(min)}+`
  return `最高 ${fmt(max)}`
}

export default App
