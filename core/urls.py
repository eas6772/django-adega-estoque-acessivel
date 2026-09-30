from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'core'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='core:painel'), name='inicio'),
    path(
        'login/',
        login_not_required(LoginView.as_view(redirect_authenticated_user=True)),
        name='login',
    ),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('painel/', views.PainelView.as_view(), name='painel'),
    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_lista'),
    path('usuarios/novo/', views.UsuarioCreateView.as_view(), name='usuario_criar'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_editar'),
    path('usuarios/<int:pk>/alternar/', views.UsuarioAlternarView.as_view(), name='usuario_alternar'),
]
