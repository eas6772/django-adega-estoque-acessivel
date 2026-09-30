"""
Views de relatorios: 5 páginas + PDF, todas somente leitura sobre os outros
apps. Ver docs/projeto_django_spec.md §3.1.
"""
from django.http import FileResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import ListView

from core.permissoes import AdminRequiredMixin
from core.views import SecaoAtivaMixin
from estoque import views as estoque_views

from . import consultas, pdf


class PeriodoMixin:
    def periodo(self):
        data_inicio = parse_date(self.request.GET.get('data_inicio', '') or '')
        data_fim = parse_date(self.request.GET.get('data_fim', '') or '')
        return data_inicio, data_fim

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['data_inicio'], context['data_fim'] = self.periodo()
        return context


class EstoqueRelView(SecaoAtivaMixin, ListView):
    template_name = 'relatorios/estoque.html'
    context_object_name = 'produtos'
    secao_ativa = 'relatorios'

    def get_queryset(self):
        return consultas.produtos_com_valor_estoque()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['valor_total'] = consultas.valor_total_estoque(self.get_queryset())
        return context


class ReposicaoRelView(SecaoAtivaMixin, ListView):
    template_name = 'relatorios/reposicao.html'
    context_object_name = 'produtos'
    secao_ativa = 'relatorios'

    def get_queryset(self):
        return consultas.produtos_para_reposicao()


def reposicao_pdf(request):
    nome_arquivo = f'reposicao-{timezone.localdate():%Y%m%d}.pdf'
    return FileResponse(pdf.gerar_pdf_reposicao(), as_attachment=True, filename=nome_arquivo)


class MaisVendidosRelView(AdminRequiredMixin, PeriodoMixin, SecaoAtivaMixin, ListView):
    template_name = 'relatorios/mais_vendidos.html'
    context_object_name = 'itens'
    paginate_by = 30
    secao_ativa = 'relatorios'

    def get_queryset(self):
        return consultas.mais_vendidos(*self.periodo())


class LucroRelView(AdminRequiredMixin, PeriodoMixin, SecaoAtivaMixin, ListView):
    template_name = 'relatorios/lucro.html'
    context_object_name = 'itens'
    secao_ativa = 'relatorios'

    def get_queryset(self):
        return consultas.lucro_por_produto(*self.periodo())


class MovimentacoesRelView(AdminRequiredMixin, estoque_views.MovimentacaoListView):
    """Reaproveita a listagem de estoque por herança — sem consulta própria."""

    template_name = 'relatorios/movimentacoes.html'
    paginate_by = 30
    secao_ativa = 'relatorios'
