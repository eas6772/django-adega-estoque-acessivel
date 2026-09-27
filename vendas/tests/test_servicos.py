"""
Testes de vendas/servicos.py::registrar_venda. Cobrem os cenários do
critério de aceite: soma de itens repetidos, rollback em conflito, preços
congelados e a correção do bug #2 (venda dupla da mesma unidade em caixas
concorrentes) via select_for_update().
"""
import threading
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque.models import Lote, Movimentacao

from ..models import ItemVenda, Venda
from ..servicos import ConflitoEstoque, registrar_venda


class RegistrarVendaTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(nome='caixa1', senha='senha123')
        self.categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(
            nome='Vinho Tinto Seco 750ml',
            categoria=self.categoria,
            preco_custo=Decimal('10.00'),
            margem_lucro=Decimal('50.00'),
        )
        self.lote = Lote.objects.create(produto=self.produto, quantidade=10)

    def test_venda_baixa_estoque_cria_item_e_movimentacao(self):
        venda = registrar_venda(self.usuario, [{'lote_id': self.lote.id, 'quantidade': 3}])

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade, 7)

        itens = ItemVenda.objects.filter(venda=venda)
        self.assertEqual(itens.count(), 1)
        item = itens.first()
        self.assertEqual(item.quantidade, 3)
        self.assertEqual(item.preco_unitario, self.produto.preco_venda)
        self.assertEqual(item.custo_unitario, self.produto.preco_custo)

        movimentacoes = Movimentacao.objects.filter(venda=venda)
        self.assertEqual(movimentacoes.count(), 1)
        self.assertEqual(movimentacoes.first().tipo, Movimentacao.Tipo.SAIDA)

        self.assertEqual(venda.total, self.produto.preco_venda * 3)

    def test_itens_repetidos_do_mesmo_lote_sao_somados(self):
        itens = [
            {'lote_id': self.lote.id, 'quantidade': 2},
            {'lote_id': self.lote.id, 'quantidade': 3},
        ]
        venda = registrar_venda(self.usuario, itens)

        self.assertEqual(ItemVenda.objects.filter(venda=venda).count(), 1)
        item = ItemVenda.objects.get(venda=venda)
        self.assertEqual(item.quantidade, 5)

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade, 5)

    def test_conflito_estoque_faz_rollback_completo(self):
        self.lote.quantidade = 2
        self.lote.save(update_fields=['quantidade'])

        with self.assertRaises(ConflitoEstoque):
            registrar_venda(self.usuario, [{'lote_id': self.lote.id, 'quantidade': 5}])

        self.assertEqual(Venda.objects.count(), 0)
        self.assertEqual(ItemVenda.objects.count(), 0)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade, 2)

    def test_lote_vencido_gera_conflito(self):
        self.lote.data_validade = timezone.localdate() - timedelta(days=1)
        self.lote.save(update_fields=['data_validade'])

        with self.assertRaisesMessage(ConflitoEstoque, 'vencido'):
            registrar_venda(self.usuario, [{'lote_id': self.lote.id, 'quantidade': 1}])
        self.assertEqual(Venda.objects.count(), 0)

    def test_produto_inativo_gera_conflito(self):
        self.produto.ativo = False
        self.produto.save(update_fields=['ativo'])

        with self.assertRaisesMessage(ConflitoEstoque, 'indisponível'):
            registrar_venda(self.usuario, [{'lote_id': self.lote.id, 'quantidade': 1}])
        self.assertEqual(Venda.objects.count(), 0)

    def test_lote_inexistente_gera_conflito(self):
        lote_id_inexistente = self.lote.id + 999
        with self.assertRaises(ConflitoEstoque):
            registrar_venda(self.usuario, [{'lote_id': lote_id_inexistente, 'quantidade': 1}])
        self.assertEqual(Venda.objects.count(), 0)

    def test_custo_e_preco_ficam_congelados(self):
        venda = registrar_venda(self.usuario, [{'lote_id': self.lote.id, 'quantidade': 1}])
        item = ItemVenda.objects.get(venda=venda)
        preco_unitario_original = item.preco_unitario
        custo_unitario_original = item.custo_unitario

        self.produto.preco_custo = Decimal('99.00')
        self.produto.margem_lucro = Decimal('200.00')
        self.produto.save()

        item.refresh_from_db()
        self.assertEqual(item.preco_unitario, preco_unitario_original)
        self.assertEqual(item.custo_unitario, custo_unitario_original)


class ConcorrenciaVendaTestCase(TransactionTestCase):
    """
    Prova a correção do bug #2 (Flask sem trava de linha): dois caixas
    concorrentes disputando a última unidade do mesmo lote. TransactionTestCase
    é necessário (não TestCase) porque as duas threads precisam de conexões e
    transações reais e committadas para o select_for_update() bloquear de
    fato — TestCase envolve o teste inteiro numa única transação com
    savepoints, que não reproduz bloqueio entre conexões distintas.
    """

    def setUp(self):
        self.usuario = Usuario.objects.create_user(nome='caixa2', senha='senha123')
        self.categoria = Categoria.objects.create(nome='Cervejas')
        self.produto = Produto.objects.create(
            nome='Cerveja Teste 350ml',
            categoria=self.categoria,
            preco_custo=Decimal('5.00'),
            margem_lucro=Decimal('40.00'),
        )
        self.lote = Lote.objects.create(produto=self.produto, quantidade=1)

    def test_concorrencia_select_for_update_impede_venda_duplicada(self):
        barreira = threading.Barrier(2)
        resultados = []

        def tentar_vender():
            from django.db import connection

            barreira.wait()
            try:
                venda = registrar_venda(self.usuario, [{'lote_id': self.lote.id, 'quantidade': 1}])
                resultados.append(('ok', venda.id))
            except ConflitoEstoque as erro:
                resultados.append(('conflito', erro.disponivel))
            finally:
                # Fecha a conexão desta thread explicitamente: cada thread
                # abre sua própria conexão automaticamente (connection é
                # thread-local), e o Postgres não deixa dropar o banco de
                # teste com sessões ainda vivas no teardown.
                connection.close()

        threads = [threading.Thread(target=tentar_vender) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        sucessos = [r for r in resultados if r[0] == 'ok']
        conflitos = [r for r in resultados if r[0] == 'conflito']
        self.assertEqual(len(sucessos), 1)
        self.assertEqual(len(conflitos), 1)

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade, 0)
        self.assertEqual(Venda.objects.count(), 1)
