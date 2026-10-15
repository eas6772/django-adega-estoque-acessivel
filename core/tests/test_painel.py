"""
Testes da página inicial (core:painel, rotulada "Home" no menu): 4 KPIs, duas
listas, banner e a regra de que "Vendas hoje" é só do admin.
"""
import re
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque.models import Lote
from vendas.servicos import registrar_venda


class PainelBase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        self.operador = Usuario.objects.create_user(nome='caixa', senha='senha123')
        categoria = Categoria.objects.create(nome='Vinhos')
        self.hoje = timezone.localdate()

        def produto(nome, **extra):
            return Produto.objects.create(
                nome=nome, categoria=categoria, preco_custo=Decimal('20.00'),
                margem_lucro=Decimal('50.00'), estoque_minimo=5, estoque_maximo=50, **extra,
            )

        self.ok = produto('Vinho Ok')
        self.baixo = produto('Vinho Baixo')
        self.zerado = produto('Vinho Zerado')
        self.inativo = produto('Vinho Inativo', ativo=False)
        Lote.objects.create(produto=self.ok, quantidade=40,
                            data_validade=self.hoje + timedelta(days=200))
        self.lote_baixo = Lote.objects.create(
            produto=self.baixo, quantidade=3, numero_lote='B1',
            data_validade=self.hoje + timedelta(days=10),
        )
        Lote.objects.create(produto=self.inativo, quantidade=1,
                            data_validade=self.hoje + timedelta(days=5))
        self.url = reverse('core:painel')

    def abrir(self, nome):
        self.client.login(username=nome, password='senha123')
        return self.client.get(self.url)


class PainelKpisTestCase(PainelBase):
    def test_kpis(self):
        ctx = self.abrir('admin').context
        self.assertEqual(ctx['total_produtos_ativos'], 3)
        # baixo (3 <= 5) e zerado (0 <= 5); o inativo não conta.
        self.assertEqual(ctx['total_estoque_baixo'], 2)
        # só o lote do "Vinho Baixo": o do inativo e o de 200 dias ficam fora.
        self.assertEqual(ctx['total_vencendo'], 1)

    def test_lista_de_estoque_baixo_traz_zerado_primeiro(self):
        ctx = self.abrir('caixa').context
        self.assertEqual([p.nome for p in ctx['produtos_estoque_baixo']],
                         ['Vinho Zerado', 'Vinho Baixo'])

    def test_lista_de_vencimento_calcula_os_dias(self):
        ctx = self.abrir('caixa').context
        lote, = ctx['lotes_vencendo']
        self.assertEqual(lote.pk, self.lote_baixo.pk)
        self.assertEqual(lote.dias_para_vencer, 10)

    def test_lote_vencido_nao_aparece(self):
        Lote.objects.create(produto=self.ok, quantidade=2,
                            data_validade=self.hoje - timedelta(days=1))
        self.assertEqual(self.abrir('caixa').context['total_vencendo'], 1)

    def test_listas_sao_limitadas_e_o_total_continua_correto(self):
        categoria = Categoria.objects.first()
        for i in range(12):
            Produto.objects.create(nome=f'Extra {i:02d}', categoria=categoria,
                                   estoque_minimo=5, estoque_maximo=50)
        ctx = self.abrir('caixa').context
        self.assertEqual(ctx['total_estoque_baixo'], 14)
        self.assertEqual(len(ctx['produtos_estoque_baixo']), 8)

    def test_estados_vazios(self):
        Lote.objects.filter(pk=self.lote_baixo.pk).update(quantidade=40, data_validade=None)
        Lote.objects.create(produto=self.zerado, quantidade=40)
        Lote.objects.filter(produto=self.inativo).delete()
        resposta = self.abrir('caixa')
        self.assertContains(resposta, 'Todos os produtos estão com estoque adequado.')
        self.assertContains(resposta, 'Nenhum lote vence nos próximos 30 dias.')


class VendasHojeTestCase(PainelBase):
    def setUp(self):
        super().setUp()
        registrar_venda(self.admin, [{'lote_id': self.lote_baixo.pk, 'quantidade': 2}])  # 2 x 30,00

    def test_admin_ve_o_total_do_dia(self):
        resposta = self.abrir('admin')
        self.assertContains(resposta, 'Vendas hoje')
        self.assertEqual(resposta.context['vendas_hoje']['total'], Decimal('60.00'))
        self.assertEqual(resposta.context['vendas_hoje']['quantidade'], 1)
        self.assertContains(resposta, 'R$ 60,00')

    def test_operador_nao_ve_nem_recebe_o_valor(self):
        resposta = self.abrir('caixa')
        self.assertNotContains(resposta, 'Vendas hoje')
        self.assertNotContains(resposta, 'R$ 60,00')
        self.assertNotIn('vendas_hoje', resposta.context)

    def test_venda_de_ontem_nao_entra(self):
        from vendas.models import Venda
        Venda.objects.update(data=timezone.now() - timedelta(days=1, hours=1))
        ctx = self.abrir('admin').context
        self.assertEqual(ctx['vendas_hoje']['total'], Decimal('0.00'))
        self.assertEqual(ctx['vendas_hoje']['quantidade'], 0)


class PainelEstruturaTestCase(PainelBase):
    def test_banner_fica_dentro_do_main(self):
        html = self.abrir('caixa').content.decode()
        main = re.search(r'<main id="conteudo".*?</main>', html, re.S).group(0)
        self.assertIn('core/imagens/baner3.jpg', main)
        self.assertIn('Estoque baixo', main)
        self.assertIn('Próximos ao vencimento', main)

    def test_menu_tem_home_fora_dos_grupos(self):
        html = self.abrir('caixa').content.decode()
        nav = re.search(r'<nav id="menu-lateral".*?</nav>', html, re.S).group(0)
        self.assertIn('<span>Home</span>', nav)
        self.assertNotIn('<span>Painel</span>', nav)
        # o link Home vem antes do primeiro grupo (h2) do menu
        self.assertLess(nav.index('<span>Home</span>'), nav.index('<h2'))
        grupo_operacoes = re.search(r'<ul aria-labelledby="grupo-operacoes">.*?</ul>', nav, re.S).group(0)
        self.assertNotIn(reverse('core:painel'), grupo_operacoes)

    def test_home_marca_aria_current(self):
        html = self.abrir('caixa').content.decode()
        self.assertRegex(html, r'href="/painel/"\s+aria-current="page"')
