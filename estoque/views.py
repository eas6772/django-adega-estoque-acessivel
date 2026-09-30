"""
Views de estoque: visão geral, entrada, ajuste, alteração de validade e
histórico de movimentações. Ver docs/projeto_django_spec.md §3.1.
"""
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, UpdateView

from catalogo.models import Produto
from core.permissoes import AdminRequiredMixin
from core.views import SecaoAtivaMixin

from . import servicos
from .forms import AjusteForm, EntradaForm, FiltroMovimentacaoForm, ValidadeForm
from .models import Lote, Movimentacao


class VisaoGeralView(SecaoAtivaMixin, ListView):
    template_name = 'estoque/visao_geral.html'
    context_object_name = 'produtos'
    paginate_by = 20
    secao_ativa = 'estoque'

    def get_queryset(self):
        queryset = Produto.objects.ativos().com_estoque().select_related('categoria')
        status = self.request.GET.get('status')
        if status == 'baixo':
            # Sempre derivado de abaixo_do_minimo() — nunca reescrever a
            # condição de "estoque baixo" em outro lugar (bugs #13/#14).
            queryset = queryset.abaixo_do_minimo().exclude(estoque_total=0)
        elif status == 'zerado':
            queryset = queryset.filter(estoque_total=0)
        return queryset.order_by('nome')


class EntradaView(SecaoAtivaMixin, FormView):
    template_name = 'estoque/entrada_form.html'
    form_class = EntradaForm
    secao_ativa = 'estoque'
    success_url = reverse_lazy('estoque:visao_geral')

    def get_initial(self):
        initial = super().get_initial()
        produto_id = self.request.GET.get('produto_id')
        if produto_id:
            initial['produto'] = produto_id
        return initial

    def form_valid(self, form):
        lote = servicos.registrar_entrada(usuario=self.request.user, **form.cleaned_data)
        messages.success(self.request, f'Entrada registrada: lote #{lote.pk} de "{lote.produto}".')
        return super().form_valid(form)


class AjusteView(AdminRequiredMixin, SecaoAtivaMixin, FormView):
    template_name = 'estoque/ajuste_form.html'
    form_class = AjusteForm
    secao_ativa = 'estoque'
    success_url = reverse_lazy('estoque:visao_geral')

    def form_valid(self, form):
        try:
            lote = servicos.ajustar_lote(
                usuario=self.request.user,
                lote_id=form.cleaned_data['lote'].pk,
                nova_quantidade=form.cleaned_data['nova_quantidade'],
                motivo=form.cleaned_data['motivo'],
            )
        except Lote.DoesNotExist:
            form.add_error('lote', 'Lote não encontrado.')
            return self.form_invalid(form)
        messages.success(self.request, f'Lote #{lote.pk} ajustado para {lote.quantidade} unidade(s).')
        return super().form_valid(form)


class ValidadeView(AdminRequiredMixin, SecaoAtivaMixin, UpdateView):
    model = Lote
    form_class = ValidadeForm
    template_name = 'estoque/validade_form.html'
    secao_ativa = 'estoque'
    success_url = reverse_lazy('estoque:visao_geral')

    def form_valid(self, form):
        # Não chamamos form.save(): o efeito precisa passar por servicos.py
        # para que a Movimentacao de auditoria seja sempre criada junto.
        servicos.alterar_validade(
            usuario=self.request.user,
            lote_id=self.object.pk,
            nova_data_validade=form.cleaned_data['data_validade'],
            motivo=form.cleaned_data['motivo'],
        )
        messages.success(self.request, f'Validade do lote #{self.object.pk} atualizada.')
        return super().form_valid(form)


class MovimentacaoListView(SecaoAtivaMixin, ListView):
    model = Movimentacao
    template_name = 'estoque/movimentacao_lista.html'
    context_object_name = 'movimentacoes'
    paginate_by = 20
    secao_ativa = 'estoque'

    def get_queryset(self):
        self.filtro = FiltroMovimentacaoForm(self.request.GET or None)
        queryset = Movimentacao.objects.select_related('produto', 'lote', 'usuario')
        if self.filtro.is_valid():
            tipo = self.filtro.cleaned_data.get('tipo')
            if tipo:
                queryset = queryset.filter(tipo=tipo)
            data_inicio = self.filtro.cleaned_data.get('data_inicio')
            if data_inicio:
                queryset = queryset.filter(data__date__gte=data_inicio)
            data_fim = self.filtro.cleaned_data.get('data_fim')
            if data_fim:
                queryset = queryset.filter(data__date__lte=data_fim)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro'] = self.filtro
        return context
