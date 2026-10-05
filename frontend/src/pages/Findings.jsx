import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getFindings } from '../services/api.js'

const STATUS_BADGE = {
  validated: 'badge-critical',
  potential_finding: 'badge-medium',
  false_positive: 'badge-info',
  inconclusive: 'badge-low',
}

const SEV_BADGE = {
  critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium',
  low: 'badge-low', info: 'badge-info',
}

function FindingCard({ f }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="card">
      <button className="w-full text-left" onClick={() => setOpen(!open)}>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div className="font-medium">{f.title}</div>
            <div className="text-xs text-gray-500 font-mono">{f.method} {f.endpoint_path}</div>
          </div>
          <div className="flex gap-2 items-center">
            {f.severity && <span className={`badge ${SEV_BADGE[f.severity]}`}>{f.severity}</span>}
            {f.cvss_score != null && <span className="text-xs text-gray-500">CVSS {f.cvss_score}</span>}
            <span className={`badge ${STATUS_BADGE[f.status]}`}>{f.status.replace('_', ' ')}</span>
          </div>
        </div>
      </button>
      {open && (
        <div className="mt-4 space-y-3 text-sm border-t border-border pt-4">
          <div><span className="text-gray-500">Description: </span>{f.description || 'N/A'}</div>
          <div><span className="text-gray-500">Evidence: </span>{f.evidence_summary || 'N/A'}</div>
          <div><span className="text-gray-500">Impact: </span>{f.impact || 'N/A'}</div>
          <div><span className="text-gray-500">Code location: </span>
            <span className="font-mono text-accent">{f.code_location || 'Code location could not be conclusively determined.'}</span>
          </div>
          <div><span className="text-gray-500">Root cause: </span>{f.root_cause || 'N/A'}</div>
          <div><span className="text-gray-500">Remediation: </span>{f.remediation || 'N/A'}</div>
          <div><span className="text-gray-500">Verification: </span>{f.verification || 'N/A'}</div>
          {f.cvss_vector && <div><span className="text-gray-500">CVSS vector: </span><span className="font-mono text-xs">{f.cvss_vector}</span></div>}
          {f.poc && Object.keys(f.poc).length > 0 && (
            <div>
              <span className="text-gray-500">Controlled PoC: </span>
              <pre className="bg-bg border border-border rounded-md p-2 text-xs overflow-x-auto mt-1">
                {JSON.stringify(f.poc, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Findings() {
  const { id } = useParams()
  const [findings, setFindings] = useState([])
  const [filter, setFilter] = useState('all')

  useEffect(() => { getFindings(id).then(setFindings) }, [id])

  const filtered = filter === 'all' ? findings : findings.filter(f => f.status === filter)

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Security Findings ({findings.length})</h1>
        <select
          value={filter} onChange={e => setFilter(e.target.value)}
          className="bg-panel border border-border rounded-md px-3 py-1.5 text-sm"
        >
          <option value="all">All statuses</option>
          <option value="validated">Validated</option>
          <option value="potential_finding">Potential</option>
          <option value="inconclusive">Inconclusive</option>
          <option value="false_positive">False positive</option>
        </select>
      </div>
      <div className="space-y-3">
        {filtered.map(f => <FindingCard key={f.id} f={f} />)}
        {filtered.length === 0 && (
          <div className="card text-center text-sm text-gray-500 py-8">
            No findings match this filter yet.
          </div>
        )}
      </div>
    </div>
  )
}
