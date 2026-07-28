from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/tables/', include('apps.data_tables.urls')),
    path('api/dynamic/', include('apps.dynamic_tables.urls')),
]
