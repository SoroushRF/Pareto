import { useState, useEffect } from 'react'
import axios from 'axios'
import UploadZone from './components/UploadZone'
import SyllabusDashboard from './components/SyllabusDashboard'

function App() {
  const [status, setStatus] = useState('Connecting...')
  const [syllabusData, setSyllabusData] = useState(null)

  useEffect(() => {
    axios.get('http://localhost:8000/')
      .then(res => setStatus(res.data.status))
      .catch(err => setStatus('Backend Offline'))
  }, [])

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans selection:bg-blue-500/30">
      {/* Navbar */}
      <nav className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center font-bold text-white">
              P
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              Pareto
            </span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-slate-400">{status}</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {!syllabusData ? (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8">
            <div className="text-center space-y-4 max-w-2xl">
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white">
                The <span className="text-blue-500">80/20</span> Student
              </h1>
              <p className="text-lg text-slate-400">
                Stop wasting time on low-impact assignments. Upload your syllabus and let AI optimize your semester.
              </p>
            </div>

            <UploadZone onAnalysisComplete={setSyllabusData} />
          </div>
        ) : (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-white">Analysis Results</h2>
              <button
                onClick={() => setSyllabusData(null)}
                className="text-sm text-slate-400 hover:text-white transition-colors"
              >
                Upload Another
              </button>
            </div>
            <SyllabusDashboard data={syllabusData} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
