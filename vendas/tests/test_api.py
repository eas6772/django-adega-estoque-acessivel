"""
Testes de vendas/api.py — contrato JSON de docs/projeto_django_spec.md §3.2:
status codes, formato da resposta e, principalmente, que a sessão expirada
devolve 401 em JSON (nunca um redirect 302) e que o CSRF é exigido.
"""
import json
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque.models import Lote


class BuscarProdutoTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(nome='caixa', senha='senha123')
        self.client.login(username='caixa', password='senha123')
        self.categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(
            nome='Vinho Tinto Seco 750ml',
            categoria=self.categoria,
            fabricante='Aurora',
            codigo_barras='7891234567890',
            preco_custo=Decimal('20.00'),
            margem_lucro=Decimal('50.00'),
        )
        Lote.objects.create(produto=self.produto, quantidade=17)
        self.url = reverse('vendas:api_busca_produto')

    def test_busca_menos_de_2_chars(self):
        resposta = self.client.get(self.url, {'q': 'v'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), [])

    def test_busca_retorna_campos_esperados(self):
        resposta = self.client.get(self.url, {'q': 'vinho'})
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(len(dados), 1)
        item = dados[0]
        self.assertEqual(item['id'], self.produto.id)
        self.assertEqual(item['nome'], self.produto.nome)
        self.assertEqual(item['fabricante'], self.produto.fabricante)
        self.assertEqual(item['codigo_barras'], self.produto.codigo_barras)
        self.assertEqual(item['preco_venda'], str(self.produto.preco_venda))
        self.assertIsInstance(item['preco_venda'], str)
        self.assertEqual(item['estoque'], 17)
        self.assertFalse(item['match_exato'])

    def test_busca_match_exato_codigo_barras(self):
        resposta = self.client.get(self.url, {'q': self.produto.codigo_barras})
        dados = resposta.json()
        self.assertEqual(len(dados), 1)
        self.assertTrue(dados[0]['match_exato'])


class CriarVendaTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(nome='caixa', senha='senha123')
        self.categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(
            nome='Vinho Tinto Seco 750ml',
            categoria=self.categoria,
            preco_custo=Decimal('20.00'),
            margem_lucro=Decimal('50.00'),
        )
        self.lote = Lote.objects.create(produto=self.produto, quantidade=5)
        self.url = reverse('vendas:api_venda_criar')

    def test_criar_venda_sucesso_201(self):
        self.client.login(username='caixa', password='senha123')
        resposta = self.client.post(
            self.url,
            data=json.dumps({'itens': [{'lote_id': self.lote.id, 'quantidade': 2}]}),
            content_type='application/json',
        )
        self.assertEqual(resposta.status_code, 201)
        dados = resposta.json()
        self.assertIn('id', dados)
        self.assertEqual(dados['total'], str(self.produto.preco_venda * 2))
        self.assertEqual(dados['recibo_url'], reverse('vendas:recibo', args=[dados['id']]))

    def test_criar_venda_json_malformado_400(self):
        self.client.login(username='caixa', password='senha123')
        resposta = self.client.post(self.url, data='não é json', content_type='application/json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('erro', resposta.json())

    def test_criar_venda_itens_vazio_400(self):
        self.client.login(username='caixa', password='senha123')
        resposta = self.client.post(
            self.url, data=json.dumps({'itens': []}), content_type='application/json',
        )
        self.assertEqual(resposta.status_code, 400)

    def test_criar_venda_quantidade_invalida_400(self):
        self.client.login(username='caixa', password='senha123')
        resposta = self.client.post(
            self.url,
            data=json.dumps({'itens': [{'lote_id': self.lote.id, 'quantidade': 0}]}),
            content_type='application/json',
        )
        self.assertEqual(resposta.status_code, 400)

    def test_criar_venda_sem_login_401_json(self):
        resposta = self.client.post(
            self.url,
            data=json.dumps({'itens': [{'lote_id': self.lote.id, 'quantidade': 1}]}),
            content_type='application/json',
        )
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta['Content-Type'], 'application/json')
        dados = resposta.json()
        self.assertIn('login_url', dados)
        self.assertIn('next=', dados['login_url'])

    def test_criar_venda_conflito_409(self):
        self.client.login(username='caixa', password='senha123')
        resposta = self.client.post(
            self.url,
            data=json.dumps({'itens': [{'lote_id': self.lote.id, 'quantidade': 99}]}),
            content_type='application/json',
        )
        self.assertEqual(resposta.status_code, 409)
        dados = resposta.json()
        self.assertEqual(dados['lote_id'], self.lote.id)
        self.assertEqual(dados['item_index'], 0)
        self.assertEqual(dados['disponivel'], 5)

    def test_criar_venda_csrf_ausente_403(self):
        client_com_csrf = Client(enforce_csrf_checks=True)
        client_com_csrf.login(username='caixa', password='senha123')
        resposta = client_com_csrf.post(
            self.url,
            data=json.dumps({'itens': [{'lote_id': self.lote.id, 'quantidade': 1}]}),
            content_type='application/json',
        )
        self.assertEqual(resposta.status_code, 403)
