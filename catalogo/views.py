"""
Views de catalogo: categorias e produtos. Ver docs/projeto_django_spec.md
§3.1 e §3.3 (categorias não usam Fetch: form comum, POST-only, sem página
própria — o form vive num <dialog> na própria lista, Etapa 3).
"""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from core.permissoes import AdminRequiredMixin
from core.views import SecaoAtivaMixin

from .forms import CategoriaForm, FiltroProdutoForm, ProdutoForm
from .models import Categoria, Produto


class CategoriaListView(SecaoAtivaMixin, ListView):
    model = Categoria
    template_name = 'catalogo/categoria_lista.html'
    context_object_name = 'categorias'
    secao_ativa = 'catalogo'

    def get_queryset(self):
        return Categoria.objects.annotate(
            num_produtos=Count('produtos', filter=Q(produtos__ativo=True))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Form vazio para o <dialog> de "nova categoria" (Etapa 3); em caso de
        # erro, CategoriaFormMixin.form_invalid sobrescreve com o form inválido.
        context.setdefault('form_categoria', CategoriaForm())
        return context


class CategoriaFormMixin(SecaoAtivaMixin):
    """
    Categoria não tem página própria: o formulário vive num <dialog> dentro
    de categoria_lista.html (Etapa 3). Em erro, precisamos re-renderizar a
    MESMA lista (nunca redirecionar) para não perder form.errors — por isso
    o form_invalid customizado, em vez do redirect padrão de FormMixin.
    """

    model = Categoria
    form_class = CategoriaForm
    template_name = 'catalogo/categoria_lista.html'
    secao_ativa = 'catalogo'
    http_method_names = ['post']

    def get_success_url(self):
        return reverse('catalogo:categoria_lista')

    def form_invalid(self, form):
        context = {
            'categorias': Categoria.objects.annotate(
                num_produtos=Count('produtos', filter=Q(produtos__ativo=True))
            ),
            'form_categoria': form,
            'secao_ativa': self.secao_ativa,
        }
        return self.render_to_response(context)


class CategoriaCreateView(AdminRequiredMixin, CategoriaFormMixin, CreateView):
    pass


class CategoriaUpdateView(AdminRequiredMixin, CategoriaFormMixin, UpdateView):
    pass


class CategoriaAlternarView(AdminRequiredMixin, View):
    def post(self, request, pk):
        categoria = get_object_or_404(Categoria, pk=pk)
        categoria.ativo = not categoria.ativo
        categoria.save(update_fields=['ativo'])
        messages.info(request, f'Categoria "{categoria.nome}" {"ativada" if categoria.ativo else "desativada"}.')
        return redirect('catalogo:categoria_lista')


class ProdutoListView(SecaoAtivaMixin, ListView):
    model = Produto
    template_name = 'catalogo/produto_lista.html'
    context_object_name = 'produtos'
    paginate_by = 15
    secao_ativa = 'catalogo'

    def get_queryset(self):
        self.filtro = FiltroProdutoForm(self.request.GET or None)
        queryset = Produto.objects.com_estoque().select_related('categoria')
        if not (self.filtro.is_valid() and self.filtro.cleaned_data.get('mostrar_inativos')):
            queryset = queryset.filter(ativo=True)
        if self.filtro.is_valid():
            q = self.filtro.cleaned_data.get('q')
            if q:
                queryset = queryset.buscar(q)
            categoria = self.filtro.cleaned_data.get('categoria')
            if categoria:
                queryset = queryset.filter(categoria=categoria)
        return queryset.order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro'] = self.filtro
        return context


class ProdutoCreateView(AdminRequiredMixin, SecaoAtivaMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'catalogo/produto_form.html'
    secao_ativa = 'catalogo'

    def get_success_url(self):
        messages.success(self.request, f'Produto "{self.object.nome}" criado com sucesso.')
        return reverse('catalogo:produto_lista')


class ProdutoUpdateView(AdminRequiredMixin, SecaoAtivaMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'catalogo/produto_form.html'
    secao_ativa = 'catalogo'

    def get_success_url(self):
        messages.success(self.request, f'Produto "{self.object.nome}" atualizado com sucesso.')
        return reverse('catalogo:produto_lista')


class ProdutoAlternarView(AdminRequiredMixin, View):
    def post(self, request, pk):
        produto = get_object_or_404(Produto, pk=pk)
        produto.ativo = not produto.ativo
        produto.save(update_fields=['ativo'])
        messages.info(request, f'Produto "{produto.nome}" {"ativado" if produto.ativo else "desativado"}.')
        return redirect('catalogo:produto_lista')
