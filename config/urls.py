"""
URLs raiz do Empório BR.

As rotas de cada app (core, catalogo, estoque, vendas, relatorios), cada uma com
seu próprio namespace, entram aqui via include() na Etapa 2 (ver docs/projeto_django_spec.md §3).
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]
