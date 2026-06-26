import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

import { getCategoryTree, getProducts } from '../api/catalog'
import { useApi } from '../hooks/useApi'
import { findNode, findPath } from '../utils/catalogTree'
import CategoryList from '../components/catalog/CategoryList'
import Breadcrumbs from '../components/catalog/Breadcrumbs'
import SearchBox from '../components/catalog/SearchBox'
import ProductGrid from '../components/catalog/ProductGrid'

// Сердце сайта. Навигация целиком в URL (?category=id / ?search=строка), поэтому
// «назад» браузера работает сам. Три взаимоисключающих режима:
//   - корень  (/catalog)            → только категории верхнего уровня
//   - ветка   (?category=id)        → крошки + подкатегории + товары ветки
//   - поиск   (?search=строка)      → плоская сетка результатов, дерево скрыто
function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const categoryParam = searchParams.get('category')
  const searchParam = searchParams.get('search') || ''
  const categoryId = categoryParam ? Number(categoryParam) : null

  const mode = searchParam ? 'search' : categoryId ? 'branch' : 'root'

  // --- Дерево категорий: грузим ОДИН раз и держим в стейте (useApi с [] зависимостями).
  const {
    data: tree,
    loading: treeLoading,
    error: treeError,
  } = useApi(getCategoryTree, [])

  // По дереву (без новых запросов) считаем подкатегории и путь для крошек.
  const currentNode = mode === 'branch' && tree ? findNode(tree, categoryId) : null
  const path = mode === 'branch' && tree ? findPath(tree, categoryId) : []
  const subcategories = currentNode ? currentNode.children : []

  // --- Товары: отдельная логика, т.к. есть пагинация «Показать ещё» (накопление страниц).
  const [products, setProducts] = useState([])
  const [count, setCount] = useState(0)
  const [next, setNext] = useState(null)
  const [productsLoading, setProductsLoading] = useState(false)
  const [productsError, setProductsError] = useState(null)
  const [moreLoading, setMoreLoading] = useState(false)

  // Перезагрузка первой страницы при смене режима/категории/поискового запроса.
  useEffect(() => {
    // В корне товары не грузим (там только верхнеуровневые категории).
    if (mode === 'root') {
      setProducts([])
      setCount(0)
      setNext(null)
      setProductsError(null)
      return
    }

    let cancelled = false // гасим устаревший ответ при быстром переключении
    setProductsLoading(true)
    setProductsError(null)
    setProducts([])

    getProducts({
      category: categoryId || undefined,
      search: searchParam || undefined,
      page: 1,
    })
      .then((res) => {
        if (cancelled) return
        setProducts(res.results)
        setCount(res.count)
        setNext(res.next)
      })
      .catch((err) => {
        if (!cancelled) setProductsError(err)
      })
      .finally(() => {
        if (!cancelled) setProductsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [mode, categoryId, searchParam])

  // «Показать ещё»: следующая страница дописывается к текущему списку.
  // next — абсолютный URL с ?page=N; вытаскиваем номер и зовём свой getProducts.
  const loadMore = useCallback(() => {
    if (!next) return
    const page = new URL(next).searchParams.get('page')
    setMoreLoading(true)
    getProducts({
      category: categoryId || undefined,
      search: searchParam || undefined,
      page,
    })
      .then((res) => {
        setProducts((prev) => [...prev, ...res.results])
        setNext(res.next)
      })
      .finally(() => setMoreLoading(false))
  }, [next, categoryId, searchParam])

  // Сабмит поиска: непустой запрос → ?search=…; пустой → возврат к дереву (/catalog).
  // setSearchParams создаёт новую запись истории → «назад» работает.
  function handleSearch(text) {
    if (text) {
      setSearchParams({ search: text })
    } else {
      setSearchParams({})
    }
  }

  // Общий блок вывода товаров (используется в ветке и в поиске).
  function renderProducts(emptyText) {
    if (productsLoading) return <p>Загрузка товаров…</p>
    if (productsError) {
      return <p className="catalog-error">{productsError.message}</p>
    }
    if (products.length === 0) {
      return emptyText ? <p className="catalog-empty">{emptyText}</p> : null
    }
    return (
      <>
        <ProductGrid products={products} />
        {next && (
          <div className="load-more">
            <button type="button" onClick={loadMore} disabled={moreLoading}>
              {moreLoading ? 'Загрузка…' : 'Показать ещё'}
            </button>
          </div>
        )}
      </>
    )
  }

  return (
    <section className="catalog">
      <h1>Каталог</h1>

      {/* key сбрасывает черновик поля при смене URL (напр. кнопкой «назад»). */}
      <SearchBox key={searchParam} initialValue={searchParam} onSubmit={handleSearch} />

      {/* Дерево нужно для корня и ветки; для поиска оно скрыто. */}
      {mode !== 'search' && treeLoading && <p>Загрузка категорий…</p>}
      {mode !== 'search' && treeError && (
        <p className="catalog-error">{treeError.message}</p>
      )}

      {/* Корень: только категории верхнего уровня. */}
      {mode === 'root' && tree && <CategoryList nodes={tree} />}

      {/* Ветка: крошки + подкатегории + товары ветки на одном экране. */}
      {mode === 'branch' && tree && (
        <>
          <Breadcrumbs path={path} />
          {subcategories.length > 0 && (
            <CategoryList nodes={subcategories} />
          )}
          {/* «Пусто» показываем только если у ветки нет и подкатегорий. */}
          {renderProducts(subcategories.length === 0 ? 'В этой категории пока нет товаров.' : null)}
        </>
      )}

      {/* Поиск: плоская сетка результатов, мимо дерева. */}
      {mode === 'search' && (
        <>
          {!productsLoading && !productsError && (
            <p className="search-summary">
              {count > 0 ? `Найдено: ${count}` : null}
            </p>
          )}
          {renderProducts('Ничего не найдено.')}
        </>
      )}
    </section>
  )
}

export default CatalogPage
