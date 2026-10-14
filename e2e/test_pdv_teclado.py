"""
Critérios de aceite da frente de caixa — docs/projeto_django_spec.md §3.6.
O item 2 (NVDA/Orca) é manual e não aparece aqui.
"""
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.sessions.models import Session
from django.utils import timezone
from playwright.sync_api import expect

from catalogo.models import Categoria, Produto
from estoque.models import Lote
from vendas.models import Venda

from .base import NavegadorTestCase

XSS = '<img src=x onerror="window.__xss=1">'


class PdvBase(NavegadorTestCase):
    def setUp(self):
        super().setUp()
        categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(
            nome='Vinho Tinto Seco', categoria=categoria, fabricante='Aurora',
            preco_custo=Decimal('20.00'), margem_lucro=Decimal('50.00'),  # venda 30,00
        )
        self.lote = Lote.objects.create(
            produto=self.produto, quantidade=5, numero_lote='L1',
            data_validade=timezone.localdate() + timedelta(days=20),
        )

    def adicionar_pelo_teclado(self, pagina, termo='vin', quantidade='2'):
        pagina.keyboard.press('F2')
        expect(pagina.locator('#busca-produto')).to_be_focused()
        pagina.keyboard.type(termo)
        expect(pagina.locator('#resultados-busca')).to_be_visible()
        pagina.keyboard.press('ArrowDown')
        pagina.keyboard.press('Enter')
        expect(pagina.locator('#dialogo-lote')).to_be_visible()
        expect(pagina.locator('#lote-select')).not_to_have_attribute('aria-busy', 'true')
        return pagina

    def linhas_carrinho(self, pagina):
        return pagina.locator('#carrinho-corpo tr')


class VendaSoTecladoTestCase(PdvBase):
    def test_venda_completa_sem_mouse(self):
        """Critério 1: F2 → "vin" → ↓ → Enter → lote → qtd 2 → Enter → F9 → recibo."""
        pagina = self.entrar(self.novo_contexto())
        self.adicionar_pelo_teclado(pagina)

        # Um único lote: o foco já abre na quantidade (spec C2).
        expect(pagina.locator('#lote-qtd')).to_be_focused()
        pagina.keyboard.press('Control+A')
        pagina.keyboard.type('2')
        pagina.keyboard.press('Enter')

        expect(pagina.locator('#dialogo-lote')).not_to_be_visible()
        expect(self.linhas_carrinho(pagina)).to_have_count(1)
        expect(pagina.locator('#busca-produto')).to_be_focused()
        expect(pagina.locator('#resumo-total')).to_have_text('R$ 60,00')

        pagina.keyboard.press('F9')
        expect(pagina.locator('#recibo-titulo')).to_be_visible()
        expect(pagina.locator('#recibo-titulo')).to_be_focused()

        venda = Venda.objects.get()
        self.assertEqual(venda.total, Decimal('60.00'))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade, 3)

    def test_esc_fecha_lista_e_dialogo_devolvendo_o_foco(self):
        pagina = self.entrar(self.novo_contexto())
        pagina.keyboard.press('F2')
        pagina.keyboard.type('vin')
        expect(pagina.locator('#resultados-busca')).to_be_visible()
        pagina.keyboard.press('Escape')
        expect(pagina.locator('#resultados-busca')).to_be_hidden()
        expect(pagina.locator('#busca-produto')).to_have_attribute('aria-expanded', 'false')

        pagina.keyboard.type('h')              # o texto "vin" continua no campo
        expect(pagina.locator('#resultados-busca')).to_be_visible()
        pagina.keyboard.press('ArrowDown')
        pagina.keyboard.press('Enter')
        expect(pagina.locator('#dialogo-lote')).to_be_visible()
        pagina.keyboard.press('Escape')
        expect(pagina.locator('#dialogo-lote')).not_to_be_visible()
        expect(pagina.locator('#busca-produto')).to_be_focused()

    def test_esc_numa_segunda_abertura_nao_adiciona_nada(self):
        pagina = self.entrar(self.novo_contexto())
        self.adicionar_pelo_teclado(pagina)
        pagina.keyboard.press('Control+A')
        pagina.keyboard.type('1')
        pagina.keyboard.press('Enter')
        expect(self.linhas_carrinho(pagina)).to_have_count(1)
        expect(pagina.locator('#resumo-total')).to_have_text('R$ 30,00')

        self.adicionar_pelo_teclado(pagina)    # abre de novo, desiste com Esc
        pagina.keyboard.press('Escape')
        expect(pagina.locator('#dialogo-lote')).not_to_be_visible()
        expect(pagina.locator('#resumo-total')).to_have_text('R$ 30,00')

    def test_quantidade_maior_que_o_saldo_mostra_erro_sem_corrigir_o_valor(self):
        pagina = self.entrar(self.novo_contexto())
        self.adicionar_pelo_teclado(pagina)
        pagina.locator('#lote-qtd').fill('9')
        pagina.get_by_role('button', name='Adicionar ao carrinho').click()
        expect(pagina.locator('#lote-qtd-erro')).to_contain_text('saldo')
        expect(pagina.locator('#lote-qtd')).to_have_attribute('aria-invalid', 'true')
        expect(pagina.locator('#lote-qtd')).to_have_value('9')
        expect(pagina.locator('#dialogo-lote')).to_be_visible()

    def test_f9_com_dialogo_aberto_e_ignorado(self):
        pagina = self.entrar(self.novo_contexto())
        self.adicionar_pelo_teclado(pagina)
        pagina.keyboard.press('F9')
        self.assertEqual(Venda.objects.count(), 0)
        expect(pagina.locator('#dialogo-lote')).to_be_visible()

    def test_f9_com_carrinho_vazio_avisa_e_nao_cria_venda(self):
        pagina = self.entrar(self.novo_contexto())
        pagina.keyboard.press('F9')
        expect(pagina.locator('#anuncio-alerta')).to_contain_text('pelo menos um produto')
        self.assertEqual(Venda.objects.count(), 0)


class CarrinhoEFluxosTestCase(PdvBase):
    def adicionar_com_mouse(self, pagina, quantidade='2'):
        self.adicionar_pelo_teclado(pagina)
        pagina.locator('#lote-qtd').fill(quantidade)
        pagina.get_by_role('button', name='Adicionar ao carrinho').click()
        expect(self.linhas_carrinho(pagina)).to_have_count(1)

    def test_recarga_f5_restaura_o_carrinho(self):
        """Critério 4."""
        pagina = self.entrar(self.novo_contexto())
        self.adicionar_com_mouse(pagina)
        pagina.reload()
        expect(self.linhas_carrinho(pagina)).to_have_count(1)
        expect(pagina.locator('#resumo-total')).to_have_text('R$ 60,00')

    def test_conflito_de_estoque_entre_duas_abas(self):
        """Critério 3: uma aba recebe 201, a outra 409 com o carrinho intacto."""
        Lote.objects.filter(pk=self.lote.pk).update(quantidade=2)
        contexto = self.novo_contexto()
        aba_a = self.entrar(contexto)
        aba_b = contexto.new_page()
        aba_b.goto('/vendas/pdv/')
        self.adicionar_com_mouse(aba_a)
        self.adicionar_com_mouse(aba_b)

        aba_a.keyboard.press('F9')
        expect(aba_a.locator('#recibo-titulo')).to_be_visible()

        aba_b.keyboard.press('F9')
        expect(aba_b.locator('#anuncio-alerta')).to_contain_text('Estoque insuficiente')
        expect(self.linhas_carrinho(aba_b)).to_have_count(1)
        # Cor nunca é o único sinal (WCAG 1.4.1): a linha também diz o saldo.
        expect(self.linhas_carrinho(aba_b).first).to_contain_text('Dispon')
        self.assertEqual(Venda.objects.count(), 1)

    def test_sessao_expirada_leva_ao_login_e_o_carrinho_volta(self):
        """Critério 5."""
        contexto = self.novo_contexto()
        pagina = self.entrar(contexto)
        self.adicionar_com_mouse(pagina)

        # Sessão expirada no servidor, com os cookies ainda no navegador (o
        # cookie do CSRF dura mais que a sessão). Apagar os cookies daria 403.
        Session.objects.all().delete()
        pagina.keyboard.press('F9')
        pagina.wait_for_url('**/login/**')
        self.assertIn('next=', pagina.url)

        pagina.get_by_label('Nome de usuário').fill('operador')
        pagina.locator('#id_password').fill('senha12345')
        pagina.get_by_role('button', name='Entrar').click()
        pagina.wait_for_url('**/vendas/pdv/')
        expect(self.linhas_carrinho(pagina)).to_have_count(1)
        self.assertEqual(Venda.objects.count(), 0)

    def test_remover_item_devolve_o_foco_para_a_busca(self):
        pagina = self.entrar(self.novo_contexto())
        self.adicionar_com_mouse(pagina)
        pagina.get_by_role('button', name='Remover Vinho Tinto Seco do carrinho').click()
        expect(self.linhas_carrinho(pagina)).to_have_count(0)
        expect(pagina.locator('#carrinho-vazio')).to_be_visible()
        expect(pagina.locator('#busca-produto')).to_be_focused()

    def test_xss_nome_de_produto_aparece_como_texto(self):
        """Critério 7: busca, carrinho e recibo."""
        self.produto.nome = XSS
        self.produto.save()
        pagina = self.entrar(self.novo_contexto())

        pagina.keyboard.press('F2')
        pagina.keyboard.type('img')
        opcao = pagina.locator('#resultados-busca [role="option"]').first
        expect(opcao).to_contain_text(XSS)
        pagina.keyboard.press('ArrowDown')
        pagina.keyboard.press('Enter')
        expect(pagina.locator('#dialogo-lote')).to_be_visible()
        expect(pagina.locator('#lote-select')).not_to_have_attribute('aria-busy', 'true')
        pagina.get_by_role('button', name='Adicionar ao carrinho').click()

        linha = self.linhas_carrinho(pagina).first
        expect(linha).to_contain_text(XSS)
        pagina.keyboard.press('F9')
        expect(pagina.locator('#painel-recibo')).to_contain_text(XSS)

        self.assertIsNone(pagina.evaluate('window.__xss'))
        self.assertEqual(pagina.locator('img[src="x"]').count(), 0)

    def test_zoom_400_empilha_colunas_sem_rolagem_horizontal(self):
        """Critério 8: 400 % de zoom em 1280 px equivale a 320 px de largura."""
        pagina = self.entrar(self.novo_contexto(viewport={'width': 320, 'height': 256}))
        self.adicionar_com_mouse(pagina)
        rolagem = pagina.evaluate(
            'document.documentElement.scrollWidth - document.documentElement.clientWidth'
        )
        self.assertLessEqual(rolagem, 0, 'a página rola na horizontal a 320 px')
        botao = pagina.locator('#btn-finalizar')
        botao.scroll_into_view_if_needed()
        expect(botao).to_be_visible()
        caixa = botao.bounding_box()
        self.assertGreaterEqual(caixa['x'], 0)
        self.assertLessEqual(caixa['x'] + caixa['width'], 320)


class AxePdvTestCase(PdvBase):
    def test_axe_pdv_com_dialogo_fechado_e_aberto(self):
        """Critério 6: zero violações serious/critical nos dois estados."""
        pagina = self.entrar(self.novo_contexto())
        fechado = self.violacoes_axe(pagina)
        self.assertEqual(fechado, [], self.resumir(fechado))

        self.adicionar_pelo_teclado(pagina)
        aberto = self.violacoes_axe(pagina)
        self.assertEqual(aberto, [], self.resumir(aberto))

    def test_axe_pdv_com_carrinho_e_recibo(self):
        pagina = self.entrar(self.novo_contexto())
        self.adicionar_pelo_teclado(pagina)
        pagina.get_by_role('button', name='Adicionar ao carrinho').click()
        expect(self.linhas_carrinho(pagina)).to_have_count(1)
        com_item = self.violacoes_axe(pagina)
        self.assertEqual(com_item, [], self.resumir(com_item))

        pagina.keyboard.press('F9')
        expect(pagina.locator('#recibo-titulo')).to_be_visible()
        com_recibo = self.violacoes_axe(pagina)
        self.assertEqual(com_recibo, [], self.resumir(com_recibo))
