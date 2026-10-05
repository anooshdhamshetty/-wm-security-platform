import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { getReport } from '../services/api.js'

export default function Report() {
  const { id } = useParams()
  const [markdown, setMarkdown] = useState(null)
  const [loading, setLoading] = useState(false)

  async function generate() {
    setLoading(true)
    try {
      const md = await getReport(id)
      setMarkdown(md)
    } finally {
      setLoading(false)
    }
  }

  function download() {
    const blob = new Blob([markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `security-report-${id}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Security Assessment Report</h1>
        <div className="flex gap-2">
          <button
            onClick={generate} disabled={loading}
            className="bg-accent text-black text-sm font-medium px-3 py-1.5 rounded-md disabled:opacity-50"
          >
            {loading ? 'Generating…' : 'Generate Report'}
          </button>
          {markdown && (
            <button onClick={download} className="border border-border text-sm px-3 py-1.5 rounded-md">
              Download .md
            </button>
          )}
        </div>
      </div>

      {markdown ? (
        <div className="card">
          <pre className="whitespace-pre-wrap text-sm leading-relaxed">{markdown}</pre>
        </div>
      ) : (
        <div className="card text-center text-sm text-gray-500 py-8">
          Click "Generate Report" to compile findings, evidence, and coverage into a full report.
        </div>
      )}
    </div>
  )
}
