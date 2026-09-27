"""
Formulários de estoque: entrada, ajuste, alteração de validade e filtro do
histórico de movimentações. Ver docs/projeto_django_spec.md §3.1.
"""
from django import forms

from catalogo.models import Produto
from core.forms import AcessivelMixin

from .models import Lote, Movimentacao


class EntradaForm(AcessivelMixin, forms.Form):
    produto = forms.ModelChoiceField(queryset=Produto.objects.ativos())
    quantidade = forms.IntegerField(min_value=1)
    numero_lote = forms.CharField(label='Número do lote', required=False)
    data_validade = forms.DateField(required=False)
    motivo = forms.CharField(required=False, widget=forms.Textarea)


class AjusteForm(AcessivelMixin, forms.Form):
    produto = forms.ModelChoiceField(queryset=Produto.objects.ativos())
    lote = forms.ModelChoiceField(queryset=Lote.objects.all())
    nova_quantidade = forms.IntegerField(min_value=0)
    motivo = forms.CharField(widget=forms.Textarea, help_text='Justifique o ajuste.')

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        lote = cleaned_data.get('lote')
        if produto and lote and lote.produto_id != produto.id:
            self.add_error('lote', 'O lote selecionado não pertence ao produto escolhido.')
        return cleaned_data


class ValidadeForm(AcessivelMixin, forms.ModelForm):
    motivo = forms.CharField(
        label='Motivo da alteração', widget=forms.Textarea,
        help_text='Explique por que a validade está sendo corrigida.',
    )

    class Meta:
        model = Lote
        fields = ['data_validade']


class FiltroMovimentacaoForm(forms.Form):
    data_inicio = forms.DateField(required=False)
    data_fim = forms.DateField(required=False)
    tipo = forms.ChoiceField(
        choices=[('', 'Todos')] + list(Movimentacao.Tipo.choices), required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        if data_inicio and data_fim and data_inicio > data_fim:
            self.add_error('data_fim', 'A data final não pode ser anterior à inicial.')
        return cleaned_data
