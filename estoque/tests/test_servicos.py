"""
Testes de estoque/servicos.py: entrada, ajuste e alteração de validade.
Ver docs/projeto_django_spec.md §2.4/§2.5 e CLAUDE.md (regras de serviço).
"""
from datetime import date
from unittest import mock

from django.test import TestCase

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque import servicos
from estoque.models import Lote, Movimentacao


class ServicosEstoqueTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(nome='Vinho', categoria=categoria)

    def test_registrar_entrada_cria_lote_e_movimentacao(self):
        lote = servicos.registrar_entrada(
            usuario=self.usuario, produto=self.produto, quantidade=12,
            numero_lote='L1', data_validade=date(2030, 1, 1), motivo='Compra',
        )
        self.assertEqual(lote.quantidade, 12)
        self.assertEqual(lote.numero_lote, 'L1')
        mov = Movimentacao.objects.get()
        self.assertEqual(
            (mov.tipo, mov.quantidade, mov.lote_id, mov.produto_id, mov.usuario_id, mov.motivo),
            ('entrada', 12, lote.pk, self.produto.pk, self.usuario.pk, 'Compra'),
        )

    def test_entrada_e_atomica(self):
        with mock.patch.object(Movimentacao.objects, 'create', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                servicos.registrar_entrada(
                    usuario=self.usuario, produto=self.produto, quantidade=5,
                )
        self.assertEqual(Lote.objects.count(), 0)

    def test_ajuste_para_menos_grava_diferenca_negativa(self):
        lote = Lote.objects.create(produto=self.produto, quantidade=10)
        servicos.ajustar_lote(usuario=self.usuario, lote_id=lote.pk,
                              nova_quantidade=7, motivo='Avaria')
        lote.refresh_from_db()
        self.assertEqual(lote.quantidade, 7)
        mov = Movimentacao.objects.get()
        self.assertEqual((mov.tipo, mov.quantidade), ('ajuste', -3))

    def test_ajuste_para_mais_grava_diferenca_positiva(self):
        lote = Lote.objects.create(produto=self.produto, quantidade=2)
        servicos.ajustar_lote(usuario=self.usuario, lote_id=lote.pk, nova_quantidade=9)
        self.assertEqual(Movimentacao.objects.get().quantidade, 7)

    def test_ajuste_de_lote_inexistente_nao_grava_movimentacao(self):
        with self.assertRaises(Lote.DoesNotExist):
            servicos.ajustar_lote(usuario=self.usuario, lote_id=999999, nova_quantidade=1)
        self.assertEqual(Movimentacao.objects.count(), 0)

    def test_alterar_validade_nao_mexe_no_saldo_e_audita(self):
        lote = Lote.objects.create(
            produto=self.produto, quantidade=4, data_validade=date(2030, 1, 1),
        )
        servicos.alterar_validade(
            usuario=self.usuario, lote_id=lote.pk,
            nova_data_validade=date(2031, 6, 30), motivo='Erro de cadastro',
        )
        lote.refresh_from_db()
        self.assertEqual(lote.data_validade, date(2031, 6, 30))
        self.assertEqual(lote.quantidade, 4)
        mov = Movimentacao.objects.get()
        self.assertEqual((mov.tipo, mov.quantidade, mov.motivo), ('ajuste', 0, 'Erro de cadastro'))

    def test_alterar_validade_para_sem_validade(self):
        lote = Lote.objects.create(
            produto=self.produto, quantidade=4, data_validade=date(2030, 1, 1),
        )
        servicos.alterar_validade(usuario=self.usuario, lote_id=lote.pk, nova_data_validade=None)
        lote.refresh_from_db()
        self.assertIsNone(lote.data_validade)
