import { Routes, Route, NavLink, useParams } from 'react-router-dom'
import NewAssessment from './pages/NewAssessment.jsx'
import AssessmentList from './pages/AssessmentList.jsx'
import Dashboard from './pages/Dashboard.jsx'
import ApplicationMap from './pages/ApplicationMap.jsx'
import Endpoints from './pages/Endpoints.jsx'
import Findings from './pages/Findings.jsx'
import TestResults from './pages/TestResults.jsx'
import Report from './pages/Report.jsx'

function AssessmentNav() {
  const { id } = useParams()
  const base = `/assessments/${id}`
  const linkClass = ({ isActive }) =>
    `px-3 py-2 rounded-md text-sm ${isActive ? 'bg-accent/20 text-accent' : 'text-gray-400 hover:text-gray-200'}`
  return (
    <nav className="flex gap-1 border-b border-border mb-6 pb-2 flex-wrap">
      <NavLink to={`${base}`} end className={linkClass}>Dashboard</NavLink>
      <NavLink to={`${base}/map`} className={linkClass}>Application Map</NavLink>
      <NavLink to={`${base}/endpoints`} className={linkClass}>Endpoints</NavLink>
      <NavLink to={`${base}/findings`} className={linkClass}>Findings</NavLink>
      <NavLink to={`${base}/tests`} className={linkClass}>Test Results</NavLink>
      <NavLink to={`${base}/report`} className={linkClass}>Report</NavLink>
    </nav>
  )
}

function AssessmentLayout({ children }) {
  return (
    <div>
      <AssessmentNav />
      {children}
    </div>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <NavLink to="/" className="text-lg font-semibold text-gray-100">
          🛡️ World Monitor <span className="text-accent">Security Platform</span>
        </NavLink>
        <NavLink to="/new" className="bg-accent text-black text-sm font-medium px-3 py-1.5 rounded-md">
          + New Assessment
        </NavLink>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<AssessmentList />} />
          <Route path="/new" element={<NewAssessment />} />
          <Route path="/assessments/:id" element={<AssessmentLayout><Dashboard /></AssessmentLayout>} />
          <Route path="/assessments/:id/map" element={<AssessmentLayout><ApplicationMap /></AssessmentLayout>} />
          <Route path="/assessments/:id/endpoints" element={<AssessmentLayout><Endpoints /></AssessmentLayout>} />
          <Route path="/assessments/:id/findings" element={<AssessmentLayout><Findings /></AssessmentLayout>} />
          <Route path="/assessments/:id/tests" element={<AssessmentLayout><TestResults /></AssessmentLayout>} />
          <Route path="/assessments/:id/report" element={<AssessmentLayout><Report /></AssessmentLayout>} />
        </Routes>
      </main>
    </div>
  )
}
