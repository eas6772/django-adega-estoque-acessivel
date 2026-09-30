"""
Formulários de catalogo: categorias e produtos. Ver
docs/projeto_django_spec.md §3.1 e §1.4.
"""
from django import forms

from core.forms import AcessivelMixin

from .models import Categoria, Produto


class CategoriaForm(AcessivelMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'ativo']

    def clean_nome(self):
        nome = self.cleaned_data['nome']
        if Categoria.objects.filter(nome__iexact=nome).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Já existe uma categoria com este nome.')
        return nome


class ProdutoForm(AcessivelMixin, forms.ModelForm):
    class Meta:
        model = Produto
        # preco_venda NUNCA aparece aqui: é calculado em Produto.save() a
        # partir de preco_custo/margem_lucro (editable=False no modelo).
        fields = [
            'nome', 'categoria', 'fabricante', 'volume', 'peso', 'codigo_barras',
            'margem_lucro', 'preco_custo', 'estoque_minimo', 'estoque_maximo', 'ativo',
        ]

    codigo_barras = forms.CharField(label='Código de barras', required=False)

    def clean_codigo_barras(self):
        codigo = self.cleaned_data['codigo_barras'].strip()
        return codigo or None

    def clean(self):
        cleaned_data = super().clean()
        minimo = cleaned_data.get('estoque_minimo')
        maximo = cleaned_data.get('estoque_maximo')
        if minimo is not None and maximo is not None and maximo < minimo:
            self.add_error('estoque_maximo', 'O estoque máximo não pode ser menor que o mínimo.')
        return cleaned_data


class FiltroProdutoForm(forms.Form):
    q = forms.CharField(label='Buscar', required=False)
    categoria = forms.ModelChoiceField(
        label='Categoria', queryset=Categoria.objects.all(), required=False,
    )
    mostrar_inativos = forms.BooleanField(label='Mostrar inativos', required=False)
