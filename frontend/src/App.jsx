import { useState, useEffect } from 'react'
import axios from 'axios'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot, Sun, Moon } from 'lucide-react'
import UploadZone from './components/UploadZone'
import SyllabusDashboard from './components/SyllabusDashboard'
import logo from './assets/logo.png' 

function App() {
  const [status, setStatus] = useState('Connecting...')
  const [modelInfo, setModelInfo] = useState(null)
  const [syllabusData, setSyllabusData] = useState(null)
  
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') || 'light'
    }
    return 'light'
  })

  useEffect(() => {
    const root = window.document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = (event) => {
    const isAppearanceTransition = document.startViewTransition
      && !window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (!isAppearanceTransition) {
      setTheme(prev => (prev === 'light' ? 'dark' : 'light'))
      return
    }

    const x = event.clientX
    const y = event.clientY
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y)
    )

    const transition = document.startViewTransition(async () => {
      const nextTheme = theme === 'light' ? 'dark' : 'light'
      setTheme(nextTheme)
      
      // Manually toggle class for the API screenshot
      if (nextTheme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    })

    transition.ready.then(() => {
      const clipPath = [
        `circle(0px at ${x}px ${y}px)`,
        `circle(${endRadius}px at ${x}px ${y}px)`,
      ]
      document.documentElement.animate(
        {
          clipPath: clipPath,
        },
        {
          duration: 500,
          easing: 'ease-in-out',
          pseudoElement: '::view-transition-new(root)',
        }
      )
    })
  }

  useEffect(() => {
    axios.get('http://localhost:8000/')
      .then(res => {
        setStatus(res.data.status)
        setModelInfo(res.data.model)
      })
      .catch(err => {
        setStatus('Backend Offline')
        setModelInfo(null)
      })
  }, [])

  const goHome = () => setSyllabusData(null);

  return (
    <div className="min-h-screen bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-sans selection:bg-blue-100 dark:selection:bg-blue-900/40 transition-colors duration-500 overflow-x-hidden">
      {/* Navbar */}
      <nav className="border-b border-slate-100 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md sticky top-0 z-50 shadow-sm transition-colors duration-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          
          <div className="flex items-center space-x-8">
            {/* Logo Area */}
            <button 
              onClick={goHome}
              className="flex items-center space-x-3 hover:opacity-80 transition-opacity focus:outline-none"
            >
              <img 
                src={logo} 
                alt="Pareto Logo" 
                className="w-8 h-8 object-contain" 
              />
              <span className="text-xl font-extrabold tracking-tight text-[#002A5C] dark:text-white transition-colors duration-500">
                Pareto
              </span>
            </button>

            {/* Model Badge */}
            {modelInfo && (
              <div className="hidden md:flex items-center px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 border border-blue-100 dark:border-blue-800/50 text-[10px] uppercase font-bold tracking-wider text-blue-700 dark:text-blue-400 transition-colors duration-500">
                <Bot className="w-3 h-3 mr-1.5" />
                {modelInfo}
              </div>
            )}
          </div>

          {/* Right Actions */}
          <div className="flex items-center space-x-6">
            {/* Morphing Theme Toggle */}
            <button
              onClick={(e) => toggleTheme(e)}
              className="relative w-12 h-12 flex items-center justify-center rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:scale-110 active:scale-95 transition-all duration-300 focus:outline-none overflow-hidden"
              aria-label="Toggle appearance"
              title="Toggle appearance"
            >
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={theme}
                  initial={{ y: 20, rotate: theme === 'light' ? 90 : -90, opacity: 0, scale: 0.5 }}
                  animate={{ y: 0, rotate: 0, opacity: 1, scale: 1 }}
                  exit={{ y: -20, rotate: theme === 'light' ? -90 : 90, opacity: 0, scale: 0.5 }}
                  transition={{ 
                    type: "spring",
                    stiffness: 300,
                    damping: 20
                  }}
                  className="flex items-center justify-center"
                >
                  {theme === 'light' ? (
                    <Sun size={24} className="stroke-[2.5px]" />
                  ) : (
                    <Moon size={24} className="stroke-[2.5px]" />
                  )}
                </motion.div>
              </AnimatePresence>
            </button>

            {/* Status Indicator */}
            <div className="flex items-center space-x-4 border-l border-slate-200 dark:border-slate-700 transition-colors duration-500 pl-6">
              <div className="flex items-center space-x-2 text-[10px] uppercase font-bold tracking-widest">
                <span className={`w-2 h-2 rounded-full ${
                  status === 'Connecting...' ? 'bg-yellow-500' : 
                  status === 'Backend Offline' ? 'bg-red-500' : 
                  'bg-emerald-500 animate-pulse'
                }`}></span>
                <span className="text-slate-400 dark:text-slate-500 transition-colors duration-500">{status}</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {!syllabusData ? (
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="text-center space-y-4 max-w-2xl">
              <h1 className="text-4xl md:text-6xl font-black tracking-tighter text-slate-900 dark:text-white transition-colors duration-500">
                The <span className="text-blue-600 dark:text-blue-500">80/20</span> Student
              </h1>
              <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 transition-colors duration-500 max-w-lg mx-auto leading-relaxed">
                Stop wasting time on low-impact assignments. Upload your syllabus and let AI optimize your semester.
              </p>
            </div>

            <UploadZone onAnalysisComplete={setSyllabusData} />
          </div>
        ) : (
          <div className="space-y-8 animate-in fade-in duration-700">
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white transition-colors duration-500">Analysis Results</h2>
                {(syllabusData.filename || syllabusData.raw_omniscient_json?.syllabus_metadata?.source_file_name) && (
                  <p className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider transition-colors duration-500">
                    File: {syllabusData.filename || syllabusData.raw_omniscient_json?.syllabus_metadata?.source_file_name}
                  </p>
                )}
              </div>
              <button
                onClick={goHome}
                className="text-sm font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-all active:scale-95"
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