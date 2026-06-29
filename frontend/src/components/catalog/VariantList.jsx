import { formatPrice } from '../../utils/format'
import AddToCartButton from '../cart/AddToCartButton'

// Список вариантов товара строками (Шаг 3, «Вариант А»).
// Показываем ВСЕ пришедшие варианты — они уже только активные и отсортированы по цене.
// Шаг 4: у доступного варианта — кнопка «В корзину»; у недоступного кнопки нет.
//
// Каждый вариант — это «как товар продаётся и почём»: форма продажи + своя цена + наличие.
// form_label («ОКС», «ЗКС 5 л», «50 л») собран на бэкенде — берём готовым, не строим сами.
function VariantList({ variants = [] }) {
  // Нет активных вариантов → честный фолбэк (как в карточке списка при отсутствии цены).
  if (variants.length === 0) {
    return <p className="variant-empty">Цена уточняется</p>
  }

  return (
    <div className="variant-block">
      <h2 className="variant-title">Варианты</h2>
      <ul className="variant-list">
        {variants.map((variant) => (
          <li
            key={variant.id}
            // Недоступные не прячем (важно для сезонных растений), а приглушаем.
            className={'variant-row' + (variant.is_available ? '' : ' variant-out')}
          >
            <span className="variant-form">
              {variant.form_label}
              {/* Возраст — необязательная справочная заметка, показываем тускло. */}
              {variant.age_note && (
                <span className="variant-age">{variant.age_note}</span>
              )}
            </span>
            <span className="variant-meta">
              <span className="variant-price">{formatPrice(variant.price)}</span>
              <span className="variant-status">
                {variant.is_available ? 'В наличии' : 'Нет в наличии'}
              </span>
              {/* Кнопка только у доступного варианта. Недоступный остаётся
                  приглушённым (.variant-out) без кнопки — добавить его нельзя. */}
              {variant.is_available && <AddToCartButton variantId={variant.id} />}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default VariantList
