"""
Formulários de core: mixin de acessibilidade compartilhado por todos os apps
e os formulários de gestão de usuário. Ver docs/melhorias_acessibilidade.md
§3.2 (AcessivelMixin) e docs/planejamento_views.md §2 (regras de usuário).
"""
from django import forms
from django.contrib.auth import password_validation

from .models import Usuario


class AcessivelMixin:
    """
    Liga help_text/erros de cada campo ao widget via aria-describedby e marca
    aria-invalid quando o campo tem erro — para os templates da Etapa 3
    poderem só referenciar esses IDs, sem repetir essa lógica em cada form.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            ids = []
            if campo.help_text:
                ids.append(f'id_{nome}-dica')
            if self.is_bound and nome in self.errors:
                campo.widget.attrs['aria-invalid'] = 'true'
                ids.append(f'id_{nome}-erro')
            if ids:
                campo.widget.attrs['aria-describedby'] = ' '.join(ids)


class UsuarioCriarForm(AcessivelMixin, forms.ModelForm):
    senha = forms.CharField(
        label='Senha', widget=forms.PasswordInput, help_text='Mínimo de 6 caracteres.',
    )
    confirmar_senha = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ['nome', 'perfil', 'ativo']

    def clean_nome(self):
        nome = self.cleaned_data['nome']
        if Usuario.objects.filter(nome__iexact=nome).exists():
            raise forms.ValidationError('Já existe um usuário com este nome.')
        return nome

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get('senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')
        if senha and confirmar_senha and senha != confirmar_senha:
            self.add_error('confirmar_senha', 'As senhas não coincidem.')
        if senha:
            try:
                password_validation.validate_password(senha)
            except forms.ValidationError as erro:
                self.add_error('senha', erro)
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['senha'])
        if commit:
            usuario.save()
        return usuario


class UsuarioEditarForm(AcessivelMixin, forms.ModelForm):
    senha = forms.CharField(
        label='Nova senha', widget=forms.PasswordInput, required=False,
        help_text='Deixe em branco para manter a senha atual.',
    )
    confirmar_senha = forms.CharField(
        label='Confirmar nova senha', widget=forms.PasswordInput, required=False,
    )

    class Meta:
        model = Usuario
        fields = ['nome', 'perfil', 'ativo']

    def __init__(self, *args, usuario_logado=None, **kwargs):
        self.usuario_logado = usuario_logado
        super().__init__(*args, **kwargs)

    def clean_nome(self):
        nome = self.cleaned_data['nome']
        if Usuario.objects.filter(nome__iexact=nome).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Já existe um usuário com este nome.')
        return nome

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get('senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')
        if senha and confirmar_senha and senha != confirmar_senha:
            self.add_error('confirmar_senha', 'As senhas não coincidem.')
        if senha:
            try:
                password_validation.validate_password(senha)
            except forms.ValidationError as erro:
                self.add_error('senha', erro)

        if self.usuario_logado is not None and self.instance.pk == self.usuario_logado.pk:
            if cleaned_data.get('perfil') != Usuario.Perfil.ADMIN:
                self.add_error('perfil', 'Você não pode remover seu próprio perfil de administrador.')
            if not cleaned_data.get('ativo'):
                self.add_error('ativo', 'Você não pode desativar sua própria conta.')
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        senha = self.cleaned_data.get('senha')
        if senha:
            usuario.set_password(senha)
        if commit:
            usuario.save()
        return usuario
