import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getEndpoints } from '../services/api.js'

export default function Endpoints() {
  const { id } = useParams()
  const [endpoints, setEndpoints] = useState([])

  useEffect(() => { getEndpoints(id).then(setEndpoints) }, [id])

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Discovered Endpoints ({endpoints.length})</h1>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-border">
              <th className="py-2 pr-4">Method</th>
              <th className="py-2 pr-4">Path</th>
              <th className="py-2 pr-4">Auth</th>
              <th className="py-2 pr-4">Handler</th>
              <th className="py-2 pr-4">Source</th>
              <th className="py-2 pr-4">Via</th>
            </tr>
          </thead>
          <tbody>
            {endpoints.map(ep => (
              <tr key={ep.id} className="border-b border-border/50">
                <td className="py-2 pr-4 font-mono text-accent">{ep.method}</td>
                <td className="py-2 pr-4 font-mono">{ep.path}</td>
                <td className="py-2 pr-4">
                  {ep.requires_auth === true && <span className="badge badge-medium">required</span>}
                  {ep.requires_auth === false && <span className="badge badge-info">not detected</span>}
                  {ep.requires_auth === null && <span className="badge badge-info">unknown</span>}
                </td>
                <td className="py-2 pr-4 text-gray-400">{ep.handler_name || '—'}</td>
                <td className="py-2 pr-4 text-gray-500 font-mono text-xs">
                  {ep.source_file}{ep.source_line ? `:${ep.source_line}` : ''}
                </td>
                <td className="py-2 pr-4 text-gray-500">{ep.discovered_via}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {endpoints.length === 0 && (
          <div className="text-sm text-gray-500 py-6 text-center">
            No endpoints yet. Run repository analysis from the Dashboard tab.
          </div>
        )}
      </div>
    </div>
  )
}
