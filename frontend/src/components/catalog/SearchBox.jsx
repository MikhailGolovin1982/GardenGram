import { useState } from 'react'

// Поиск по товарам. Ищем ПО САБМИТУ (Enter или кнопка), а не по мере ввода —
// для Шага 2 так проще и не спамит запросами (согласовано).
//
// Локальный стейт поля — это «черновик» ввода. Отправка зовёт onSubmit(текст),
// который страница превратит в ?search=... Пустой ввод трактуем как очистку.
function SearchBox({ initialValue = '', onSubmit }) {
  const [value, setValue] = useState(initialValue)

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit(value.trim())
  }

  return (
    <form className="search-box" onSubmit={handleSubmit} role="search">
      <input
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Поиск по каталогу…"
        aria-label="Поиск по каталогу"
      />
      <button type="submit">Найти</button>
    </form>
  )
}

export default SearchBox
