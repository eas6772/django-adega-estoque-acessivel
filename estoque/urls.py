from django.urls import path

from . import api, views

app_name = 'estoque'

urlpatterns = [
    path('', views.VisaoGeralView.as_view(), name='visao_geral'),
    path('entrada/', views.EntradaView.as_view(), name='entrada'),
    path('ajuste/', views.AjusteView.as_view(), name='ajuste'),
    path('lotes/<int:pk>/validade/', views.ValidadeView.as_view(), name='lote_validade'),
    path('movimentacoes/', views.MovimentacaoListView.as_view(), name='movimentacao_lista'),
    path('api/produtos/<int:pk>/lotes/', api.lotes_produto, name='api_lotes_produto'),
]
