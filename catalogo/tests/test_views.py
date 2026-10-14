"""
Testes de forms e views de catalogo. Ver docs/projeto_django_spec.md §3.1.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalogo.forms import ProdutoForm
from catalogo.models import Categoria, Produto
from core.models import Usuario


class ProdutoFormTestCase(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Vinhos')

    def dados(self, **extra):
        base = {
            'nome': 'Vinho', 'categoria': self.categoria.pk, 'fabricante': '', 'volume': '',
            'peso': '', 'codigo_barras': '', 'margem_lucro': '30.00', 'preco_custo': '10.00',
            'estoque_minimo': '5', 'estoque_maximo': '100', 'ativo': 'on',
        }
        base.update(extra)
        return base

    def test_preco_venda_nao_e_campo_do_formulario(self):
        self.assertNotIn('preco_venda', ProdutoForm().fields)

    def test_codigo_de_barras_vazio_vira_none(self):
        form = ProdutoForm(self.dados(codigo_barras='   '))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['codigo_barras'])

    def test_maximo_menor_que_minimo(self):
        form = ProdutoForm(self.dados(estoque_minimo='10', estoque_maximo='5'))
        self.assertFalse(form.is_valid())
        self.assertIn('estoque_maximo', form.errors)

    def test_custo_negativo_rejeitado(self):
        form = ProdutoForm(self.dados(preco_custo='-1'))
        self.assertFalse(form.is_valid())
        self.assertIn('preco_custo', form.errors)


class CatalogoViewsBase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        self.client.login(username='admin', password='senha123')
        self.categoria = Categoria.objects.create(nome='Vinhos')


class CategoriaViewsTestCase(CatalogoViewsBase):
    def test_lista_conta_apenas_produtos_ativos(self):
        Produto.objects.create(nome='A', categoria=self.categoria)
        Produto.objects.create(nome='B', categoria=self.categoria, ativo=False)
        resposta = self.client.get(reverse('catalogo:categoria_lista'))
        categoria = resposta.context['categorias'].get(pk=self.categoria.pk)
        self.assertEqual(categoria.num_produtos, 1)

    def test_criar_categoria(self):
        resposta = self.client.post(reverse('catalogo:categoria_criar'),
                                    {'nome': 'Cervejas', 'ativo': 'on'})
        self.assertRedirects(resposta, reverse('catalogo:categoria_lista'))
        self.assertTrue(Categoria.objects.filter(nome='Cervejas').exists())

    def test_criar_categoria_duplicada_reexibe_lista_com_erro(self):
        resposta = self.client.post(reverse('catalogo:categoria_criar'),
                                    {'nome': 'vinhos', 'ativo': 'on'})
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('nome', resposta.context['form_categoria'].errors)
        self.assertEqual(Categoria.objects.count(), 1)

    def test_editar_categoria(self):
        url = reverse('catalogo:categoria_editar', args=[self.categoria.pk])
        self.client.post(url, {'nome': 'Vinhos Finos', 'ativo': 'on'})
        self.categoria.refresh_from_db()
        self.assertEqual(self.categoria.nome, 'Vinhos Finos')

    def test_alternar_categoria(self):
        url = reverse('catalogo:categoria_alternar', args=[self.categoria.pk])
        self.client.post(url)
        self.categoria.refresh_from_db()
        self.assertFalse(self.categoria.ativo)


class ProdutoViewsTestCase(CatalogoViewsBase):
    def dados(self, **extra):
        base = {
            'nome': 'Vinho Novo', 'categoria': self.categoria.pk, 'fabricante': 'Aurora',
            'volume': '750ml', 'peso': '', 'codigo_barras': '', 'margem_lucro': '50.00',
            'preco_custo': '20.00', 'estoque_minimo': '5', 'estoque_maximo': '100', 'ativo': 'on',
        }
        base.update(extra)
        return base

    def test_criar_produto_calcula_preco_de_venda(self):
        resposta = self.client.post(reverse('catalogo:produto_criar'), self.dados())
        self.assertRedirects(resposta, reverse('catalogo:produto_lista'))
        produto = Produto.objects.get(nome='Vinho Novo')
        self.assertEqual(produto.preco_venda, Decimal('30.00'))

    def test_cliente_nao_consegue_forcar_preco_de_venda(self):
        self.client.post(reverse('catalogo:produto_criar'), self.dados(preco_venda='1.00'))
        self.assertEqual(Produto.objects.get(nome='Vinho Novo').preco_venda, Decimal('30.00'))

    def test_editar_produto(self):
        produto = Produto.objects.create(nome='Velho', categoria=self.categoria)
        url = reverse('catalogo:produto_editar', args=[produto.pk])
        self.client.post(url, self.dados(nome='Atualizado'))
        produto.refresh_from_db()
        self.assertEqual(produto.nome, 'Atualizado')

    def test_alternar_produto(self):
        produto = Produto.objects.create(nome='P', categoria=self.categoria)
        self.client.post(reverse('catalogo:produto_alternar', args=[produto.pk]))
        produto.refresh_from_db()
        self.assertFalse(produto.ativo)

    def test_lista_oculta_inativos_por_padrao(self):
        Produto.objects.create(nome='Ativo', categoria=self.categoria)
        Produto.objects.create(nome='Inativo', categoria=self.categoria, ativo=False)
        resposta = self.client.get(reverse('catalogo:produto_lista'))
        nomes = [p.nome for p in resposta.context['produtos']]
        self.assertEqual(nomes, ['Ativo'])

    def test_lista_mostra_inativos_quando_pedido(self):
        Produto.objects.create(nome='Ativo', categoria=self.categoria)
        Produto.objects.create(nome='Inativo', categoria=self.categoria, ativo=False)
        resposta = self.client.get(reverse('catalogo:produto_lista'), {'mostrar_inativos': 'on'})
        self.assertEqual(len(resposta.context['produtos']), 2)

    def test_lista_filtra_por_busca_e_categoria(self):
        outra = Categoria.objects.create(nome='Cervejas')
        Produto.objects.create(nome='Vinho Tinto', categoria=self.categoria)
        Produto.objects.create(nome='Cerveja Pilsen', categoria=outra)
        url = reverse('catalogo:produto_lista')
        busca = self.client.get(url, {'q': 'pilsen'})
        self.assertEqual([p.nome for p in busca.context['produtos']], ['Cerveja Pilsen'])
        cat = self.client.get(url, {'categoria': self.categoria.pk})
        self.assertEqual([p.nome for p in cat.context['produtos']], ['Vinho Tinto'])

    def test_lista_pagina_de_15_em_15(self):
        for i in range(20):
            Produto.objects.create(nome=f'P{i:02d}', categoria=self.categoria)
        resposta = self.client.get(reverse('catalogo:produto_lista'))
        self.assertEqual(len(resposta.context['produtos']), 15)

    def test_nome_do_produto_e_escapado_no_html(self):
        Produto.objects.create(nome='<img src=x onerror=alert(1)>', categoria=self.categoria)
        resposta = self.client.get(reverse('catalogo:produto_lista'))
        self.assertNotContains(resposta, '<img src=x onerror=alert(1)>')
        self.assertContains(resposta, '&lt;img src=x onerror=alert(1)&gt;')
