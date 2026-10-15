"""
Testes de relatorios/views.py e relatorios/pdf.py. Ver
docs/projeto_django_spec.md §3.1.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque.models import Lote
from vendas.servicos import registrar_venda


class RelatoriosViewsTestCase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        self.operador = Usuario.objects.create_user(nome='operador', senha='senha123')
        categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(
            nome='Vinho Tinto', categoria=categoria, preco_custo=Decimal('20.00'),
            margem_lucro=Decimal('50.00'), estoque_minimo=5, estoque_maximo=50,
        )
        self.lote = Lote.objects.create(produto=self.produto, quantidade=10)
        registrar_venda(self.admin, [{'lote_id': self.lote.pk, 'quantidade': 2}])

    def entrar(self, nome):
        self.client.login(username=nome, password='senha123')

    def test_estoque_mostra_valor_total(self):
        self.entrar('operador')
        resposta = self.client.get(reverse('relatorios:estoque'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['valor_total'], Decimal('160.00'))
        self.assertContains(resposta, 'Vinho Tinto')

    def test_reposicao_lista_produtos_abaixo_do_minimo(self):
        self.entrar('operador')
        Lote.objects.filter(pk=self.lote.pk).update(quantidade=3)
        resposta = self.client.get(reverse('relatorios:reposicao'))
        self.assertEqual([p.nome for p in resposta.context['produtos']], ['Vinho Tinto'])

    def test_reposicao_pdf(self):
        self.entrar('operador')
        resposta = self.client.get(reverse('relatorios:reposicao_pdf'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta['Content-Type'], 'application/pdf')
        self.assertIn('attachment', resposta['Content-Disposition'])
        self.assertIn(f'reposicao-{timezone.localdate():%Y%m%d}.pdf',
                      resposta['Content-Disposition'])
        conteudo = b''.join(resposta.streaming_content)
        self.assertTrue(conteudo.startswith(b'%PDF'))

    def test_estoque_pdf_inventario_completo(self):
        self.entrar('operador')
        resposta = self.client.get(reverse('relatorios:estoque'))
        self.assertContains(resposta, reverse('relatorios:estoque_pdf'))
        resposta = self.client.get(reverse('relatorios:estoque_pdf'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta['Content-Type'], 'application/pdf')
        self.assertIn(f'estoque-{timezone.localdate():%Y%m%d}.pdf', resposta['Content-Disposition'])
        self.assertTrue(b''.join(resposta.streaming_content).startswith(b'%PDF'))

    def test_paginas_de_relatorio_nao_tem_mais_o_menu_superior(self):
        self.entrar('admin')
        for nome in ['estoque', 'reposicao', 'mais_vendidos', 'lucro', 'movimentacoes']:
            with self.subTest(pagina=nome):
                self.assertNotContains(self.client.get(reverse(f'relatorios:{nome}')), 'abas-relatorio')

    def test_movimentacoes_usa_campos_de_data_com_calendario(self):
        self.entrar('admin')
        resposta = self.client.get(reverse('relatorios:movimentacoes'), {'data_inicio': '2026-10-01'})
        self.assertContains(resposta, 'type="date"', count=2)
        self.assertContains(resposta, 'value="2026-10-01"')
        self.assertRegex(resposta.content.decode(), r'<label for="id_data_inicio">\s*De\s*</label>')

    def test_mais_vendidos_admin(self):
        self.entrar('admin')
        resposta = self.client.get(reverse('relatorios:mais_vendidos'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['itens'][0]['qtd'], 2)

    def test_mais_vendidos_respeita_periodo(self):
        self.entrar('admin')
        amanha = (timezone.localdate() + timedelta(days=1)).isoformat()
        resposta = self.client.get(reverse('relatorios:mais_vendidos'), {'data_inicio': amanha})
        self.assertEqual(len(resposta.context['itens']), 0)

    def test_periodo_invalido_e_ignorado(self):
        self.entrar('admin')
        resposta = self.client.get(reverse('relatorios:lucro'), {'data_inicio': 'lixo'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.context['itens']), 1)

    def test_lucro_admin(self):
        self.entrar('admin')
        resposta = self.client.get(reverse('relatorios:lucro'))
        item = resposta.context['itens'][0]
        self.assertEqual(item['lucro'], Decimal('20.00'))

    def test_movimentacoes_relatorio_herda_filtros_do_estoque(self):
        self.entrar('admin')
        url = reverse('relatorios:movimentacoes')
        todas = self.client.get(url)
        self.assertEqual(len(todas.context['movimentacoes']), 1)  # a saída da venda
        entradas = self.client.get(url, {'tipo': 'entrada'})
        self.assertEqual(len(entradas.context['movimentacoes']), 0)

    def test_paginas_restritas_negam_operador(self):
        self.entrar('operador')
        for nome in ['mais_vendidos', 'lucro', 'movimentacoes']:
            with self.subTest(relatorio=nome):
                self.assertEqual(self.client.get(reverse(f'relatorios:{nome}')).status_code, 403)
