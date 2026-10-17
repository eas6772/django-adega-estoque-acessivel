"""Dicas de botões só de ícone: mouse, teclado, Esc (WCAG 1.4.13) e axe com a dica aberta."""
from e2e.base import NavegadorTestCase


class DicasTest(NavegadorTestCase):
    def test_dica_no_mouse_no_foco_e_esc(self):
        pagina = self.entrar(self.novo_contexto(), nome='admin', destino='/painel/')
        dica = pagina.locator('.dica')
        botao = pagina.get_by_role('button', name='Sair do sistema')

        botao.hover()
        dica.wait_for(state='visible')
        self.assertEqual(dica.inner_text(), 'Sair do sistema')
        self.assertEqual(dica.get_attribute('aria-hidden'), 'true')

        pagina.keyboard.press('Escape')
        dica.wait_for(state='hidden')

        pagina.mouse.move(0, 400)
        botao.focus()
        pagina.keyboard.press('Tab')
        pagina.keyboard.press('Shift+Tab')
        dica.wait_for(state='visible')
        self.assertEqual(dica.inner_text(), 'Sair do sistema')

        pagina.keyboard.press('Tab')
        dica.wait_for(state='hidden')

    def test_dica_visivel_passa_no_axe(self):
        pagina = self.entrar(self.novo_contexto(), nome='admin', destino='/painel/')
        pagina.get_by_role('button', name='Sair do sistema').hover()
        pagina.locator('.dica').wait_for(state='visible')
        self.assertEqual(self.violacoes_axe(pagina), [], self.resumir(self.violacoes_axe(pagina)))

    def test_dica_nas_acoes_de_produtos_e_categorias(self):
        from decimal import Decimal

        from catalogo.models import Categoria, Produto
        categoria = Categoria.objects.create(nome='Vinhos')
        Produto.objects.create(nome='Vinho Tinto', categoria=categoria, preco_custo=Decimal('10'), margem_lucro=Decimal('50'),
                               estoque_minimo=1, estoque_maximo=5)
        pagina = self.entrar(self.novo_contexto(), nome='admin', destino='/catalogo/produtos/')
        dica = pagina.locator('.dica')
        for url, rotulo in (('/catalogo/produtos/', 'Editar Vinho Tinto'), ('/catalogo/produtos/', 'Desativar Vinho Tinto'),
                            ('/catalogo/categorias/', 'Editar Vinhos'), ('/catalogo/categorias/', 'Desativar Vinhos')):
            pagina.goto(url)
            pagina.get_by_role('button' if 'categorias' in url or 'Desativar' in rotulo else 'link', name=rotulo).hover()
            dica.wait_for(state='visible')
            self.assertEqual(dica.inner_text(), rotulo)
