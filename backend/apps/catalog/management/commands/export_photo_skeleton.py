"""Экспорт «скелета папок» под загрузку фотографий товаров (ШАГ A плана PLAN_PHOTOS.md).

Пробегает по каталогу и строит дерево ПУСТЫХ папок, сгруппированных по дереву категорий,
где каждый товар — это листовая папка с ID в начале имени:

    photos_upload/
    ├── Декоративные растения/Гортензии/Метельчатые/
    │   └── 0004__Гортензия метельчатая «Фрайз Мельба»/   ← сюда кладут фото
    └── _МАНИФЕСТ.csv                                      ← чек-лист (id; путь; товар; фото сейчас)

Привязка фото к товару при импорте идёт ТОЛЬКО по «ID__» в имени листовой папки
(см. import_photos). Категории-папки и текст после «__» — для удобной навигации
на телефоне, на матчинг не влияют.

Команда НИЧЕГО не пишет в базу (read-only). Создаёт папки на диске и, по флагу, zip.

Запуск (из папки backend/):
    python manage.py export_photo_skeleton                       # → _scratch/photos_upload/
    python manage.py export_photo_skeleton --out /путь/куда      # своя папка назначения
    python manage.py export_photo_skeleton --zip                 # ещё и упаковать в .zip
"""

import csv
import shutil
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Product

# Символы, недопустимые/неудобные в именах папок. Заменяем на дефис, чтобы не сломать
# файловую систему (главное — «/»: это разделитель пути).
_BAD_CHARS = '/\\:*?"<>|\n\r\t'


def _safe(name):
    """Имя категории/товара → безопасное имя папки (на матчинг не влияет, только косметика)."""
    name = (name or "").strip()
    for ch in _BAD_CHARS:
        name = name.replace(ch, "-")
    # Точки/пробелы в конце имени неудобны на части ФС — подчистим.
    return name.rstrip(" .") or "—"


class Command(BaseCommand):
    help = "Генерирует дерево пустых папок под фото товаров (по ID) + _МАНИФЕСТ.csv. Базу не трогает."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="_scratch/photos_upload",
            help="Куда сложить скелет папок (по умолчанию _scratch/photos_upload).",
        )
        parser.add_argument(
            "--zip",
            action="store_true",
            dest="make_zip",
            help="Дополнительно упаковать получившуюся папку в <out>.zip для скачивания.",
        )

    def handle(self, *args, **options):
        out = Path(options["out"])
        if out.exists():
            raise CommandError(
                f"Папка уже существует: {out}. Удалите её или укажите другую через --out, "
                f"чтобы случайно не смешать со старым содержимым."
            )

        # Тащим товары вместе с категорией и считаем фото одним запросом.
        products = (
            Product.objects.select_related("category")
            .prefetch_related("category__parent")  # ancestors всё равно дёрнем ниже
            .all()
            .order_by("id")
        )

        out.mkdir(parents=True)
        manifest_rows = []
        made = 0

        for p in products:
            # Путь категории строим через MPTT-предков: «A / B / C».
            ancestors = p.category.get_ancestors(include_self=True)
            cat_parts = [_safe(c.name) for c in ancestors]
            cat_path = "/".join(c.name for c in ancestors)  # для манифеста — как есть

            leaf = f"{p.id:04d}__{_safe(p.display_name)}"
            folder = out.joinpath(*cat_parts, leaf)
            folder.mkdir(parents=True, exist_ok=True)
            made += 1

            photos_now = p.images.count()
            manifest_rows.append(
                {
                    "id": p.id,
                    "category": cat_path,
                    "product": p.display_name,
                    "photos_now": photos_now,
                }
            )

        # _МАНИФЕСТ.csv — чек-лист «что ещё без фото». Кладём в корень скелета.
        manifest_path = out / "_МАНИФЕСТ.csv"
        with open(manifest_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "category", "product", "photos_now"], delimiter=";"
            )
            writer.writeheader()
            writer.writerows(manifest_rows)

        self.stdout.write(self.style.MIGRATE_HEADING("Скелет папок создан:"))
        self.stdout.write(f"  Папок-товаров: {made}")
        self.stdout.write(f"  Манифест:      {manifest_path}")
        self.stdout.write(f"  Корень:        {out}")

        no_photo = sum(1 for r in manifest_rows if r["photos_now"] == 0)
        self.stdout.write(f"  Без фото пока: {no_photo} из {made}")

        if options["make_zip"]:
            archive = shutil.make_archive(str(out), "zip", root_dir=out)
            self.stdout.write(self.style.SUCCESS(f"  ZIP:           {archive}"))

        self.stdout.write("")
        self.stdout.write(
            "Разложите фото по папкам (имена 1.jpg, 2.jpg…; первое = главное), "
            "затем импортируйте командой import_photos."
        )
