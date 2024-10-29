from rest_framework import serializers
from .models import Category, Product, Stock, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'subcategories']

    def get_subcategories(self, obj):
        children = obj.subcategories.all()
        return CategorySerializer(children, many=True, context=self.context).data


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
    product = serializers.StringRelatedField(read_only=True)  # Только для чтения, так как связь с продуктом не должна меняться
    quantity = serializers.IntegerField()  # Доступно для изменения

    class Meta:
        model = Stock
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()  # Поле для загрузки файла изображения

    class Meta:
        model = ProductImage
        fields = '__all__'
        
