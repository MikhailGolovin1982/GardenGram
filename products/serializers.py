from rest_framework import serializers
from .models import Category, Product, Stock, ProductImage

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    images = serializers.PrimaryKeyRelatedField(many=True, queryset=ProductImage.objects.all(), required=False)
    quantity = serializers.IntegerField(write_only=True, required=False, default=0)
    
    class Meta:
        model = Product
        fields = '__all__'

        extra_kwargs = {
            'name': {'required': True},
            'description': {'required': False},
            'price': {'required': False},
            'currency': {'required': False},
            'category': {'required': False},
            'is_available': {'required': False},
        }
    
    def create(self, validated_data):
        quantity = validated_data.pop('quantity', 0)
        product = super().create(validated_data)
    
        # Создание объекта Stock только один раз
        if not Stock.objects.filter(product=product).exists():
            Stock.objects.create(product=product, quantity=quantity)

        return product

class StockSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField()

    class Meta:
        model = Stock
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'
        