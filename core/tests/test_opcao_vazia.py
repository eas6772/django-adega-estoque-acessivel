"""Todo <select> com opção vazia mostra "Selecione uma opção" (nunca o "---------" do Django)."""
from django.test import TestCase
from django.urls import reverse

from catalogo.forms import FiltroProdutoForm, ProdutoForm
from catalogo.models import Categoria
from core.models import Usuario
from estoque.forms import AjusteForm, EntradaForm


class OpcaoVaziaTestCase(TestCase):
    def test_formularios_usam_o_rotulo_em_portugues(self):
        Categoria.objects.create(nome='Vinhos')
        for form in [ProdutoForm(), FiltroProdutoForm(), EntradaForm(), AjusteForm()]:
            with self.subTest(form=type(form).__name__):
                html = str(form)
                self.assertIn('Selecione uma opção', html)
                self.assertNotIn('---------', html)

    def test_paginas_nao_exibem_o_rotulo_padrao_do_django(self):
        Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        self.client.login(username='admin', password='senha123')
        for nome in ['catalogo:produto_lista', 'catalogo:produto_criar', 'estoque:entrada', 'estoque:ajuste']:
            with self.subTest(url=nome):
                resposta = self.client.get(reverse(nome))
                self.assertNotContains(resposta, '---------')
                self.assertContains(resposta, 'Selecione uma opção')
