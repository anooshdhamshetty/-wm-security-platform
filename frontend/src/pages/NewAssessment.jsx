import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createAssessment } from '../services/api.js'

export default function NewAssessment() {
  const [name, setName] = useState('World Monitor Assessment')
  const [repoUrl, setRepoUrl] = useState('')
  const [targetUrl, setTargetUrl] = useState('http://localhost:8080')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const assessment = await createAssessment({
        name, repo_url: repoUrl, target_base_url: targetUrl,
      })
      navigate(`/assessments/${assessment.id}`)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to create assessment.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-semibold mb-1">New Security Assessment</h1>
      <p className="text-sm text-gray-400 mb-6">
        Only test applications and repositories you are explicitly authorized to assess.
        The target host must be in the backend's <code className="text-accent">ALLOWED_TARGET_HOSTS</code> list.
      </p>

      <form onSubmit={handleSubmit} className="card space-y-4">
        <div>
          <label className="block text-sm mb-1 text-gray-400">Assessment name</label>
          <input
            className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
            value={name} onChange={e => setName(e.target.value)} required
          />
        </div>
        <div>
          <label className="block text-sm mb-1 text-gray-400">GitHub repository URL</label>
          <input
            className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
            placeholder="https://github.com/org/world-monitor"
            value={repoUrl} onChange={e => setRepoUrl(e.target.value)} required
          />
        </div>
        <div>
          <label className="block text-sm mb-1 text-gray-400">Authorized target base URL</label>
          <input
            className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
            value={targetUrl} onChange={e => setTargetUrl(e.target.value)} required
          />
        </div>

        {error && <div className="text-sm text-red-400">{error}</div>}

        <button
          type="submit" disabled={loading}
          className="bg-accent text-black font-medium text-sm px-4 py-2 rounded-md disabled:opacity-50"
        >
          {loading ? 'Creating…' : 'Create Assessment'}
        </button>
      </form>
    </div>
  )
}
