from django.urls import path

from . import views

urlpatterns = [
    path('', views.DynamicTableView.as_view(), name='dynamic-table-list'),
    path('<str:key>/', views.DynamicTableDetailView.as_view(), name='dynamic-table-detail'),
    path('<str:key>/export/', views.dynamic_table_export, name='dynamic-table-export'),
    path('<str:key>/import/', views.dynamic_table_import, name='dynamic-table-import'),
    path('<str:key>/template/', views.dynamic_table_template, name='dynamic-table-template'),
]
