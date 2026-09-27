"""
Views de vendas: frente de caixa, lista de vendas e recibo. Ver
docs/projeto_django_spec.md §3.1.
"""
from django.db.models import Count, Sum
from django.views.generic import DetailView, ListView, TemplateView

from core.views import SecaoAtivaMixin

from .models import Venda


class PdvView(SecaoAtivaMixin, TemplateView):
    template_name = 'vendas/pdv.html'
    secao_ativa = 'vendas'


class VendaListView(SecaoAtivaMixin, ListView):
    model = Venda
    template_name = 'vendas/venda_lista.html'
    context_object_name = 'vendas'
    paginate_by = 20
    secao_ativa = 'vendas'

    def get_queryset(self):
        return Venda.objects.select_related('usuario').annotate(num_itens=Count('itens'))


class ReciboView(SecaoAtivaMixin, DetailView):
    model = Venda
    context_object_name = 'venda'
    secao_ativa = 'vendas'

    def get_queryset(self):
        return Venda.objects.select_related('usuario')

    def get_template_names(self):
        if self.request.GET.get('parcial') == '1':
            return ['vendas/_recibo.html']
        return ['vendas/recibo.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # O agrupamento por produto que no Flask era feito no Jinja migra
        # para a view: o DTL não deve fazer esse tipo de lógica.
        context['itens_agrupados'] = (
            self.object.itens.values('produto__id', 'produto__nome')
            .annotate(quantidade=Sum('quantidade'), subtotal=Sum('subtotal'))
            .order_by('produto__nome')
        )
        return context
