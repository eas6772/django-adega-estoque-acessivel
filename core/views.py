"""
Views de core: painel (dashboard) e gestão de usuários. Ver
docs/projeto_django_spec.md §3.1.
"""
from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from catalogo.models import Produto
from estoque.models import Lote
from vendas.models import Venda

from .forms import UsuarioCriarForm, UsuarioEditarForm
from .models import Usuario
from .permissoes import AdminRequiredMixin


class SecaoAtivaMixin:
    """Cada view define explicitamente a seção ativa do menu (ver D2 do plano
    da Etapa 2) — não é inferida a partir da URL no template."""

    secao_ativa = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secao_ativa'] = self.secao_ativa
        return context


class PainelView(SecaoAtivaMixin, TemplateView):
    template_name = 'core/painel.html'
    secao_ativa = 'painel'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        vendas_hoje = Venda.objects.filter(data__date=hoje)
        context['produtos_abaixo_do_minimo'] = (
            Produto.objects.ativos().abaixo_do_minimo().select_related('categoria')
        )
        context['lotes_vencendo'] = Lote.objects.vencendo_em(30).select_related('produto')
        context['qtd_vendas_hoje'] = vendas_hoje.count()
        context['total_vendas_hoje'] = vendas_hoje.aggregate(
            total=Coalesce(Sum('total'), Decimal('0.00'))
        )['total']
        return context


class UsuarioListView(AdminRequiredMixin, SecaoAtivaMixin, ListView):
    model = Usuario
    template_name = 'core/usuario_lista.html'
    context_object_name = 'usuarios'
    secao_ativa = 'usuarios'


class UsuarioCreateView(AdminRequiredMixin, SecaoAtivaMixin, CreateView):
    model = Usuario
    form_class = UsuarioCriarForm
    template_name = 'core/usuario_form.html'
    secao_ativa = 'usuarios'
    success_url = reverse_lazy('core:usuario_lista')

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, f'Usuário "{self.object.nome}" criado com sucesso.')
        return resposta


class UsuarioUpdateView(AdminRequiredMixin, SecaoAtivaMixin, UpdateView):
    model = Usuario
    form_class = UsuarioEditarForm
    template_name = 'core/usuario_form.html'
    secao_ativa = 'usuarios'
    success_url = reverse_lazy('core:usuario_lista')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario_logado'] = self.request.user
        return kwargs

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, f'Usuário "{self.object.nome}" atualizado com sucesso.')
        return resposta


class UsuarioAlternarView(AdminRequiredMixin, View):
    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        if usuario.pk == request.user.pk:
            messages.error(request, 'Você não pode desativar sua própria conta.')
            return redirect('core:usuario_lista')
        usuario.ativo = not usuario.ativo
        usuario.save(update_fields=['ativo'])
        if usuario.ativo:
            messages.success(request, f'Usuário "{usuario.nome}" ativado.')
        else:
            messages.info(request, f'Usuário "{usuario.nome}" desativado.')
        return redirect('core:usuario_lista')
