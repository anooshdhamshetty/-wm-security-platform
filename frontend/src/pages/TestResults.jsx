import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getTestExecutions } from '../services/api.js'

const RESULT_BADGE = {
  pass: 'badge-info',
  fail: 'badge-low',
  potential_finding: 'badge-medium',
  error: 'badge-critical',
}

export default function TestResults() {
  const { id } = useParams()
  const [tests, setTests] = useState([])
  const [open, setOpen] = useState(null)

  useEffect(() => { getTestExecutions(id).then(setTests) }, [id])

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Test Executions ({tests.length})</h1>
      <div className="space-y-2">
        {tests.map(t => (
          <div key={t.id} className="card">
            <button className="w-full text-left flex items-center justify-between" onClick={() => setOpen(open === t.id ? null : t.id)}>
              <div className="font-mono text-sm">
                <span className="text-accent">{t.test_id}</span> — {t.method} {t.endpoint_path}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">{t.status_code ?? '—'}</span>
                <span className="text-xs text-gray-500">{t.duration_ms ? `${t.duration_ms.toFixed(0)}ms` : ''}</span>
                <span className={`badge ${RESULT_BADGE[t.result] || 'badge-info'}`}>{t.result.replace('_', ' ')}</span>
              </div>
            </button>
            {open === t.id && (
              <div className="mt-3 pt-3 border-t border-border grid md:grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-gray-500 mb-1">Request</div>
                  <pre className="bg-bg border border-border rounded-md p-2 overflow-x-auto">{JSON.stringify(t.request, null, 2)}</pre>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Response</div>
                  <pre className="bg-bg border border-border rounded-md p-2 overflow-x-auto">{JSON.stringify(t.response, null, 2)}</pre>
                </div>
              </div>
            )}
          </div>
        ))}
        {tests.length === 0 && (
          <div className="card text-center text-sm text-gray-500 py-8">
            No tests executed yet. Run the pipeline from the Dashboard tab.
          </div>
        )}
      </div>
    </div>
  )
}
