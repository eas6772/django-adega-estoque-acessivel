"""
Testes de Lote/LoteQuerySet: regra PEPS e vencimento. É a fonte de verdade de
"quanto posso vender" (CLAUDE.md). Ver docs/projeto_django_spec.md §2.4.
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from catalogo.models import Categoria, Produto
from estoque.models import Lote


class LoteQuerySetTestCase(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(nome='Vinho', categoria=categoria)
        self.hoje = timezone.localdate()

    def lote(self, quantidade=5, dias=None):
        validade = None if dias is None else self.hoje + timedelta(days=dias)
        return Lote.objects.create(produto=self.produto, quantidade=quantidade,
                                   data_validade=validade)

    def test_vendaveis_exclui_zerado_e_vencido(self):
        valido = self.lote(dias=10)
        self.lote(quantidade=0, dias=10)
        self.lote(dias=-1)
        self.assertEqual(list(Lote.objects.vendaveis()), [valido])

    def test_lote_que_vence_hoje_ainda_e_vendavel(self):
        lote = self.lote(dias=0)
        self.assertIn(lote, Lote.objects.vendaveis())

    def test_ordem_peps_validade_mais_proxima_primeiro_e_nulos_por_ultimo(self):
        sem_validade = self.lote()
        longe = self.lote(dias=90)
        perto = self.lote(dias=5)
        self.assertEqual(list(Lote.objects.vendaveis()), [perto, longe, sem_validade])

    def test_empate_de_validade_desempata_por_id(self):
        a = self.lote(dias=5)
        b = self.lote(dias=5)
        self.assertEqual(list(Lote.objects.vendaveis()), [a, b])

    def test_vencendo_em_30_dias(self):
        dentro = self.lote(dias=30)
        self.lote(dias=31)
        self.lote(dias=-2)
        self.assertEqual(list(Lote.objects.vencendo_em(30)), [dentro])

    def test_propriedades_vencido_e_proximo_vencimento(self):
        self.assertTrue(self.lote(dias=-1).vencido)
        self.assertFalse(self.lote(dias=0).vencido)
        self.assertTrue(self.lote(dias=30).proximo_vencimento)
        self.assertFalse(self.lote(dias=31).proximo_vencimento)
        self.assertFalse(self.lote().vencido)
        self.assertFalse(self.lote().proximo_vencimento)

    def test_saldo_negativo_e_barrado_pelo_banco(self):
        lote = self.lote()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Lote.objects.filter(pk=lote.pk).update(quantidade=-1)
