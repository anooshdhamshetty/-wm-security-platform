import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAssessments } from '../services/api.js'

export default function AssessmentList() {
  const [assessments, setAssessments] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listAssessments().then(setAssessments).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-400">Loading…</div>

  if (assessments.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-400 mb-4">No assessments yet.</p>
        <Link to="/new" className="bg-accent text-black text-sm font-medium px-4 py-2 rounded-md">
          Create your first assessment
        </Link>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Assessments</h1>
      <div className="space-y-2">
        {assessments.map(a => (
          <Link
            key={a.id} to={`/assessments/${a.id}`}
            className="card flex items-center justify-between hover:border-accent transition-colors"
          >
            <div>
              <div className="font-medium">{a.name}</div>
              <div className="text-xs text-gray-500">{a.repo_url}</div>
            </div>
            <div className="text-right">
              <div className="badge badge-info">{a.stage}</div>
              <div className="text-xs text-gray-500 mt-1">{new Date(a.created_at).toLocaleString()}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
