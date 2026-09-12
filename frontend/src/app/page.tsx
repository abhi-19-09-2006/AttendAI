'use client'

import { useEffect, useState } from 'react'

interface ApiHealth {
  status: string
  timestamp: string
  environment: string
  version: string
}

export default function Home() {
  const [apiHealth, setApiHealth] = useState<ApiHealth | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/health`)

        if (response.ok) {
          const data = await response.json()
          setApiHealth(data)
        } else {
          setError('Backend API returned an error')
        }
      } catch (err) {
        setError('Unable to connect to backend API')
        console.error('Backend health check failed:', err)
      }
    }

    checkBackendHealth()
  }, [])

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-24">
      <div className="max-w-4xl w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-6xl font-bold text-primary-600 mb-4">
            AttendAI
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300">
            AI-Powered Automated Student Absence Communication Platform
          </p>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
          {/* Frontend Status */}
          <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2 border-green-500">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold">Frontend</h2>
              <span className="px-3 py-1 bg-green-500 text-white rounded-full text-sm">
                Running
              </span>
            </div>
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              <p><strong>Framework:</strong> Next.js 14</p>
              <p><strong>Status:</strong> Operational</p>
              <p><strong>Port:</strong> 3000</p>
            </div>
          </div>

          {/* Backend Status */}
          <div className={`p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2 ${
            apiHealth ? 'border-green-500' : 'border-yellow-500'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold">Backend API</h2>
              <span className={`px-3 py-1 rounded-full text-sm text-white ${
                apiHealth ? 'bg-green-500' : 'bg-yellow-500'
              }`}>
                {apiHealth ? 'Healthy' : 'Checking...'}
              </span>
            </div>
            {apiHealth ? (
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
                <p><strong>Framework:</strong> FastAPI</p>
                <p><strong>Environment:</strong> {apiHealth.environment}</p>
                <p><strong>Version:</strong> {apiHealth.version}</p>
                <p><strong>Status:</strong> {apiHealth.status}</p>
              </div>
            ) : error ? (
              <p className="text-sm text-yellow-600 dark:text-yellow-400">{error}</p>
            ) : (
              <p className="text-sm text-gray-500">Connecting...</p>
            )}
          </div>
        </div>

        {/* Features */}
        <div className="mt-12">
          <h2 className="text-3xl font-semibold text-center mb-6">Key Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { title: 'AI Voice Calls', desc: 'Automated parent communication' },
              { title: 'Smart Extraction', desc: 'Structured absence information' },
              { title: 'Faculty Dashboard', desc: 'Real-time insights & analytics' },
              { title: 'Follow-up Management', desc: 'Automated task tracking' },
              { title: 'Comprehensive Reports', desc: 'Data-driven decisions' },
              { title: 'Secure & Compliant', desc: 'FERPA-aware architecture' },
            ].map((feature, idx) => (
              <div
                key={idx}
                className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700"
              >
                <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-300">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Links */}
        <div className="mt-12 text-center space-x-4">
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
          >
            API Documentation
          </a>
          <a
            href="/dashboard"
            className="inline-block px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
          >
            Dashboard (Coming Soon)
          </a>
        </div>

        {/* Development Notice */}
        <div className="mt-8 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <p className="text-sm text-yellow-800 dark:text-yellow-200 text-center">
            <strong>⚠️ Development Mode:</strong> This is Phase 1 (Foundation).
            Core features are under active development.
          </p>
        </div>
      </div>
    </main>
  )
}
