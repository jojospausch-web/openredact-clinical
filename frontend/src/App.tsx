import React, { useEffect, useState } from 'react'
import './App.css'

interface HealthResponse {
  status: string
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => setError(err.message))
  }, [])

  return (
    <div className="App">
      <header className="App-header">
        <h1>OpenRedact Clinical</h1>
        <p>Medical Document Anonymization for German Clinical Documents</p>
        <div className="status">
          {health && <p>✅ Backend Status: {health.status}</p>}
          {error && <p>❌ Backend Error: {error}</p>}
        </div>
      </header>
    </div>
  )
}

export default App
