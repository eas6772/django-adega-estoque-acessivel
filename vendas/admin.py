from django.contrib import admin

from .models import ItemVenda, Venda


class ItemVendaInline(admin.TabularInline):
    """Histórico imutável: nenhum campo é editável pelo admin."""

    model = ItemVenda
    extra = 0
    readonly_fields = [f.name for f in ItemVenda._meta.fields if f.name != 'id']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'data', 'usuario', 'total')
    list_filter = ('usuario',)
    date_hierarchy = 'data'
    list_select_related = ('usuario',)
    readonly_fields = ('data', 'usuario', 'total')
    inlines = [ItemVendaInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
