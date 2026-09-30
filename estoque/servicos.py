"""
Regras de negócio de estoque: entrada, ajuste de quantidade e alteração de
validade de um lote. Tudo em transaction.atomic(); ajustar_lote e
alterar_validade usam select_for_update() para não perder uma baixa
concorrente feita por vendas.servicos.registrar_venda() no mesmo lote.
"""
from django.db import transaction

from .models import Lote, Movimentacao


@transaction.atomic
def registrar_entrada(*, usuario, produto, quantidade, numero_lote='', data_validade=None, motivo=''):
    """Cria um novo lote (entrada de mercadoria) e a movimentação correspondente."""
    lote = Lote.objects.create(
        produto=produto,
        numero_lote=numero_lote,
        quantidade=quantidade,
        data_validade=data_validade,
    )
    Movimentacao.objects.create(
        produto=produto,
        lote=lote,
        tipo=Movimentacao.Tipo.ENTRADA,
        quantidade=quantidade,
        usuario=usuario,
        motivo=motivo,
    )
    return lote


@transaction.atomic
def ajustar_lote(*, usuario, lote_id, nova_quantidade, motivo=''):
    """
    Corrige o saldo de um lote (contagem física, avaria, perda etc.).

    Grava a DIFERENÇA (pode ser negativa) na Movimentacao, nunca a quantidade
    final — é a diferença que soma corretamente no histórico e nos relatórios.
    select_for_update() garante que este ajuste não sobrescreva uma baixa de
    venda ocorrida entre a renderização do formulário e o POST.
    """
    lote = Lote.objects.select_for_update().select_related('produto').get(pk=lote_id)
    diferenca = nova_quantidade - lote.quantidade
    lote.quantidade = nova_quantidade
    lote.save(update_fields=['quantidade'])
    Movimentacao.objects.create(
        produto=lote.produto,
        lote=lote,
        tipo=Movimentacao.Tipo.AJUSTE,
        quantidade=diferenca,
        usuario=usuario,
        motivo=motivo,
    )
    return lote


@transaction.atomic
def alterar_validade(*, usuario, lote_id, nova_data_validade, motivo=''):
    """
    Corrige a data de validade de um lote (erro de cadastro na entrada).

    Não altera o saldo: a Movimentacao é gravada com quantidade=0, só para
    manter a trilha de auditoria (quem alterou, quando e por quê).
    """
    lote = Lote.objects.select_for_update().select_related('produto').get(pk=lote_id)
    lote.data_validade = nova_data_validade
    lote.save(update_fields=['data_validade'])
    Movimentacao.objects.create(
        produto=lote.produto,
        lote=lote,
        tipo=Movimentacao.Tipo.AJUSTE,
        quantidade=0,
        usuario=usuario,
        motivo=motivo,
    )
    return lote
