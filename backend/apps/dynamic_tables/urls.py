from django.urls import path

from . import views

urlpatterns = [
    path('', views.DynamicTableView.as_view(), name='dynamic-table-list'),
    path('<str:key>/', views.DynamicTableDetailView.as_view(), name='dynamic-table-detail'),
]
