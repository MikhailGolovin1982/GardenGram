from django.contrib import admin
from .models import Category, Product, Stock, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Количество пустых полей для загрузки новых изображений

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'currency', 'is_available', 'thumbnail')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'description')
    inlines = [ProductImageInline]  # Добавляем Inline для изображений

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'parent')
    search_fields = ('name',)

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity')

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'image_tag')
