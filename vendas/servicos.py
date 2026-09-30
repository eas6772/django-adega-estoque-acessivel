"""
Serviço transacional de venda (frente de caixa). Ver
docs/planejamento_views.md §3.4 (código testado) e
docs/projeto_django_spec.md §3.2 (contrato de erro).
"""
from collections import Counter

from django.db import transaction
from django.db.models import F

from estoque.models import Lote, Movimentacao

from .models import ItemVenda, Venda


class ConflitoEstoque(Exception):
    def __init__(self, mensagem, lote_id, disponivel=0):
        super().__init__(mensagem)
        self.lote_id, self.disponivel = lote_id, disponivel


@transaction.atomic
def registrar_venda(usuario, itens):
    # Soma itens repetidos do mesmo lote ANTES de validar (com F() o saldo em
    # memória não diminui a cada item, como acontecia na sessão SQLAlchemy).
    pedido = Counter()
    for item in itens:
        pedido[int(item['lote_id'])] += int(item['quantidade'])

    # Trava as linhas dos lotes até o commit: dois caixas não vendem a mesma
    # unidade. order_by('id') evita deadlock entre transações concorrentes.
    lotes = {
        l.id: l for l in
        Lote.objects.select_for_update().select_related('produto')
        .filter(id__in=pedido).order_by('id')
    }

    venda = Venda.objects.create(usuario=usuario)
    for lote_id, qtd in pedido.items():
        lote = lotes.get(lote_id)
        if lote is None or not lote.produto.ativo:
            raise ConflitoEstoque('Lote ou produto indisponível.', lote_id)
        if lote.vencido:
            raise ConflitoEstoque(f'Lote #{lote_id} de "{lote.produto}" está vencido.', lote_id)
        if qtd > lote.quantidade:
            raise ConflitoEstoque(
                f'Estoque insuficiente no lote #{lote_id} de "{lote.produto}" '
                f'(disponível: {lote.quantidade}).', lote_id, lote.quantidade)

        Lote.objects.filter(pk=lote_id).update(quantidade=F('quantidade') - qtd)
        ItemVenda.objects.create(
            venda=venda, produto=lote.produto, lote=lote, quantidade=qtd,
            preco_unitario=lote.produto.preco_venda,
            custo_unitario=lote.produto.preco_custo,
        )
        Movimentacao.objects.create(
            produto=lote.produto, lote=lote, venda=venda, tipo=Movimentacao.Tipo.SAIDA,
            quantidade=qtd, usuario=usuario, motivo=f'Venda #{venda.pk}',
        )

    venda.recalcular_total()
    venda.save(update_fields=['total'])
    return venda
