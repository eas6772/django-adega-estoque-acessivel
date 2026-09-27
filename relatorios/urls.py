from django.urls import path

from . import views

app_name = 'relatorios'

urlpatterns = [
    path('estoque/', views.EstoqueRelView.as_view(), name='estoque'),
    path('reposicao/', views.ReposicaoRelView.as_view(), name='reposicao'),
    path('reposicao/pdf/', views.reposicao_pdf, name='reposicao_pdf'),
    path('mais-vendidos/', views.MaisVendidosRelView.as_view(), name='mais_vendidos'),
    path('lucro/', views.LucroRelView.as_view(), name='lucro'),
    path('movimentacoes/', views.MovimentacoesRelView.as_view(), name='movimentacoes'),
]
