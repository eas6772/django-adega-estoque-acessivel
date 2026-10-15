"""
O título da página (h1) fica na topbar, nunca na área de conteúdo (main).
Garante também um único h1 por página (spec §3.5 A3).
"""
import re
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque.models import Lote
from vendas.servicos import registrar_venda


class TituloNaTopbarTestCase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(
            nome='Vinho', categoria=categoria, preco_custo=Decimal('10.00'),
        )
        self.lote = Lote.objects.create(produto=self.produto, quantidade=5)
        self.venda = registrar_venda(self.admin, [{'lote_id': self.lote.pk, 'quantidade': 1}])
        self.client.login(username='admin', password='senha123')

    def paginas(self):
        return {
            'core:painel': ('Home', []),
            'vendas:pdv': ('Frente de caixa', []),
            'vendas:venda_lista': ('Vendas', []),
            'vendas:recibo': (f'Recibo da venda #{self.venda.pk}', [self.venda.pk]),
            'catalogo:categoria_lista': ('Categorias', []),
            'catalogo:produto_lista': ('Produtos', []),
            'catalogo:produto_criar': ('Novo produto', []),
            'estoque:visao_geral': ('Visão geral', []),
            'estoque:entrada': ('Registrar entrada de estoque', []),
            'estoque:ajuste': ('Ajustar estoque', []),
            'estoque:movimentacao_lista': ('Movimentações', []),
            'relatorios:estoque': ('Estoque', []),
            'relatorios:reposicao': ('Reposição', []),
            'relatorios:mais_vendidos': ('Mais vendidos', []),
            'relatorios:lucro': ('Lucro', []),
            'relatorios:movimentacoes': ('Movimentações', []),
            'core:usuario_lista': ('Usuários', []),
            'core:usuario_criar': ('Novo usuário', []),
        }

    def test_h1_unico_na_topbar_e_nenhum_no_main(self):
        for nome, (titulo, args) in self.paginas().items():
            with self.subTest(pagina=nome):
                html = self.client.get(reverse(nome, args=args)).content.decode()
                self.assertEqual(len(re.findall(r'<h1[\s>]', html)), 1)
                topbar = re.search(r'<header class="topbar">.*?</header>', html, re.S).group(0)
                self.assertRegex(topbar, rf'<h1 class="topbar-titulo">\s*{re.escape(titulo)}\s*</h1>')
                main = re.search(r'<main id="conteudo".*?</main>', html, re.S).group(0)
                self.assertNotIn('<h1', main)

    def test_login_tem_h1_na_topbar(self):
        self.client.logout()
        html = self.client.get(reverse('core:login')).content.decode()
        self.assertEqual(len(re.findall(r'<h1[\s>]', html)), 1)
        self.assertRegex(html, r'<h1 class="topbar-titulo">\s*Entrar\s*</h1>')
