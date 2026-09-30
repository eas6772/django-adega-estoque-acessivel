"""
API JSON da frente de caixa: busca de produto e criação de venda. Ver
docs/projeto_django_spec.md §3.2 (contrato completo de request/response).
"""
import json

from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from catalogo.models import Produto
from core.permissoes import login_required_json

from .servicos import ConflitoEstoque, registrar_venda


@login_not_required
@login_required_json
@require_GET
def buscar_produto(request):
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)

    produtos = Produto.objects.ativos().com_estoque().buscar(q).order_by('nome')[:10]
    dados = [
        {
            'id': produto.id,
            'nome': produto.nome,
            'fabricante': produto.fabricante,
            'codigo_barras': produto.codigo_barras,
            'preco_venda': str(produto.preco_venda),
            'estoque': produto.estoque_total,
            'match_exato': produto.codigo_barras is not None and produto.codigo_barras == q,
        }
        for produto in produtos
    ]
    return JsonResponse(dados, safe=False)


@login_not_required
@login_required_json
@require_POST
def criar_venda(request):
    try:
        corpo = json.loads(request.body)
        itens = corpo.get('itens') or []
        if not itens or any(int(item['quantidade']) <= 0 for item in itens):
            raise ValueError('Carrinho inválido.')
    except (ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError):
        return JsonResponse({'erro': 'Dados do carrinho inválidos.'}, status=400)

    try:
        venda = registrar_venda(request.user, itens)
    except ConflitoEstoque as erro:
        indice = next(
            (n for n, item in enumerate(itens) if int(item['lote_id']) == erro.lote_id), None
        )
        return JsonResponse(
            {'erro': str(erro), 'lote_id': erro.lote_id, 'item_index': indice, 'disponivel': erro.disponivel},
            status=409,
        )

    return JsonResponse(
        {'id': venda.pk, 'total': str(venda.total), 'recibo_url': reverse('vendas:recibo', args=[venda.pk])},
        status=201,
    )
