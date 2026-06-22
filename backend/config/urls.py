from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.users.views import RegisterView, MeView



urlpatterns = [
    path('admin/', admin.site.urls),

    # auth
    path('api/v1/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/register/', RegisterView.as_view(), name='register'),

    # catalog (read-only витрина)
    path('api/v1/catalog/', include('apps.catalog.urls')),

    # cart (гостевая + пользовательская корзина)
    path('api/v1/cart/', include('apps.cart.urls')),

    # docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

urlpatterns += [
    path('api/v1/me/', MeView.as_view(), name='me'),
]

# В режиме разработки Django сам раздаёт загруженные media-файлы.
# На проде это делает веб-сервер (nginx/whitenoise), поэтому только при DEBUG.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
