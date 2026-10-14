"""
Testes de autenticação e gestão de usuários (core/forms.py, core/views.py).
Ver docs/projeto_django_spec.md §2.2 e §3.1.
"""
from django.test import TestCase
from django.urls import reverse

from core.forms import UsuarioCriarForm, UsuarioEditarForm
from core.models import Usuario


class LoginTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(nome='caixa', senha='senha123')

    def test_login_valido_redireciona_para_painel(self):
        resposta = self.client.post(
            reverse('core:login'), {'username': 'caixa', 'password': 'senha123'}
        )
        self.assertRedirects(resposta, reverse('core:painel'))

    def test_senha_errada_nao_autentica(self):
        resposta = self.client.post(
            reverse('core:login'), {'username': 'caixa', 'password': 'errada'}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_usuario_inativo_nao_autentica(self):
        self.usuario.ativo = False
        self.usuario.save()
        resposta = self.client.post(
            reverse('core:login'), {'username': 'caixa', 'password': 'senha123'}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_exige_post(self):
        self.client.login(username='caixa', password='senha123')
        self.assertEqual(self.client.get(reverse('core:logout')).status_code, 405)
        resposta = self.client.post(reverse('core:logout'))
        self.assertRedirects(resposta, reverse('core:login'))

    def test_raiz_redireciona_para_painel(self):
        self.client.login(username='caixa', password='senha123')
        resposta = self.client.get(reverse('core:inicio'))
        self.assertRedirects(resposta, reverse('core:painel'))


class UsuarioModelTestCase(TestCase):
    def test_perfil_admin(self):
        admin = Usuario.objects.create_user(nome='a', senha='senha123', perfil='admin')
        operador = Usuario.objects.create_user(nome='o', senha='senha123')
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_staff)
        self.assertFalse(operador.is_admin)
        self.assertFalse(operador.is_staff)

    def test_is_active_reflete_campo_ativo(self):
        usuario = Usuario.objects.create_user(nome='u', senha='senha123', ativo=False)
        self.assertFalse(usuario.is_active)

    def test_senha_nunca_fica_em_texto_puro(self):
        usuario = Usuario.objects.create_user(nome='u', senha='senha123')
        self.assertNotEqual(usuario.password, 'senha123')
        self.assertTrue(usuario.check_password('senha123'))


class UsuarioCriarFormTestCase(TestCase):
    def dados(self, **extra):
        base = {'nome': 'novo', 'perfil': 'operador', 'ativo': 'on',
                'senha': 'senha123', 'confirmar_senha': 'senha123'}
        base.update(extra)
        return base

    def test_form_valido_grava_senha_com_hash(self):
        form = UsuarioCriarForm(self.dados())
        self.assertTrue(form.is_valid(), form.errors)
        usuario = form.save()
        self.assertTrue(usuario.check_password('senha123'))

    def test_nome_duplicado_ignora_maiusculas(self):
        Usuario.objects.create_user(nome='Maria', senha='senha123')
        form = UsuarioCriarForm(self.dados(nome='maria'))
        self.assertFalse(form.is_valid())
        self.assertIn('nome', form.errors)

    def test_senhas_diferentes(self):
        form = UsuarioCriarForm(self.dados(confirmar_senha='outra123'))
        self.assertFalse(form.is_valid())
        self.assertIn('confirmar_senha', form.errors)

    def test_senha_curta_rejeitada(self):
        form = UsuarioCriarForm(self.dados(senha='123', confirmar_senha='123'))
        self.assertFalse(form.is_valid())
        self.assertIn('senha', form.errors)

    def test_campo_com_erro_recebe_atributos_aria(self):
        form = UsuarioCriarForm(self.dados(senha='123', confirmar_senha='123'))
        form.is_valid()
        # AcessivelMixin (WCAG 3.3.1): campo inválido liga ao id do erro.
        attrs = form.fields['senha'].widget.attrs
        self.assertEqual(attrs.get('aria-invalid'), 'true')
        self.assertIn('id_senha-erro', attrs.get('aria-describedby', ''))


class UsuarioEditarFormTestCase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        self.outro = Usuario.objects.create_user(nome='outro', senha='senha123')

    def dados(self, usuario, **extra):
        base = {'nome': usuario.nome, 'perfil': usuario.perfil, 'ativo': 'on',
                'senha': '', 'confirmar_senha': ''}
        base.update(extra)
        return base

    def test_senha_em_branco_mantem_a_atual(self):
        form = UsuarioEditarForm(self.dados(self.outro), instance=self.outro,
                                 usuario_logado=self.admin)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.outro.refresh_from_db()
        self.assertTrue(self.outro.check_password('senha123'))

    def test_nova_senha_e_aplicada(self):
        form = UsuarioEditarForm(
            self.dados(self.outro, senha='nova1234', confirmar_senha='nova1234'),
            instance=self.outro, usuario_logado=self.admin,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.outro.refresh_from_db()
        self.assertTrue(self.outro.check_password('nova1234'))

    def test_admin_nao_pode_remover_o_proprio_perfil(self):
        form = UsuarioEditarForm(self.dados(self.admin, perfil='operador'),
                                 instance=self.admin, usuario_logado=self.admin)
        self.assertFalse(form.is_valid())
        self.assertIn('perfil', form.errors)

    def test_admin_nao_pode_desativar_a_propria_conta(self):
        dados = self.dados(self.admin)
        del dados['ativo']
        form = UsuarioEditarForm(dados, instance=self.admin, usuario_logado=self.admin)
        self.assertFalse(form.is_valid())
        self.assertIn('ativo', form.errors)

    def test_nome_de_outro_usuario_rejeitado(self):
        form = UsuarioEditarForm(self.dados(self.outro, nome='ADMIN'), instance=self.outro,
                                 usuario_logado=self.admin)
        self.assertFalse(form.is_valid())
        self.assertIn('nome', form.errors)


class UsuarioViewsTestCase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        self.outro = Usuario.objects.create_user(nome='outro', senha='senha123')
        self.client.login(username='admin', password='senha123')

    def test_lista_mostra_os_usuarios(self):
        resposta = self.client.get(reverse('core:usuario_lista'))
        self.assertContains(resposta, 'outro')

    def test_criar_usuario(self):
        resposta = self.client.post(reverse('core:usuario_criar'), {
            'nome': 'novo', 'perfil': 'operador', 'ativo': 'on',
            'senha': 'senha123', 'confirmar_senha': 'senha123',
        })
        self.assertRedirects(resposta, reverse('core:usuario_lista'))
        self.assertTrue(Usuario.objects.filter(nome='novo').exists())

    def test_criar_usuario_invalido_reexibe_formulario(self):
        resposta = self.client.post(reverse('core:usuario_criar'), {
            'nome': '', 'perfil': 'operador', 'senha': 'x', 'confirmar_senha': 'y',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Usuario.objects.count(), 2)

    def test_alternar_desativa_e_reativa(self):
        url = reverse('core:usuario_alternar', args=[self.outro.pk])
        self.client.post(url)
        self.outro.refresh_from_db()
        self.assertFalse(self.outro.ativo)
        self.client.post(url)
        self.outro.refresh_from_db()
        self.assertTrue(self.outro.ativo)

    def test_alternar_exige_post(self):
        resposta = self.client.get(reverse('core:usuario_alternar', args=[self.outro.pk]))
        self.assertEqual(resposta.status_code, 405)

    def test_nao_desativa_a_propria_conta(self):
        self.client.post(reverse('core:usuario_alternar', args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.ativo)
