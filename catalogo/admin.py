from django.contrib import admin

from .models import Categoria, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome',)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'preco_custo', 'preco_venda', 'estoque_minimo', 'estoque_maximo', 'ativo')
    list_filter = ('ativo', 'categoria')
    search_fields = ('nome', 'fabricante', 'codigo_barras')
    list_select_related = ('categoria',)
    readonly_fields = ('preco_venda',)
