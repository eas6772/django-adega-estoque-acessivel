"""Comando seed_demo: dados de demonstração para o deploy (Render + Supabase)."""
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from catalogo.models import Produto
from core.models import Usuario
from estoque.models import Lote, Movimentacao
from vendas.models import Venda


def rodar(**opcoes):
    saida = StringIO()
    call_command('seed_demo', stdout=saida, **opcoes)
    return saida.getvalue()


class SeedDemoTestCase(TestCase):
    def test_cria_usuarios_catalogo_estoque_e_vendas(self):
        rodar(senha_admin='senha-admin-1', senha_caixa='senha-caixa-1')

        admin = Usuario.objects.get(nome='admin')
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.check_password('senha-admin-1'))
        self.assertFalse(Usuario.objects.get(nome='caixa').is_admin)

        self.assertEqual(Produto.objects.count(), 8)
        self.assertGreaterEqual(Venda.objects.count(), 3)
        # as vendas baixaram o estoque pelo serviço (saldo nunca negativo) e geraram movimentações
        self.assertFalse(Lote.objects.filter(quantidade__lt=0).exists())
        self.assertTrue(Movimentacao.objects.filter(tipo=Movimentacao.Tipo.SAIDA).exists())

    def test_tem_alertas_para_a_home(self):
        rodar(senha_admin='a', senha_caixa='b')
        com_estoque = Produto.objects.ativos().com_estoque()
        self.assertTrue(com_estoque.abaixo_do_minimo().exists())
        self.assertEqual(Produto.objects.get(nome='Gin London Dry').lotes.count(), 0)  # zerado

    def test_segunda_execucao_nao_duplica(self):
        rodar(senha_admin='a', senha_caixa='b')
        produtos, vendas = Produto.objects.count(), Venda.objects.count()
        saida = rodar()  # usuários já existem: não pede senha
        self.assertIn('não recarregados', saida)
        self.assertEqual(Produto.objects.count(), produtos)
        self.assertEqual(Venda.objects.count(), vendas)

    def test_exige_senha_quando_o_usuario_ainda_nao_existe(self):
        with self.assertRaisesMessage(CommandError, 'DEMO_ADMIN_SENHA'):
            rodar()
        self.assertEqual(Produto.objects.count(), 0)

    def test_nao_troca_senha_de_usuario_existente(self):
        Usuario.objects.create_user(nome='admin', senha='original', perfil='admin')
        rodar(senha_admin='outra', senha_caixa='b')
        self.assertTrue(Usuario.objects.get(nome='admin').check_password('original'))
