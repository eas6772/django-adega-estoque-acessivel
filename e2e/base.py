"""
Infraestrutura dos testes e2e: servidor Django real (StaticLiveServerTestCase)
+ Chromium headless via Playwright. Roda com o runner do Django:

    python manage.py test e2e --keepdb

Requer `pip install -e ".[dev]"` e `playwright install chromium`.
"""
import os

# O Playwright (sync API) mantém um event loop ativo na thread do teste, e o
# ORM do Django recusa consultas "dentro de um loop assíncrono". Só afeta
# estes testes: o acesso ao banco aqui é sempre síncrono e de uma thread.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

from axe_playwright_python.sync_playwright import Axe  # noqa: E402
from django.contrib.staticfiles.testing import StaticLiveServerTestCase  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from core.models import Usuario  # noqa: E402

SENHA = 'senha12345'
TAGS_WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']


class NavegadorTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._playwright.stop()
        super().tearDownClass()

    def setUp(self):
        self.admin = Usuario.objects.create_user(nome='admin', senha=SENHA, perfil='admin')
        self.operador = Usuario.objects.create_user(nome='operador', senha=SENHA)

    def novo_contexto(self, **opcoes):
        opcoes.setdefault('locale', 'pt-BR')
        opcoes.setdefault('base_url', self.live_server_url)
        contexto = self._browser.new_context(**opcoes)
        # O CSS de ícones vem de um CDN. Os ícones são aria-hidden, então
        # bloquear a rede externa deixa o teste rápido e determinístico.
        contexto.route('https://cdn.jsdelivr.net/**', lambda rota: rota.abort())
        contexto.set_default_timeout(10_000)
        self.addCleanup(contexto.close)
        return contexto

    def entrar(self, contexto, nome='operador', destino='/vendas/pdv/'):
        """Faz login pela tela real e devolve a página já em `destino`."""
        pagina = contexto.new_page()
        pagina.goto(f'/login/?next={destino}')
        pagina.get_by_label('Nome de usuário').fill(nome)
        pagina.locator('#id_password').fill(SENHA)
        pagina.get_by_role('button', name='Entrar').click()
        pagina.wait_for_url(f'**{destino}')
        return pagina

    def violacoes_axe(self, pagina, graves=('serious', 'critical')):
        resultado = Axe().run(pagina, options={
            'runOnly': {'type': 'tag', 'values': TAGS_WCAG},
            'resultTypes': ['violations'],
        })
        return [v for v in resultado.response['violations'] if v['impact'] in graves]

    @staticmethod
    def resumir(violacoes):
        return '\n'.join(
            f"[{v['impact']}] {v['id']}: {v['help']} "
            f"({len(v['nodes'])} nó(s)) ex.: {v['nodes'][0]['html'][:140]}"
            for v in violacoes
        )
