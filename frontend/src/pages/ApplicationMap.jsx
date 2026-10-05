import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getApplicationMap } from '../services/api.js'

const TYPE_COLORS = {
  repository: 'bg-gray-700',
  file: 'bg-blue-900 border-blue-700',
  endpoint: 'bg-cyan-900 border-cyan-700',
  function: 'bg-purple-900 border-purple-700',
  frontend_component: 'bg-green-900 border-green-700',
}

export default function ApplicationMap() {
  const { id } = useParams()
  const [graph, setGraph] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getApplicationMap(id).then(setGraph).catch(err => setError(err?.response?.data?.detail || 'Failed to load map. Run repository analysis first.'))
  }, [id])

  if (error) return <div className="card text-sm text-red-400">{error}</div>
  if (!graph) return <div className="text-gray-400">Loading…</div>

  const byType = {}
  for (const n of graph.nodes) {
    byType[n.type] = byType[n.type] || []
    byType[n.type].push(n)
  }

  const edgesFrom = (nodeId) => graph.edges.filter(e => e.source === nodeId)

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Application Map</h1>
      <p className="text-sm text-gray-500">
        {graph.nodes.length} nodes, {graph.edges.length} relationships. Frontend→API links are heuristic
        (detected via fetch/axios call matching) and labeled as such.
      </p>

      {['repository', 'file', 'frontend_component', 'endpoint', 'function'].map(type => (
        byType[type] && (
          <div key={type} className="card">
            <div className="text-xs text-gray-500 uppercase mb-3">{type.replace('_', ' ')} ({byType[type].length})</div>
            <div className="space-y-2">
              {byType[type].slice(0, 50).map(n => (
                <div key={n.id} className={`border rounded-md px-3 py-2 text-sm ${TYPE_COLORS[type] || 'bg-gray-800'}`}>
                  <div className="font-mono">{n.label}</div>
                  {edgesFrom(n.id).length > 0 && (
                    <div className="mt-1 text-xs text-gray-400">
                      {edgesFrom(n.id).map((e, i) => (
                        <div key={i}>→ ({e.relation}) {e.target.split('::').pop()}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {byType[type].length > 50 && (
                <div className="text-xs text-gray-600">…and {byType[type].length - 50} more</div>
              )}
            </div>
          </div>
        )
      ))}
    </div>
  )
}
