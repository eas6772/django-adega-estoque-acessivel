"""
Testes de relatorios/consultas.py. Ver docs/projeto_django_spec.md §3.1.
Foco: reaproveitar abaixo_do_minimo(), e lucro com custo CONGELADO na venda.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque.models import Lote
from relatorios import consultas
from vendas.servicos import registrar_venda


class RelatoriosBase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(nome='caixa', senha='senha123')
        self.categoria = Categoria.objects.create(nome='Vinhos')

    def produto(self, nome='P', custo='20.00', margem='50.00', **extra):
        return Produto.objects.create(
            nome=nome, categoria=self.categoria, preco_custo=Decimal(custo),
            margem_lucro=Decimal(margem), **extra,
        )

    def vender(self, lote, quantidade):
        return registrar_venda(self.usuario, [{'lote_id': lote.pk, 'quantidade': quantidade}])


class EstoqueConsultaTestCase(RelatoriosBase):
    def test_valor_de_estoque_usa_preco_de_custo(self):
        a = self.produto('A', custo='10.00')
        b = self.produto('B', custo='2.50')
        Lote.objects.create(produto=a, quantidade=3)
        Lote.objects.create(produto=a, quantidade=2)
        Lote.objects.create(produto=b, quantidade=4)
        self.assertEqual(consultas.valor_total_estoque(), Decimal('60.00'))

    def test_valor_total_sem_produtos_e_zero(self):
        self.assertEqual(consultas.valor_total_estoque(), Decimal('0.00'))

    def test_produto_inativo_fica_fora(self):
        a = self.produto('A', custo='10.00', ativo=False)
        Lote.objects.create(produto=a, quantidade=3)
        self.assertEqual(consultas.valor_total_estoque(), Decimal('0.00'))


class ReposicaoConsultaTestCase(RelatoriosBase):
    def test_quantidade_de_compra_e_maximo_menos_estoque(self):
        p = self.produto('A', estoque_minimo=5, estoque_maximo=50)
        Lote.objects.create(produto=p, quantidade=4)
        item = consultas.produtos_para_reposicao().get(pk=p.pk)
        self.assertEqual(item.qtd_compra, 46)

    def test_so_produtos_abaixo_do_minimo_e_ativos(self):
        baixo = self.produto('Baixo', estoque_minimo=5, estoque_maximo=50)
        ok = self.produto('Ok', estoque_minimo=5, estoque_maximo=50)
        inativo = self.produto('Inativo', ativo=False)
        Lote.objects.create(produto=baixo, quantidade=5)
        Lote.objects.create(produto=ok, quantidade=6)
        Lote.objects.create(produto=inativo, quantidade=0)
        nomes = [p.nome for p in consultas.produtos_para_reposicao()]
        self.assertEqual(nomes, ['Baixo'])

    def test_produto_zerado_entra_na_reposicao(self):
        self.produto('Zerado', estoque_minimo=5, estoque_maximo=30)
        item = consultas.produtos_para_reposicao().get()
        self.assertEqual(item.qtd_compra, 30)


class VendasConsultaTestCase(RelatoriosBase):
    def setUp(self):
        super().setUp()
        self.a = self.produto('A', custo='20.00', margem='50.00')  # venda 30.00
        self.b = self.produto('B', custo='10.00', margem='100.00')  # venda 20.00
        self.lote_a = Lote.objects.create(produto=self.a, quantidade=50)
        self.lote_b = Lote.objects.create(produto=self.b, quantidade=50)
        self.vender(self.lote_a, 2)
        self.vender(self.lote_b, 5)
        self.vender(self.lote_a, 1)

    def test_mais_vendidos_agrega_e_ordena_por_quantidade(self):
        linhas = list(consultas.mais_vendidos())
        self.assertEqual([l['produto__nome'] for l in linhas], ['B', 'A'])
        self.assertEqual(linhas[0]['qtd'], 5)
        self.assertEqual(linhas[0]['receita'], Decimal('100.00'))
        self.assertEqual(linhas[1]['qtd'], 3)
        self.assertEqual(linhas[1]['receita'], Decimal('90.00'))

    def test_lucro_por_produto(self):
        linhas = {l['produto__nome']: l for l in consultas.lucro_por_produto()}
        self.assertEqual(linhas['A']['custo'], Decimal('60.00'))
        self.assertEqual(linhas['A']['lucro'], Decimal('30.00'))
        self.assertEqual(linhas['B']['lucro'], Decimal('50.00'))

    def test_lucro_usa_custo_congelado_na_venda(self):
        self.a.preco_custo = Decimal('100.00')
        self.a.save()
        linhas = {l['produto__nome']: l for l in consultas.lucro_por_produto()}
        self.assertEqual(linhas['A']['custo'], Decimal('60.00'))
        self.assertEqual(linhas['A']['lucro'], Decimal('30.00'))

    def test_filtro_de_periodo(self):
        hoje = timezone.localdate()
        amanha = hoje + timedelta(days=1)
        ontem = hoje - timedelta(days=1)
        self.assertEqual(len(list(consultas.mais_vendidos(data_inicio=hoje, data_fim=hoje))), 2)
        self.assertEqual(list(consultas.mais_vendidos(data_inicio=amanha)), [])
        self.assertEqual(list(consultas.mais_vendidos(data_fim=ontem)), [])
        self.assertEqual(list(consultas.lucro_por_produto(data_inicio=amanha)), [])
