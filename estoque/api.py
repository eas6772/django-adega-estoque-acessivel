"""
API JSON de estoque: lotes vendáveis de um produto (usado pelo diálogo de
lote do PDV e pela tela de ajuste). Ver docs/projeto_django_spec.md §3.2.
"""
from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET

from catalogo.models import Produto
from core.permissoes import login_required_json

from .models import Lote


@login_not_required
@login_required_json
@require_GET
def lotes_produto(request, pk):
    get_object_or_404(Produto, pk=pk)
    hoje = timezone.localdate()
    dados = [
        {
            'id': lote.id,
            'numero_lote': lote.numero_lote,
            'quantidade': lote.quantidade,
            'data_validade': lote.data_validade.isoformat() if lote.data_validade else None,
            'data_validade_fmt': (
                lote.data_validade.strftime('%d/%m/%Y') if lote.data_validade else 'Sem validade'
            ),
            'dias_para_vencer': (lote.data_validade - hoje).days if lote.data_validade else None,
            'data_entrada': timezone.localtime(lote.data_entrada).date().isoformat(),
        }
        for lote in Lote.objects.filter(produto_id=pk).vendaveis()
    ]
    return JsonResponse(dados, safe=False)
