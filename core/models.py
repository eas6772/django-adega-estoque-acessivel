"""
Usuário customizado do Empório BR.

Substitui Usuario(UserMixin) + Flask-Login do sistema original
(estoque_app/app/models/models.py). Ver docs/projeto_django_spec.md §2.2.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, nome, senha=None, perfil='operador', **extra):
        if not nome:
            raise ValueError('O nome de usuário é obrigatório.')
        usuario = self.model(nome=nome, perfil=perfil, **extra)
        usuario.set_password(senha)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, nome, senha=None, **extra):
        return self.create_user(nome, senha, perfil=Usuario.Perfil.ADMIN, **extra)


class Usuario(AbstractBaseUser):
    """
    - set_senha()/verificar_senha() -> set_password()/check_password() herdados.
    - senha_hash -> campo `password` herdado (ampliado para 255, ver abaixo).
    """

    class Perfil(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        OPERADOR = 'operador', 'Operador'

    nome = models.CharField('nome de usuário', max_length=100, unique=True)
    perfil = models.CharField(max_length=20, choices=Perfil.choices, default=Perfil.OPERADOR)
    ativo = models.BooleanField(default=True)

    # Hashes scrypt do Werkzeug importados do Flask têm ~180 caracteres; o padrão
    # do Django (128) não comporta. Ver core/hashers.py.
    password = models.CharField('senha', max_length=255)

    objects = UsuarioManager()

    USERNAME_FIELD = 'nome'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'usuarios'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def is_admin(self):
        return self.perfil == self.Perfil.ADMIN

    # O ModelBackend consulta is_active para bloquear login de usuários desativados.
    @property
    def is_active(self):
        return self.ativo

    # Necessários apenas para liberar o Django Admin ao perfil admin.
    @property
    def is_staff(self):
        return self.is_admin

    def has_perm(self, perm, obj=None):
        return self.ativo and self.is_admin

    def has_module_perms(self, app_label):
        return self.ativo and self.is_admin
