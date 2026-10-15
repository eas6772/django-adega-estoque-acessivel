"""
Querysets anotados reutilizados pelas páginas HTML e pelo PDF de reposição.
Sempre reaproveita ProdutoQuerySet.abaixo_do_minimo()/com_estoque() (nunca
redefine "estoque baixo" aqui) e ItemVenda.custo_unitario congelado (nunca
Produto.preco_custo atual — bug #8 do Flask). Ver docs/projeto_django_spec.md
§3.1.
"""
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from catalogo.models import Produto
from estoque.models import Lote
from vendas.models import ItemVenda, Venda


def produtos_com_valor_estoque():
    """Base do relatório de estoque: produtos ativos com estoque e valor agregado."""
    return (
        Produto.objects.ativos().com_estoque().select_related('categoria')
        .annotate(valor_estoque=F('estoque_total') * F('preco_custo'))
    )


def valor_total_estoque(queryset=None):
    queryset = queryset if queryset is not None else produtos_com_valor_estoque()
    total = queryset.aggregate(
        total=Coalesce(Sum(F('estoque_total') * F('preco_custo')), Decimal('0.00'))
    )
    return total['total']


def com_qtd_compra(queryset):
    """Anota a quantidade sugerida de compra (máximo − estoque, nunca negativa).

    Espera um queryset já anotado com `estoque_total` (ProdutoQuerySet.com_estoque()).
    """
    return queryset.annotate(qtd_compra=Greatest(F('estoque_maximo') - F('estoque_total'), 0))


def produtos_para_reposicao():
    """Reaproveita abaixo_do_minimo() — não redefine a regra de "estoque baixo"."""
    return com_qtd_compra(
        Produto.objects.ativos().abaixo_do_minimo().select_related('categoria')
    ).order_by('nome')


def _filtrar_periodo(queryset, data_inicio, data_fim):
    if data_inicio:
        queryset = queryset.filter(venda__data__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(venda__data__date__lte=data_fim)
    return queryset


def mais_vendidos(data_inicio=None, data_fim=None):
    queryset = _filtrar_periodo(ItemVenda.objects.all(), data_inicio, data_fim)
    return (
        queryset.values('produto__id', 'produto__nome', 'produto__fabricante')
        .annotate(qtd=Sum('quantidade'), receita=Sum('subtotal'))
        .order_by('-qtd')
    )


def lucro_por_produto(data_inicio=None, data_fim=None):
    """custo_unitario congelado no momento da venda, nunca Produto.preco_custo atual."""
    queryset = _filtrar_periodo(ItemVenda.objects.all(), data_inicio, data_fim)
    return (
        queryset.values('produto__id', 'produto__nome')
        .annotate(
            receita=Sum('subtotal'),
            custo=Sum(F('quantidade') * F('custo_unitario')),
        )
        .annotate(lucro=F('receita') - F('custo'))
        .order_by('-lucro')
    )


# ---------- Indicadores da página inicial (core:painel) ----------

def produtos_ativos():
    return Produto.objects.ativos()


def produtos_estoque_baixo():
    """Mesma regra de produtos_para_reposicao(): abaixo_do_minimo() inclui os zerados."""
    return (
        Produto.objects.ativos().abaixo_do_minimo().select_related('categoria')
        .order_by('estoque_total', 'nome')
    )


def lotes_vencendo(dias=30):
    """Lotes com saldo que vencem em até `dias` dias (hoje inclusive), do mais próximo ao mais distante."""
    return (
        Lote.objects.vencendo_em(dias).filter(produto__ativo=True)
        .select_related('produto').order_by('data_validade', 'id')
    )


def vendas_do_dia(dia=None):
    """Total e quantidade de vendas do dia local (nunca date.today())."""
    dia = dia or timezone.localdate()
    resumo = Venda.objects.filter(data__date=dia).aggregate(
        total=Coalesce(Sum('total'), Decimal('0.00')), quantidade=Count('id'),
    )
    return resumo
