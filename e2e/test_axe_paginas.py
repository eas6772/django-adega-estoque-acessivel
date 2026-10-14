"""
Varredura axe-core nas páginas principais (docs/projeto_django_spec.md §3.5 e
§3.6 item 6): zero violações "serious"/"critical" em WCAG 2.2 AA.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from catalogo.models import Categoria, Produto
from estoque.models import Lote
from vendas.servicos import registrar_venda

from .base import NavegadorTestCase

PAGINAS_COMUNS = [
    '/painel/',
    '/catalogo/produtos/',
    '/catalogo/categorias/',
    '/estoque/',
    '/estoque/entrada/',
    '/estoque/movimentacoes/',
    '/vendas/pdv/',
    '/vendas/',
    '/relatorios/estoque/',
    '/relatorios/reposicao/',
]
PAGINAS_ADMIN = [
    '/usuarios/',
    '/usuarios/novo/',
    '/catalogo/produtos/novo/',
    '/estoque/ajuste/',
    '/relatorios/mais-vendidos/',
    '/relatorios/lucro/',
    '/relatorios/movimentacoes/',
]


class AxePaginasTestCase(NavegadorTestCase):
    def setUp(self):
        super().setUp()
        categoria = Categoria.objects.create(nome='Vinhos')
        produto = Produto.objects.create(
            nome='Vinho Tinto Seco', categoria=categoria, fabricante='Aurora',
            preco_custo=Decimal('20.00'), margem_lucro=Decimal('50.00'),
            estoque_minimo=5, estoque_maximo=50,
        )
        # Lote baixo (reposição) e vencendo (badges de status), mais uma venda.
        self.lote = Lote.objects.create(
            produto=produto, quantidade=4, numero_lote='L1',
            data_validade=timezone.localdate() + timedelta(days=10),
        )
        self.venda = registrar_venda(self.admin, [{'lote_id': self.lote.pk, 'quantidade': 1}])
        self.produto = produto

    def varrer(self, pagina, urls):
        falhas = []
        for url in urls:
            pagina.goto(url)
            graves = self.violacoes_axe(pagina)
            if graves:
                falhas.append(f'{url}\n{self.resumir(graves)}')
        self.assertEqual(falhas, [], '\n\n'.join(falhas))

    def test_login(self):
        pagina = self.novo_contexto().new_page()
        pagina.goto('/login/')
        graves = self.violacoes_axe(pagina)
        self.assertEqual(graves, [], self.resumir(graves))

    def test_paginas_do_operador(self):
        pagina = self.entrar(self.novo_contexto(), 'operador', '/painel/')
        self.varrer(pagina, PAGINAS_COMUNS)

    def test_paginas_do_admin(self):
        pagina = self.entrar(self.novo_contexto(), 'admin', '/painel/')
        urls = PAGINAS_COMUNS + PAGINAS_ADMIN + [
            f'/catalogo/produtos/{self.produto.pk}/editar/',
            f'/estoque/lotes/{self.lote.pk}/validade/',
            f'/vendas/{self.venda.pk}/recibo/',
        ]
        self.varrer(pagina, urls)
