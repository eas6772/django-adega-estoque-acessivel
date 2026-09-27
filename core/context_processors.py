"""
Rede de segurança para a seção ativa do menu: cada CBV já define
`secao_ativa` explicitamente (ver core.views.SecaoAtivaMixin). Este context
processor só garante que a variável exista mesmo em views que não usem o
mixin (function-based views, páginas de erro etc.).
"""
SECOES_POR_NAMESPACE = {
    'core': 'painel',
    'catalogo': 'catalogo',
    'estoque': 'estoque',
    'vendas': 'vendas',
    'relatorios': 'relatorios',
}


def secao_ativa(request):
    match = getattr(request, 'resolver_match', None)
    namespace = match.namespace if match else None
    return {'secao_ativa': SECOES_POR_NAMESPACE.get(namespace)}
