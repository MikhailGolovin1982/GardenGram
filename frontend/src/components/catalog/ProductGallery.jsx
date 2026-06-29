import { useState } from 'react'

// Простая галерея фото товара без библиотек (Шаг 3).
// Три случая по числу фото:
//  - нет фото  → крупная заглушка «Нет фото» (сейчас самый частый случай);
//  - одно фото → просто главное изображение;
//  - несколько → главное + ряд миниатюр, клик по миниатюре меняет главное.
// Зум/слайдер/лайтбокс — backlog, не Шаг 3.
//
// images[] приходят с бэкенда уже упорядоченными по position, image — абсолютный URL.
// alt берём из самой картинки, а если он пуст — подставляем имя товара (проп alt).
function ProductGallery({ images = [], alt }) {
  // Индекс выбранной (главной) картинки. Хранится локально — это чистый UI-стейт.
  const [activeIndex, setActiveIndex] = useState(0)

  if (images.length === 0) {
    return (
      <div className="product-thumb product-thumb--large">
        <span className="product-thumb-empty">Нет фото</span>
      </div>
    )
  }

  const active = images[activeIndex] ?? images[0]

  return (
    <div className="product-gallery">
      <div className="gallery-main">
        <img src={active.image} alt={active.alt || alt} loading="lazy" />
      </div>

      {/* Миниатюры показываем только когда фото больше одного. */}
      {images.length > 1 && (
        <div className="gallery-thumbs">
          {images.map((img, index) => (
            <button
              key={img.id}
              type="button"
              className={
                'gallery-thumb' + (index === activeIndex ? ' gallery-thumb--active' : '')
              }
              onClick={() => setActiveIndex(index)}
            >
              <img src={img.image} alt={img.alt || alt} loading="lazy" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default ProductGallery
