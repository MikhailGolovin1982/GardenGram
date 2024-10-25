from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe


# Модель для категорий товаров
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# Модель для товаров
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    currency = models.CharField(max_length=10, default='руб.')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def thumbnail(self):
        first_image = self.images.first()  # Берем первое изображение, если оно есть
        if first_image and first_image.image:
            return mark_safe(f'<img src="{first_image.image.url}" width="50" height="50" />')
        return "Нет изображения"

    thumbnail.allow_tags = True
    thumbnail.short_description = 'Thumbnail'


# Модель для учета наличия товаров
class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} - {self.quantity} шт."


# Сигнал для обновления доступности товара при изменении Stock
@receiver(post_save, sender=Stock)
def update_product_availability(sender, instance, **kwargs):
    product = instance.product
    if instance.quantity > 0:
        product.is_available = True
    else:
        product.is_available = False
    product.save()


# Сигнал для автоматического создания объекта Stock при создании Product
@receiver(post_save, sender=Product)
def create_stock_for_product(sender, instance, created, **kwargs):
    if created:
        Stock.objects.create(product=instance, quantity=0)


# Модель для хранения фотографий товаров
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f"Image for {self.product.name}"

    def image_tag(self):
        if self.image:
            return mark_safe(f'<img src="{self.image.url}" width="100" height="100" />')
        return "Нет изображения"

    image_tag.allow_tags = True
    image_tag.short_description = 'Image'
    