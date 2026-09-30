import functools

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UsuarioCriarForm, UsuarioEditarForm
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Não reaproveita UserCreationForm/UserChangeForm nativos: ambos são ligados
    hard-coded ao modelo auth.User (campo `username`), incompatíveis com
    Usuario (USERNAME_FIELD='nome'). Por isso usamos os forms próprios.
    """

    add_form = UsuarioCriarForm
    form = UsuarioEditarForm
    model = Usuario
    list_display = ('nome', 'perfil', 'ativo', 'last_login')
    list_filter = ('perfil', 'ativo')
    search_fields = ('nome',)
    ordering = ('nome',)
    filter_horizontal = ()
    fieldsets = ((None, {'fields': ('nome', 'password', 'perfil', 'ativo')}),)
    add_fieldsets = ((None, {'fields': ('nome', 'perfil', 'ativo', 'senha', 'confirmar_senha')}),)

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)
        if obj is None:
            # add_form (UsuarioCriarForm) não aceita usuario_logado.
            return FormClass
        return functools.partial(FormClass, usuario_logado=request.user)
