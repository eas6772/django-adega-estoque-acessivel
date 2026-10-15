"""
Testes de core/permissoes.py e do controle de acesso global: o
LoginRequiredMiddleware redireciona anônimos, AdminRequiredMixin responde 403
para operador, e os endpoints JSON respondem 401 em JSON (nunca 302).
Ver docs/projeto_django_spec.md §3 (legenda 🔓 👤 🔑) e §3.2.
"""
from django.test import TestCase
from django.urls import reverse

from core.models import Usuario


class AcessoAnonimoTestCase(TestCase):
    def test_paginas_html_redirecionam_para_login(self):
        urls = [
            reverse('core:painel'),
            reverse('core:usuario_lista'),
            reverse('catalogo:produto_lista'),
            reverse('estoque:visao_geral'),
            reverse('vendas:pdv'),
            reverse('relatorios:estoque'),
        ]
        for url in urls:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 302)
                self.assertTrue(resposta['Location'].startswith(reverse('core:login')))

    def test_login_e_publico(self):
        self.assertEqual(self.client.get(reverse('core:login')).status_code, 200)

    def test_apis_json_respondem_401_em_json(self):
        urls = [
            reverse('vendas:api_busca_produto'),
            reverse('estoque:api_lotes_produto', args=[1]),
        ]
        for url in urls:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 401)
                corpo = resposta.json()
                self.assertEqual(corpo['erro'], 'Sessão expirada.')
                self.assertIn(reverse('core:login'), corpo['login_url'])


class ProximoDoLoginJsonTestCase(TestCase):
    """O 401 devolve `next` apontando para a página do PDV, não para a API."""

    url = '/vendas/api/produtos/'

    def test_usa_o_referer_do_mesmo_host(self):
        resposta = self.client.get(self.url, headers={'referer': 'http://testserver/vendas/pdv/'})
        self.assertEqual(resposta.status_code, 401)
        self.assertIn('next=%2Fvendas%2Fpdv%2F', resposta.json()['login_url'])

    def test_ignora_referer_de_outro_host(self):
        resposta = self.client.get(self.url, headers={'referer': 'https://malicioso.example/x/'})
        self.assertIn('next=%2Fvendas%2Fapi%2Fprodutos%2F', resposta.json()['login_url'])

    def test_sem_referer_usa_a_url_da_requisicao(self):
        resposta = self.client.get(self.url)
        self.assertIn('next=%2Fvendas%2Fapi%2Fprodutos%2F', resposta.json()['login_url'])


class PerfilOperadorTestCase(TestCase):
    """Operador logado: vê as telas comuns, recebe 403 nas telas de admin."""

    def setUp(self):
        Usuario.objects.create_user(nome='operador', senha='senha123')
        self.client.login(username='operador', password='senha123')

    def test_telas_comuns_liberadas(self):
        for nome in ['core:painel', 'catalogo:produto_lista', 'estoque:visao_geral',
                     'vendas:pdv', 'relatorios:estoque', 'relatorios:reposicao']:
            with self.subTest(url=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200)

    def test_telas_de_admin_respondem_403(self):
        for nome in ['core:usuario_lista', 'core:usuario_criar', 'catalogo:produto_criar',
                     'estoque:ajuste', 'relatorios:mais_vendidos', 'relatorios:lucro',
                     'relatorios:movimentacoes']:
            with self.subTest(url=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 403)

    def test_acoes_post_de_admin_respondem_403(self):
        for nome in ['core:usuario_alternar', 'catalogo:produto_alternar',
                     'catalogo:categoria_alternar']:
            with self.subTest(url=nome):
                self.assertEqual(self.client.post(reverse(nome, args=[1])).status_code, 403)


class PerfilAdminTestCase(TestCase):
    def setUp(self):
        Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        self.client.login(username='admin', password='senha123')

    def test_telas_de_admin_liberadas(self):
        for nome in ['core:usuario_lista', 'core:usuario_criar', 'catalogo:produto_criar',
                     'estoque:ajuste', 'relatorios:mais_vendidos', 'relatorios:lucro',
                     'relatorios:movimentacoes']:
            with self.subTest(url=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200)
