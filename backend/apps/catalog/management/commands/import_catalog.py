"""Импорт каталога из CSV.

Идемпотентность (повторный запуск не плодит дубли):
- категория ищется/создаётся по полному пути «A/B/C» (по паре имя+родитель на каждом уровне);
- товар ищется по (name_ru + категория);
- вариант ищется по (товар + root_system + price).

По умолчанию работает в режиме DRY-RUN (ничего не пишет в базу).
Реальная запись — только с флагом --commit.

Запуск:
    python manage.py import_catalog _scratch/catalog_import.csv            # пробный прогон
    python manage.py import_catalog _scratch/catalog_import.csv --commit   # реальная запись
"""

import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Category, Product, ProductVariant

# CSV отдаёт человекочитаемые значения; модель хранит коды. Сопоставляем явно.
ROOT_SYSTEM_MAP = {
    "ОКС": ProductVariant.RootSystem.OPEN,    # → "OKS"
    "ЗКС": ProductVariant.RootSystem.CLOSED,  # → "ZKS"
    "": "",                                   # сопутствующие товары — без корневой системы
}
VALID_KINDS = {k for k, _ in Product.Kind.choices}
VALID_AVAIL = {v for v, _ in ProductVariant.Availability.choices}


class Command(BaseCommand):
    help = "Импорт каталога (товары + варианты) из CSV. По умолчанию dry-run."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Путь к CSV-файлу (разделитель ;).")
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Реально записать в базу. Без флага — только пробный прогон (dry-run).",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        commit = options["commit"]

        rows = self._read_rows(csv_path)
        if not rows:
            raise CommandError("CSV пуст или не содержит строк данных.")

        # Всё делаем внутри транзакции. В режиме dry-run в конце откатываем —
        # так get_or_create честно сообщает, что создалось бы, не оставляя следов.
        with transaction.atomic():
            self._import(rows)
            if not commit:
                transaction.set_rollback(True)

        mode = "РЕАЛЬНЫЙ ИМПОРТ (записано в базу)" if commit else "DRY-RUN (база не изменена)"
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(f"Режим: {mode}"))
        if not commit:
            self.stdout.write("Повторите с флагом --commit, чтобы записать данные.")

    # --- чтение и валидация CSV ---

    def _read_rows(self, csv_path):
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                rows = [r for r in reader if any((v or "").strip() for v in r.values())]
        except FileNotFoundError:
            raise CommandError(f"Файл не найден: {csv_path}")

        for i, r in enumerate(rows, start=2):  # +2: шапка + 1-based
            name = (r.get("name_ru") or "").strip()
            if not name:
                raise CommandError(f"Строка {i}: пустое название (name_ru).")
            if not (r.get("price") or "").strip():
                raise CommandError(f"Строка {i}: пустая цена (price).")
            try:
                Decimal(r["price"].strip())
            except (InvalidOperation, AttributeError):
                raise CommandError(f"Строка {i}: цена не число: {r['price']!r}.")
            kind = (r.get("kind") or "").strip()
            if kind not in VALID_KINDS:
                raise CommandError(f"Строка {i}: неизвестный kind {kind!r}.")
            avail = (r.get("availability") or "").strip()
            if avail not in VALID_AVAIL:
                raise CommandError(f"Строка {i}: неизвестный availability {avail!r}.")
            rs = (r.get("root_system") or "").strip()
            if rs not in ROOT_SYSTEM_MAP:
                raise CommandError(f"Строка {i}: неизвестная корневая система {rs!r}.")
        return rows

    # --- собственно импорт ---

    def _import(self, rows):
        prod_created = prod_existing = 0
        var_created = var_existing = 0
        # Узлы категорий считаем по distinct id, чтобы повторы пути в строках не плодили счёт.
        cat_referenced = set()
        cat_created_ids = set()

        for r in rows:
            path = (r["category"] or "").strip()
            category, made_ids, ref_ids = self._resolve_category(path)
            cat_created_ids |= made_ids
            cat_referenced |= ref_ids

            name = r["name_ru"].strip()
            product, p_made = Product.objects.get_or_create(
                name_ru=name,
                category=category,
                defaults={
                    "kind": r["kind"].strip(),
                    "name_lat": (r.get("name_lat") or "").strip(),
                    "cultivar": (r.get("cultivar") or "").strip(),
                    "description": (r.get("description") or "").strip(),
                    # черновик: товар появится в каталоге после публикации (фото зальют позже)
                    "is_published": False,
                },
            )
            prod_created += p_made
            prod_existing += (not p_made)

            price = Decimal(r["price"].strip())
            root_system = ROOT_SYSTEM_MAP[(r.get("root_system") or "").strip()]
            _, v_made = ProductVariant.objects.get_or_create(
                product=product,
                root_system=root_system,
                price=price,
                defaults={"availability_status": r["availability"].strip()},
            )
            var_created += v_made
            var_existing += (not v_made)

            verb = "СОЗДАМ" if (p_made or v_made) else "есть"
            label = f"{root_system or '—'} {price:g}₽"
            self.stdout.write(
                f"  [{verb:6}] {name}  ({label}, {r['availability'].strip()})  → {path}"
            )

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Итого:"))
        self.stdout.write(
            f"  Категории:  создать {len(cat_created_ids)}, "
            f"уже есть {len(cat_referenced - cat_created_ids)}"
        )
        self.stdout.write(f"  Товары:     создать {prod_created}, уже есть {prod_existing}")
        self.stdout.write(f"  Варианты:   создать {var_created}, уже есть {var_existing}")

    def _resolve_category(self, path):
        """Идёт по пути «A/B/C», создавая недостающие узлы.

        Возвращает (лист, {id созданных узлов}, {id всех узлов пути}).
        """
        if not path:
            raise CommandError("Пустой путь категории в строке.")
        parent = None
        node = None
        created_ids, referenced_ids = set(), set()
        for name in (p.strip() for p in path.split("/")):
            node, made = Category.objects.get_or_create(name=name, parent=parent)
            referenced_ids.add(node.pk)
            if made:
                created_ids.add(node.pk)
            parent = node
        return node, created_ids, referenced_ids
