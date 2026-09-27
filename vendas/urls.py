from django.urls import path

from . import api, views

app_name = 'vendas'

urlpatterns = [
    path('pdv/', views.PdvView.as_view(), name='pdv'),
    path('', views.VendaListView.as_view(), name='venda_lista'),
    path('<int:pk>/recibo/', views.ReciboView.as_view(), name='recibo'),
    path('api/produtos/', api.buscar_produto, name='api_busca_produto'),
    path('api/vendas/', api.criar_venda, name='api_venda_criar'),
]
