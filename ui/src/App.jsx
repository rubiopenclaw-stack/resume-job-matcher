import { useState, useEffect, useRef } from 'react'

function App() {
  const [jobs, setJobs] = useState([])
  const [favorites, setFavorites] = useState([])
  const [sources, setSources] = useState([])
  const [activeTab, setActiveTab] = useState('jobs')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selectedSource, setSelectedSource] = useState('')
  const [loading, setLoading] = useState(true)
  const debounceTimer = useRef(null)

  // 載入收藏
  useEffect(() => {
    const saved = localStorage.getItem('job-favorites')
    if (saved) {
      setFavorites(JSON.parse(saved))
    }
  }, [])

  // 儲存收藏
  useEffect(() => {
    localStorage.setItem('job-favorites', JSON.stringify(favorites))
  }, [favorites])

  // 取得來源列表
  useEffect(() => {
    fetch('/api/jobs/sources')
      .then(res => res.json())
      .then(data => setSources(data.sources || []))
      .catch(console.error)
  }, [])

  // Debounce 搜尋輸入
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      setDebouncedSearch(search)
    }, 300)
    return () => clearTimeout(debounceTimer.current)
  }, [search])

  // 取得職缺列表
  useEffect(() => {
    setLoading(true)
    let url = '/api/jobs?limit=50'
    if (debouncedSearch) url += `&search=${encodeURIComponent(debouncedSearch)}`
    if (selectedSource) url += `&source=${encodeURIComponent(selectedSource)}`

    fetch(url)
      .then(res => res.json())
      .then(data => {
        setJobs(data.jobs || [])
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [debouncedSearch, selectedSource])

  const toggleFavorite = (job) => {
    const isFav = favorites.some(f => f.id === job.id)
    if (isFav) {
      setFavorites(favorites.filter(f => f.id !== job.id))
    } else {
      setFavorites([...favorites, {
        id: job.id,
        title: job.title,
        company: job.company,
        url: job.url,
        location: job.location,
        source: job.source,
        tags: job.tags,
        savedAt: new Date().toISOString()
      }])
    }
  }

  const isFavorite = (jobId) => {
    return favorites.some(f => f.id === jobId)
  }

  return (
    <div>
      <header className="header">
        <div className="container">
          <h1>🎯 職缺獵人</h1>
          <p>AI-powered 履歷與職缺智能匹配系統</p>
        </div>
      </header>

      <div className="container">
        {/* 統計卡片 */}
        <div className="stats">
          <div className="stat-card">
            <div className="number">{jobs.length}</div>
            <div className="label">職缺數</div>
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
                onChange={(e) => setSearch(e.target.value)}
              />
              <select 
                value={selectedSource} 
                onChange={(e) => setSelectedSource(e.target.value)}
              >
                <option value="">所有來源</option>
                {sources.map(source => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
              <button 
                className="btn btn-primary"
                onClick={() => setSearch('')}
              >
                🔄 清除篩選
              </button>
            </div>

            {/* 來源快速篩選 */}
            <div className="source-chips" style={{ marginBottom: '20px' }}>
              <span 
                className={`source-chip ${selectedSource === '' ? 'active' : ''}`}
                onClick={() => setSelectedSource('')}
              >
                全部
              </span>
              {sources.map(source => (
                <span
                  key={source}
                  className={`source-chip ${selectedSource === source ? 'active' : ''}`}
                  onClick={() => setSelectedSource(source === selectedSource ? '' : source)}
                >
                  {source}
                </span>
              ))}
            </div>

            {/* 載入中 */}
            {loading && <div className="loading">載入中...</div>}

            {/* 職缺列表 */}
            {!loading && (
              <div className="job-list">
                {jobs.map(job => (
                  <JobCard 
                    key={job.id} 
                    job={job} 
                    isFavorite={isFavorite(job.id)}
                    onToggleFavorite={() => toggleFavorite(job)}
                  />
                ))}
                {jobs.length === 0 && (
                  <div className="empty-state">
                    <h3>沒有找到職缺</h3>
                    <p>試試調整搜尋條件</p>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* 收藏頁面 */}
        {activeTab === 'favorites' && (
          <div className="favorites-list">
            {favorites.length > 0 ? (
              favorites.map(fav => (
                <div key={fav.id} className="favorite-item">
                  <div className="favorite-item-info">
                    <h4>{fav.title}</h4>
                    <p>{fav.company} • {fav.location}</p>
                    <div className="job-card-tags" style={{ marginTop: '8px' }}>
                      {fav.tags?.slice(0, 5).map(tag => (
                        <span key={tag} className="tag">{tag}</span>
                      ))}
                    </div>
                  </div>
                  <div className="favorite-item-actions">
                    <a 
                      href={fav.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn btn-primary"
                      style={{ textDecoration: 'none' }}
                    >
                      申請連結
                    </a>
                    <button 
                      className="favorite-btn active"
                      onClick={() => toggleFavorite({ id: fav.id })}
                    >
                      ❤️
                    </button>
                  </div>
                </div>
              ))
            ) : (
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

// 職缺卡片元件
function JobCard({ job, isFavorite, onToggleFavorite }) {
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
        <span className="job-card-info">
          📍 {job.location || 'Remote'}
        </span>
        {job.salary_min > 0 && (
          <span className="job-card-info">
            💰 ${job.salary_min.toLocaleString()} - ${job.salary_max?.toLocaleString()}
          </span>
        )}
      </div>

      <div className="job-card-tags">
        {job.tags?.slice(0, 8).map(tag => (
          <span key={tag} className="tag">{tag}</span>
        ))}
      </div>

      <div className="job-card-footer">
        <a 
          href={job.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="job-card-link"
        >
          🔗 申請連結 →
        </a>
        <button 
          className={`favorite-btn ${isFavorite ? 'active' : ''}`}
          onClick={(e) => {
            e.stopPropagation()
            onToggleFavorite()
          }}
        >
          {isFavorite ? '❤️' : '🤍'}
        </button>
      </div>
    </div>
  )
}

export default App
