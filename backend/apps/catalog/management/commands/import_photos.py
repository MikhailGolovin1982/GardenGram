"""Импорт фотографий товаров из подготовленной папки-скелета (ШАГ D плана PLAN_PHOTOS.md).

Папку-скелет генерирует export_photo_skeleton; человек раскладывает в листовые папки фото.
Эта команда находит товар по «ID__» в имени листовой папки и создаёт ProductImage,
копируя файлы в media/products/… (с авто-ресайзом до 1600 px по умолчанию).

Идемпотентность (повторный запуск не плодит дубли):
- товар, у которого УЖЕ есть фото, по умолчанию ПРОПУСКАЕТСЯ;
- флаг --replace — сначала удалить старые фото товара, потом залить заново.

По умолчанию DRY-RUN: ничего не пишется ни в базу, ни в media/. Реальная запись — с --commit
(как в import_catalog).

Запуск (из папки backend/):
    python manage.py import_photos _scratch/photos_upload                  # пробный прогон
    python manage.py import_photos _scratch/photos_upload --commit         # реальная запись
    python manage.py import_photos _scratch/photos_upload --commit --replace
    python manage.py import_photos _scratch/photos_upload --commit --no-resize
"""

import io
import re
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageOps

from apps.catalog.models import Product, ProductImage

# Какие файлы считаем фотографиями. Регистр не важен.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
# Имя листовой папки товара: начинается с цифрового ID и «__».
LEAF_RE = re.compile(r"^(\d+)__")


def _natural_key(name):
    """Натуральная сортировка: «2.jpg» раньше «10.jpg», регистр не важен."""
    parts = re.split(r"(\d+)", name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


class Command(BaseCommand):
    help = "Импорт фото товаров из папки-скелета (привязка по ID в имени папки). По умолчанию dry-run."

    def add_arguments(self, parser):
        parser.add_argument("folder", help="Папка-скелет с фото (как из export_photo_skeleton).")
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Реально записать в базу и media/. Без флага — пробный прогон (dry-run).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Сначала удалить существующие фото товара, потом залить заново.",
        )
        parser.add_argument(
            "--no-resize",
            action="store_true",
            dest="no_resize",
            help="Не ужимать фото (по умолчанию ресайз до --max-size и пересохранение JPEG).",
        )
        parser.add_argument(
            "--max-size",
            type=int,
            default=1600,
            help="Макс. размер по длинной стороне в px при ресайзе (по умолчанию 1600).",
        )
        parser.add_argument(
            "--quality",
            type=int,
            default=85,
            help="Качество JPEG при ресайзе (по умолчанию 85).",
        )

    def handle(self, *args, **options):
        root = Path(options["folder"])
        if not root.is_dir():
            raise CommandError(f"Папка не найдена: {root}")

        commit = options["commit"]
        replace = options["replace"]

        # Собираем папки товаров: имя начинается с «ID__». Сортируем по ID для стабильного вывода.
        product_dirs = sorted(
            (d for d in root.rglob("*") if d.is_dir() and LEAF_RE.match(d.name)),
            key=lambda d: int(LEAF_RE.match(d.name).group(1)),
        )
        if not product_dirs:
            raise CommandError(
                f"В {root} не найдено ни одной папки вида «ID__Название». "
                f"Сгенерируйте скелет командой export_photo_skeleton."
            )

        stats = {
            "with_photos": 0,   # товаров, которым добавили фото
            "files": 0,         # сколько файлов залили
            "skipped_have": 0,  # пропущено: уже есть фото (без --replace)
            "skipped_empty": 0, # пропущено: в папке нет картинок
            "missing": 0,       # ID не найден в базе
            "replaced": 0,      # у скольких товаров удалили старые фото
        }

        # Файловые операции (запись в media/) НЕ транзакционны, поэтому в dry-run их вообще
        # не выполняем — только считаем и печатаем. В commit-режиме оборачиваем БД в atomic.
        ctx = transaction.atomic() if commit else _NullCtx()
        with ctx:
            for d in product_dirs:
                self._process_dir(d, options, commit, replace, stats)

        self._report(stats, commit)

    def _process_dir(self, d, options, commit, replace, stats):
        product_id = int(LEAF_RE.match(d.name).group(1))
        product = Product.objects.filter(pk=product_id).first()
        if product is None:
            stats["missing"] += 1
            self.stdout.write(self.style.WARNING(f"  [НЕТ ID]  {product_id} — папка {d.name}, пропуск"))
            return

        files = sorted(
            (f for f in d.iterdir()
             if f.is_file() and not f.name.startswith("_") and f.suffix.lower() in IMAGE_EXTS),
            key=lambda f: _natural_key(f.name),
        )
        if not files:
            stats["skipped_empty"] += 1
            return

        had = product.images.exists()
        if had and not replace:
            stats["skipped_have"] += 1
            self.stdout.write(f"  [есть]    {product_id} {product.display_name} — уже {product.images.count()} фото, пропуск")
            return

        if had and replace:
            stats["replaced"] += 1
            if commit:
                for img in product.images.all():
                    img.image.delete(save=False)  # удалить файл из media/
                    img.delete()

        for position, f in enumerate(files):
            if commit:
                name, data = self._prepare_file(f, product_id, position, options)
                pi = ProductImage(product=product, position=position, alt="")
                pi.image.save(name, ContentFile(data), save=True)
            stats["files"] += 1

        stats["with_photos"] += 1
        verb = "ЗАМЕНЮ" if (had and replace) else ("ЗАЛЬЮ" if commit else "ЗАЛИЛ БЫ")
        self.stdout.write(f"  [{verb:8}] {product_id} {product.display_name} — {len(files)} фото")

    def _prepare_file(self, path, product_id, position, options):
        """Готовит (имя, байты) для сохранения. С ресайзом → JPEG; без — исходный файл как есть."""
        if options["no_resize"]:
            return f"{product_id:04d}_{position + 1}{path.suffix.lower()}", path.read_bytes()

        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)  # учесть поворот с телефона
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            max_size = options["max_size"]
            if max(im.size) > max_size:
                im.thumbnail((max_size, max_size), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=options["quality"], optimize=True)
        return f"{product_id:04d}_{position + 1}.jpg", buf.getvalue()

    def _report(self, stats, commit):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Итого:"))
        self.stdout.write(f"  Товаров с фото:     {stats['with_photos']}")
        self.stdout.write(f"  Файлов:             {stats['files']}")
        if stats["replaced"]:
            self.stdout.write(f"  Заменено товаров:   {stats['replaced']}")
        self.stdout.write(f"  Пропущено (есть фото): {stats['skipped_have']}")
        self.stdout.write(f"  Пропущено (пусто):  {stats['skipped_empty']}")
        if stats["missing"]:
            self.stdout.write(self.style.WARNING(f"  ID не найдено:      {stats['missing']}"))

        mode = "РЕАЛЬНЫЙ ИМПОРТ (записано)" if commit else "DRY-RUN (ничего не записано)"
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(f"Режим: {mode}"))
        if not commit:
            self.stdout.write("Повторите с флагом --commit, чтобы залить фото.")


class _NullCtx:
    """Пустой контекст для dry-run (без транзакции — мы и так ничего не пишем)."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
