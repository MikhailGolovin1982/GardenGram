import { useEffect, useState } from 'react'

// Шаг 0: доказываем связь фронта с бэкендом.
// Адрес API берём из переменной окружения (без хардкода) — см. .env.local.
const API_BASE = import.meta.env.VITE_API_BASE_URL

function App() {
  // status: 'loading' | 'ok' | 'error'
  const [status, setStatus] = useState('loading')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!API_BASE) {
      setStatus('error')
      setError('VITE_API_BASE_URL не задан. Проверь файл frontend/.env.local и перезапусти npm run dev.')
      return
    }

    const url = `${API_BASE}/catalog/categories/`
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)
        return res.json()
      })
      .then((json) => {
        setData(json)
        setStatus('ok')
      })
      .catch((err) => {
        setError(String(err))
        setStatus('error')
      })
  }, [])

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: '1rem', lineHeight: 1.4 }}>
      <h1>GardenGram — проверка связи (Шаг 0)</h1>
      <p style={{ color: '#666' }}>
        API: <code>{API_BASE || '(не задан)'}</code>
      </p>

      {status === 'loading' && <p>Загрузка категорий…</p>}

      {status === 'error' && (
        <div style={{ color: '#b00020' }}>
          <p><strong>Ошибка связи с API:</strong></p>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{error}</pre>
          <p style={{ color: '#666' }}>
            Частые причины: порт 8000 не публичный, Django не запущен, или не задан VITE_API_BASE_URL.
          </p>
        </div>
      )}

      {status === 'ok' && (
        <div>
          <p style={{ color: '#0a7d00' }}>
            <strong>✓ Связь работает.</strong> Сырой ответ <code>/catalog/categories/</code>:
          </p>
          <pre
            style={{
              background: '#f5f5f5',
              padding: '1rem',
              borderRadius: 8,
              overflowX: 'auto',
              fontSize: 13,
            }}
          >
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </main>
  )
}

export default App
