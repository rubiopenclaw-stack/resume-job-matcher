import { useState, useEffect, useRef, useCallback } from 'react'

const PAGE_SIZE = 20

function App() {
  const [jobs, setJobs] = useState([])
  const [total, setTotal] = useState(0)
  const [favorites, setFavorites] = useState([])
  const [sources, setSources] = useState([])
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
  const debounceTimer = useRef(null)

  // 載入收藏（try-catch 防止私密模式報錯）
  useEffect(() => {
    try {
      const saved = localStorage.getItem('job-favorites')
      if (saved) setFavorites(JSON.parse(saved))
    } catch {}
  }, [])

  // 儲存收藏
  useEffect(() => {
    try {
      localStorage.setItem('job-favorites', JSON.stringify(favorites))
    } catch {}
  }, [favorites])

  // 取得來源列表
  useEffect(() => {
    fetch('/api/jobs/sources')
      .then(r => r.json())
      .then(d => setSources(d.sources || []))
      .catch(() => {})
  }, [])

  // Debounce 搜尋，同時重置頁碼
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      setCurrentPage(0)
      setDebouncedSearch(search)
    }, 300)
    return () => clearTimeout(debounceTimer.current)
  }, [search])

  // 篩選條件變更時重置頁碼
  useEffect(() => {
    setCurrentPage(0)
  }, [selectedSource, salaryMin, salaryMax])

  // 取得職缺列表
  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams({
      limit: PAGE_SIZE,
      offset: currentPage * PAGE_SIZE,
    })
    if (debouncedSearch) params.set('search', debouncedSearch)
    if (selectedSource) params.set('source', selectedSource)
    if (salaryMin) params.set('salary_min', salaryMin)
    if (salaryMax) params.set('salary_max', salaryMax)

    fetch(`/api/jobs?${params}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => {
        setJobs(data.jobs || [])
        setTotal(data.total || 0)
        setCacheAge(data.cache_age_minutes ?? null)
        setLoading(false)
      })
      .catch(() => {
        setError('無法載入職缺，請確認後端服務是否運行')
        setLoading(false)
      })
  }, [debouncedSearch, selectedSource, salaryMin, salaryMax, currentPage, refreshTick])

  const toggleFavorite = (job) => {
    setFavorites(prev => {
      const isFav = prev.some(f => f.id === job.id)
      if (isFav) return prev.filter(f => f.id !== job.id)
      return [...prev, {
        id: job.id,
        title: job.title,
        company: job.company,
        url: job.url,
        location: job.location,
        source: job.source,
        tags: job.tags,
        salary_min: job.salary_min,
        salary_max: job.salary_max,
        savedAt: new Date().toISOString(),
      }]
    })
  }

  const isFavorite = useCallback((jobId) => {
    return favorites.some(f => f.id === jobId)
  }, [favorites])

  const clearFilters = () => {
    setSearch('')
    setSelectedSource('')
    setSalaryMin('')
    setSalaryMax('')
    setCurrentPage(0)
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await fetch('/api/jobs/refresh', { method: 'POST' })
      setCurrentPage(0)
      setRefreshTick(t => t + 1)
    } catch {}
    setRefreshing(false)
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
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
            <button
              className="btn btn-secondary"
              onClick={handleRefresh}
              disabled={refreshing}
              style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.4)' }}
            >
              {refreshing ? '⟳ 更新中...' : '⟳ 更新職缺'}
            </button>
            {cacheAge !== null && (
              <span style={{ fontSize: '12px', opacity: 0.75 }}>
                快取：{cacheAge} 分鐘前
              </span>
            )}
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
          <button
            className={`tab ${activeTab === 'jobs' ? 'active' : ''}`}
            onClick={() => setActiveTab('jobs')}
          >
            🏠 職缺列表
          </button>
          <button
            className={`tab ${activeTab === 'favorites' ? 'active' : ''}`}
            onClick={() => setActiveTab('favorites')}
          >
            ⭐ 收藏 ({favorites.length})
          </button>
        </div>

        {/* 職缺列表頁面 */}
        {activeTab === 'jobs' && (
          <>
            {/* 搜尋與篩選 */}
            <div className="filters">
              <input
                type="text"
                placeholder="搜尋職缺、公司或技能..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              <select
                value={selectedSource}
                onChange={e => { setSelectedSource(e.target.value); setCurrentPage(0) }}
              >
                <option value="">所有來源</option>
                {sources.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <input
                type="number"
                placeholder="薪資下限 $"
                value={salaryMin}
                onChange={e => setSalaryMin(e.target.value)}
                className="salary-input"
                min="0"
              />
              <input
                type="number"
                placeholder="薪資上限 $"
                value={salaryMax}
                onChange={e => setSalaryMax(e.target.value)}
                className="salary-input"
                min="0"
              />
              {hasFilters && (
                <button className="btn btn-secondary" onClick={clearFilters}>
                  ✕ 清除篩選
                </button>
              )}
            </div>

            {/* 來源快速篩選 */}
            <div className="source-chips" style={{ marginBottom: '20px' }}>
              <span
                className={`source-chip ${selectedSource === '' ? 'active' : ''}`}
                onClick={() => { setSelectedSource(''); setCurrentPage(0) }}
              >全部</span>
              {sources.map(s => (
                <span
                  key={s}
                  className={`source-chip ${selectedSource === s ? 'active' : ''}`}
                  onClick={() => { setSelectedSource(s === selectedSource ? '' : s); setCurrentPage(0) }}
                >{s}</span>
              ))}
            </div>

            {/* 錯誤提示 */}
            {error && (
              <div className="error-state">
                <span>⚠️ {error}</span>
                <button className="btn btn-primary" onClick={() => window.location.reload()}>重試</button>
              </div>
            )}

            {/* Skeleton 載入中 */}
            {loading && !error && (
              <div className="job-list">
                {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
              </div>
            )}

            {/* 職缺列表 */}
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
                    <JobCard
                      key={job.id}
                      job={job}
                      isFavorite={isFavorite(job.id)}
                      onToggleFavorite={() => toggleFavorite(job)}
                      onTagClick={tag => { setSearch(tag); setCurrentPage(0) }}
                    />
                  ))}
                  {jobs.length === 0 && (
                    <div className="empty-state">
                      <h3>沒有找到職缺</h3>
                      <p>試試調整搜尋條件</p>
                      {hasFilters && (
                        <button
                          className="btn btn-primary"
                          style={{ marginTop: '16px' }}
                          onClick={clearFilters}
                        >清除所有篩選</button>
                      )}
                    </div>
                  )}
                </div>

                {/* 分頁 */}
                {totalPages > 1 && (
                  <div className="pagination">
                    <button
                      className="page-btn"
                      disabled={currentPage === 0}
                      onClick={() => setCurrentPage(0)}
                    >«</button>
                    <button
                      className="page-btn"
                      disabled={currentPage === 0}
                      onClick={() => setCurrentPage(p => p - 1)}
                    >‹ 上一頁</button>
                    <span className="page-info">{currentPage + 1} / {totalPages}</span>
                    <button
                      className="page-btn"
                      disabled={currentPage >= totalPages - 1}
                      onClick={() => setCurrentPage(p => p + 1)}
                    >下一頁 ›</button>
                    <button
                      className="page-btn"
                      disabled={currentPage >= totalPages - 1}
                      onClick={() => setCurrentPage(totalPages - 1)}
                    >»</button>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* 收藏頁面 */}
        {activeTab === 'favorites' && (
          <div className="favorites-list">
            {favorites.length > 0 ? favorites.map(fav => (
              <div key={fav.id} className="favorite-item">
                <div className="favorite-item-info">
                  <h4>{fav.title}</h4>
                  <p>{fav.company} • {fav.location}</p>
                  {fav.salary_min > 0 && (
                    <p className="salary-tag">
                      💰 {formatSalary(fav.salary_min, fav.salary_max)}
                    </p>
                  )}
                  <div className="job-card-tags" style={{ marginTop: '8px' }}>
                    {fav.tags?.slice(0, 5).map(tag => (
                      <span key={tag} className="tag">{tag}</span>
                    ))}
                  </div>
                </div>
                <div className="favorite-item-actions">
                  <span className="job-card-source">{fav.source}</span>
                  <a
                    href={fav.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                    style={{ textDecoration: 'none' }}
                  >申請</a>
                  <button
                    className="favorite-btn active"
                    onClick={() => toggleFavorite({ id: fav.id })}
                    aria-label="取消收藏"
                  >❤️</button>
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

// Skeleton 載入卡片
function SkeletonCard() {
  return (
    <div className="job-card skeleton-card">
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-company" />
      <div className="skeleton skeleton-tags" />
    </div>
  )
}

// 職缺卡片元件
function JobCard({ job, isFavorite, onToggleFavorite, onTagClick }) {
  const salary = formatSalary(job.salary_min, job.salary_max)

  return (
    <div className="job-card">
      <div className="job-card-header">
        <div>
          <h3 className="job-card-title">{job.title}</h3>
          <p className="job-card-company">{job.company}</p>
        </div>
        <span className="job-card-source">{job.source}</span>
      </div>

      <div className="job-card-body">
        <span className="job-card-info">📍 {job.location || 'Remote'}</span>
        {salary && <span className="job-card-info salary-info">💰 {salary}</span>}
      </div>

      <div className="job-card-tags">
        {job.tags?.slice(0, 8).map(tag => (
          <span
            key={tag}
            className="tag tag-clickable"
            onClick={() => onTagClick(tag)}
            title={`搜尋 "${tag}"`}
          >{tag}</span>
        ))}
      </div>

      <div className="job-card-footer">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="job-card-link"
        >🔗 申請連結 →</a>
        <button
          className={`favorite-btn ${isFavorite ? 'active' : ''}`}
          onClick={e => { e.stopPropagation(); onToggleFavorite() }}
          aria-label={isFavorite ? '取消收藏' : '加入收藏'}
        >
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
