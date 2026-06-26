// Маленький хук загрузки данных: убирает копипасту loading/error/data из страниц.
// Принимает функцию-запрос и список зависимостей (как у useEffect). При смене
// зависимостей перезапрашивает. Один аккуратный паттерн на все экраны.

import { useEffect, useState, useCallback } from 'react'

export function useApi(asyncFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Оборачиваем запрос в useCallback, привязанный к deps, чтобы reload() и эффект
  // всегда звали актуальную версию. eslint попросил бы asyncFn в зависимостях, но
  // мы сознательно завязываемся на deps, переданные вызывающим кодом.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(asyncFn, deps)

  useEffect(() => {
    // Флаг гонки: если зависимости сменились до прихода ответа — игнорируем старый.
    let cancelled = false
    setLoading(true)
    setError(null)

    run()
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    // Очистка эффекта: помечаем прошлый запрос неактуальным.
    return () => {
      cancelled = true
    }
  }, [run])

  return { data, loading, error }
}
