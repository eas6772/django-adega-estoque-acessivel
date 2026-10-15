"""
Testes de catalogo/models.py: cálculo do preço de venda, constraints do banco
e ProdutoQuerySet. Ver docs/projeto_django_spec.md §2.3.
"""
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from catalogo.models import Categoria, Produto
from estoque.models import Lote


class ProdutoPrecoVendaTestCase(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Vinhos')

    def criar(self, **campos):
        return Produto.objects.create(nome='P', categoria=self.categoria, **campos)

    def test_preco_venda_e_custo_vezes_margem(self):
        produto = self.criar(preco_custo=Decimal('20.00'), margem_lucro=Decimal('50.00'))
        self.assertEqual(produto.preco_venda, Decimal('30.00'))

    def test_arredondamento_half_up(self):
        # 0,10 * 1,05 = 0,105 -> 0,11 (ROUND_HALF_UP; half-even daria 0,10)
        produto = self.criar(preco_custo=Decimal('0.10'), margem_lucro=Decimal('5.00'))
        self.assertEqual(produto.preco_venda, Decimal('0.11'))

    def test_preco_recalculado_a_cada_save(self):
        produto = self.criar(preco_custo=Decimal('10.00'), margem_lucro=Decimal('30.00'))
        self.assertEqual(produto.preco_venda, Decimal('13.00'))
        produto.preco_custo = Decimal('20.00')
        produto.save()
        produto.refresh_from_db()
        self.assertEqual(produto.preco_venda, Decimal('26.00'))

    def test_preco_venda_nao_e_editavel(self):
        self.assertFalse(Produto._meta.get_field('preco_venda').editable)


class ProdutoConstraintsTestCase(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Vinhos')

    def test_varios_produtos_sem_codigo_de_barras(self):
        Produto.objects.create(nome='A', categoria=self.categoria, codigo_barras=None)
        Produto.objects.create(nome='B', categoria=self.categoria, codigo_barras=None)
        self.assertEqual(Produto.objects.filter(codigo_barras__isnull=True).count(), 2)

    def test_codigo_de_barras_unico(self):
        Produto.objects.create(nome='A', categoria=self.categoria, codigo_barras='123')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Produto.objects.create(nome='B', categoria=self.categoria, codigo_barras='123')

    def test_estoque_maximo_nao_pode_ser_menor_que_minimo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Produto.objects.create(
                nome='A', categoria=self.categoria, estoque_minimo=10, estoque_maximo=5,
            )

    def test_categoria_unica_ignorando_maiusculas(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Categoria.objects.create(nome='VINHOS')


class ProdutoQuerySetTestCase(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Bebidas')
        self.baixo = Produto.objects.create(
            nome='Cerveja Pilsen', categoria=self.categoria, fabricante='Brahma',
            estoque_minimo=5, estoque_maximo=50,
        )
        self.ok = Produto.objects.create(
            nome='Vinho Tinto', categoria=self.categoria, fabricante='Aurora',
            codigo_barras='7890001', estoque_minimo=5, estoque_maximo=50,
        )
        self.sem_lote = Produto.objects.create(nome='Whisky', categoria=self.categoria)
        Lote.objects.create(produto=self.baixo, quantidade=3)
        Lote.objects.create(produto=self.baixo, quantidade=1)
        Lote.objects.create(produto=self.ok, quantidade=20)

    def test_com_estoque_soma_os_lotes(self):
        totais = {p.nome: p.estoque_total for p in Produto.objects.com_estoque()}
        self.assertEqual(totais['Cerveja Pilsen'], 4)
        self.assertEqual(totais['Vinho Tinto'], 20)

    def test_com_estoque_produto_sem_lote_vale_zero(self):
        produto = Produto.objects.com_estoque().get(pk=self.sem_lote.pk)
        self.assertEqual(produto.estoque_total, 0)

    def test_abaixo_do_minimo_inclui_zerado_e_igual_ao_minimo(self):
        no_limite = Produto.objects.create(
            nome='No Limite', categoria=self.categoria, estoque_minimo=5, estoque_maximo=50,
        )
        Lote.objects.create(produto=no_limite, quantidade=5)  # == mínimo: conta como baixo
        nomes = set(Produto.objects.abaixo_do_minimo().values_list('nome', flat=True))
        self.assertEqual(nomes, {'Cerveja Pilsen', 'Whisky', 'No Limite'})

    def test_estoque_atual_sem_anotacao(self):
        self.assertEqual(Produto.objects.get(pk=self.baixo.pk).estoque_atual, 4)

    def test_estoque_baixo(self):
        self.assertTrue(self.baixo.estoque_baixo)
        self.assertFalse(Produto.objects.get(pk=self.ok.pk).estoque_baixo)

    def test_buscar_por_nome_fabricante_e_codigo(self):
        self.assertEqual(list(Produto.objects.buscar('pilsen')), [self.baixo])
        self.assertEqual(list(Produto.objects.buscar('aurora')), [self.ok])
        self.assertEqual(list(Produto.objects.buscar('7890001')), [self.ok])

    def test_ativos(self):
        self.ok.ativo = False
        self.ok.save()
        self.assertNotIn(self.ok, Produto.objects.ativos())
