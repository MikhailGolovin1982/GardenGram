"""Модели каталога GardenGram.

Два независимых механизма (см. CLAUDE.md → КАТАЛОГ):
- дерево категорий (Category) — «ЧТО это и ГДЕ лежит»;
- варианты товара (ProductVariant) — «в каком ВИДЕ продаётся и ПОЧЁМ».

Цена и остаток живут на уровне ВАРИАНТА, а не товара.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class Category(MPTTModel):
    """Узел единого дерева категорий каталога.

    Произвольная вложенность: декоративные растения → гортензии → метельчатые → сорта.
    Ветки верхнего уровня (растения, удобрения, горшки…) независимы и не смешиваются.
    Дерево строит и углубляет владелец через админку, без программиста.
    """

    name = models.CharField("Название", max_length=255)
    # parent=None → корневая ветка. PROTECT: непустую ветку нельзя снести случайно —
    # удаление потребует осознанных действий (сначала разобраться с детьми/товарами).
    parent = TreeForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Родительская категория",
        help_text="Пусто = категория верхнего уровня (корень дерева).",
    )
    # Задел под будущие ЧПУ-ссылки. Уникальность пока НЕ навязываем (дешёвый задел);
    # в админке заполняется автоматически из названия (prepopulated_fields).
    slug = models.SlugField(
        "Slug (для ссылок)",
        max_length=255,
        blank=True,
        help_text="Для будущих ЧПУ-ссылок. Можно оставить пустым.",
    )
    is_active = models.BooleanField(
        "Активна",
        default=True,
        help_text="Снимите галочку, чтобы скрыть ветку из каталога.",
    )

    class MPTTMeta:
        # Порядок сиблингов внутри уровня — по названию.
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Product(models.Model):
    """Карточка товара: один вид/сорт растения ИЛИ один сопутствующий товар.

    Сами формы продажи (горшок 5 л, мешок 50 л) — это варианты (ProductVariant).
    Поле `kind` — лёгкий маркер типа: держит общую модель варианта в дисциплине
    и даёт валидацию/удобную админку, не навязывая «растительные» поля всем.
    """

    class Kind(models.TextChoices):
        PLANT = "PLANT", "Растение"
        SUPPLY = "SUPPLY", "Сопутствующий товар"

    category = TreeForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Категория",
    )
    kind = models.CharField(
        "Тип товара",
        max_length=10,
        choices=Kind.choices,
        default=Kind.PLANT,
        help_text="Растение или сопутствующий товар. Влияет на набор полей варианта.",
    )
    name_ru = models.CharField("Название (рус.)", max_length=255)
    cultivar = models.CharField(
        "Сорт",
        max_length=255,
        blank=True,
        help_text="Необязательно. Есть не у всех позиций; нужен для будущей фильтрации.",
    )
    name_lat = models.CharField(
        "Латинское название",
        max_length=255,
        blank=True,
        help_text="Необязательно. Если заполнено — показывается как «Русское (Латинское)».",
    )
    description = models.TextField("Описание")
    is_published = models.BooleanField(
        "Опубликован",
        default=False,
        help_text="Черновик не виден в каталоге. Можно завести карточку и дозалить фото позже.",
    )
    # Нейтральный задел под мультипродавца (см. CLAUDE.md): nullable-FK ничего не стоит
    # сейчас и позволит позже привязать товары к продавцу без перестройки модели.
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Продавец",
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["name_ru"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        """Правило отображения названия (единое место для админки/API/фронта).

        Если задано латинское имя → «Русское (Латинское)», иначе только русское.
        """
        if self.name_lat:
            return f"{self.name_ru} ({self.name_lat})"
        return self.name_ru


class ProductImage(models.Model):
    """Фото товара (одно из нескольких). Переменное число (обычно 5–6), грузятся по мере возможности."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Товар",
    )
    image = models.ImageField("Фото", upload_to="products/%Y/%m/")
    position = models.PositiveIntegerField(
        "Порядок",
        default=0,
        help_text="Меньшее число = выше. Первое фото считается главным.",
    )
    alt = models.CharField(
        "Подпись (alt)",
        max_length=255,
        blank=True,
        help_text="Необязательно. Текст для доступности и SEO на будущем фронте.",
    )

    class Meta:
        verbose_name = "Фото товара"
        verbose_name_plural = "Фото товара"
        ordering = ["position", "id"]

    def __str__(self):
        return f"Фото #{self.position} для {self.product}"


def _trim_decimal(value):
    """«600.00» → «600», «5.0» → «5», «2.5» → «2.5» — для аккуратных подписей."""
    text = f"{value:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


class ProductVariant(models.Model):
    """Вариант товара: конкретная форма продажи со своей ценой и наличием.

    Один вид/сорт = одна карточка (Product), внутри — варианты, отличающиеся тем, КАК
    товар продаётся. Модель ОБЩАЯ: описывает и растения (ОКС/ЗКС + объём горшка),
    и сопутствующие товары (объём/размер фасовки). «Растительные» поля необязательны.
    """

    class RootSystem(models.TextChoices):
        OPEN = "OKS", "ОКС (открытая, без горшка)"
        CLOSED = "ZKS", "ЗКС (закрытая, в контейнере)"

    class Availability(models.TextChoices):
        IN_STOCK = "IN_STOCK", "В наличии"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Нет в наличии"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="Товар",
    )

    # --- Общие поля (у всех вариантов) ---
    # Decimal, а не float — это деньги. Цена базовая, всегда за 1 шт.
    price = models.DecimalField(
        "Цена за шт., ₽",
        max_digits=10,
        decimal_places=2,
    )
    availability_status = models.CharField(
        "Наличие",
        max_length=20,
        choices=Availability.choices,
        default=Availability.IN_STOCK,
        help_text="Главный источник правды о наличии. Товар не скрывается при отсутствии — "
        "показывается со статусом «Нет в наличии».",
    )
    quantity = models.PositiveIntegerField(
        "Количество (опц.)",
        null=True,
        blank=True,
        help_text="Необязательно. Точное число известно не всегда; наличием управляет статус.",
    )
    is_active = models.BooleanField(
        "Активен",
        default=True,
        help_text="Снимите галочку, чтобы скрыть вариант, не удаляя его.",
    )
    variant_label = models.CharField(
        "Подпись варианта",
        max_length=255,
        blank=True,
        help_text="Необязательно. Если пусто — подпись можно собрать из полей формы продажи.",
    )

    # --- Форма продажи (все необязательные, заполняются по типу товара) ---
    root_system = models.CharField(
        "Корневая система",
        max_length=3,
        choices=RootSystem.choices,
        blank=True,
        help_text="Только для растений. Для сопутствующих товаров оставьте пустым.",
    )
    volume_l = models.DecimalField(
        "Объём, л",
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Объём в литрах: горшок ЗКС у растения или фасовка (мешок) у грунта/торфа.",
    )
    size_label = models.CharField(
        "Размер (текст)",
        max_length=100,
        blank=True,
        help_text="Размер, не выражаемый литрами: диаметр горшка «P9», «50 кг» и т.п.",
    )
    age_note = models.CharField(
        "Возраст (заметка)",
        max_length=255,
        blank=True,
        help_text="Только для растений. Справочно; на цену влияет слабо.",
    )

    class Meta:
        verbose_name = "Вариант товара"
        verbose_name_plural = "Варианты товара"
        ordering = ["price"]

    @property
    def form_label(self):
        """Короткая форма продажи без цены: «ОКС», «ЗКС 5 л», «50 л», «P9».

        Растения — корневая система (+ объём для ЗКС); сопутствующие — объём/размер
        фасовки. Если владелец задал подпись вручную (variant_label) — используем её.
        """
        if self.variant_label:
            return self.variant_label
        parts = []
        if self.root_system:
            # «ОКС (открытая…)» → «ОКС»; «ЗКС (закрытая…)» → «ЗКС»
            parts.append(self.get_root_system_display().split()[0])
        if self.volume_l is not None:
            parts.append(f"{_trim_decimal(self.volume_l)} л")
        if self.size_label:
            parts.append(self.size_label)
        return " ".join(parts) or "вариант"

    @property
    def short_label(self):
        """Форма продажи + цена: «ОКС — 600 ₽», «ЗКС 5 л — 800 ₽». Заголовок блока в админке."""
        price = _trim_decimal(self.price) if self.price is not None else "?"
        return f"{self.form_label} — {price} ₽"

    def __str__(self):
        return self.short_label

    @property
    def is_available(self):
        """Удобный флаг для шаблонов/сериализаторов."""
        return self.availability_status == self.Availability.IN_STOCK

    def clean(self):
        """Лёгкая валидация дисциплины полей по типу товара.

        У сопутствующего товара нет корневой системы и «возраста» — не даём их задать,
        чтобы общая таблица не превращалась в свалку. Жёстче не делаем намеренно.
        """
        if self.product_id and self.product.kind == Product.Kind.SUPPLY:
            if self.root_system:
                raise ValidationError(
                    {"root_system": "У сопутствующего товара нет корневой системы."}
                )
            if self.age_note:
                raise ValidationError(
                    {"age_note": "Поле «Возраст» применимо только к растениям."}
                )
