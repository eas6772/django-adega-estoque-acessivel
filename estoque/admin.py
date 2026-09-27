from django.contrib import admin

from .models import Lote, Movimentacao


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'produto', 'numero_lote', 'quantidade', 'data_validade', 'esta_vencido', 'vence_em_breve')
    list_filter = ('produto__categoria',)
    search_fields = ('numero_lote', 'produto__nome')
    list_select_related = ('produto',)

    @admin.display(description='Vencido?', boolean=True)
    def esta_vencido(self, obj):
        return obj.vencido

    @admin.display(description='Vence em breve?', boolean=True)
    def vence_em_breve(self, obj):
        return obj.proximo_vencimento


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    """Log de auditoria: nunca editável pelo admin."""

    list_display = ('id', 'tipo', 'produto', 'lote', 'quantidade', 'data', 'usuario')
    list_filter = ('tipo',)
    search_fields = ('produto__nome', 'motivo')
    list_select_related = ('produto', 'lote', 'usuario')
    readonly_fields = [f.name for f in Movimentacao._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
