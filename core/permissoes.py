"""
Regras de permissão do Empório BR — um único mecanismo de "somente admin"
para toda a aplicação (corrige o bug #11: o Flask tinha três implementações
inconsistentes de admin-only, com comportamentos diferentes entre elas).

Ver docs/planejamento_views.md §4 e docs/projeto_django_spec.md §3 (legenda
🔓 público · 👤 logado · 🔑 admin).
"""
from functools import wraps

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from urllib.parse import urlsplit


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """CBV: exige login (redirect ao login) e depois perfil admin (403)."""

    def test_func(self):
        return self.request.user.is_admin


def admin_required(view):
    """FBV: mesma regra do mixin acima, para views baseadas em função."""

    @wraps(view)
    def _view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return _view


def _pagina_de_origem(request):
    """
    Para onde voltar depois do login: a PÁGINA que fez o fetch (Referer do
    mesmo host), não a URL da API. Voltar para /vendas/api/vendas/ levaria o
    caixa a uma rota só-POST (405). Sem Referer válido, cai na URL da requisição.
    """
    referer = request.META.get('HTTP_REFERER', '')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        partes = urlsplit(referer)
        return partes.path + (f'?{partes.query}' if partes.query else '')
    return request.get_full_path()


def login_required_json(view):
    """
    Para endpoints JSON (vendas/api.py, estoque/api.py).

    Nunca redireciona: a sessão expirar no meio do PDV precisa devolver 401 em
    JSON para o `fetch` tratar (docs/projeto_django_spec.md §3.2) — nunca um
    302 para o HTML de login, que o fetch seguiria silenciosamente.

    A view também precisa do decorator nativo `login_not_required` por fora
    deste, senão o LoginRequiredMiddleware intercepta a requisição antes desta
    função rodar e faz o redirect que este decorator existe para evitar.
    """

    @wraps(view)
    def _view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = resolve_url(settings.LOGIN_URL)
            proximo = urlencode({'next': _pagina_de_origem(request)})
            return JsonResponse(
                {'erro': 'Sessão expirada.', 'login_url': f'{login_url}?{proximo}'},
                status=401,
            )
        return view(request, *args, **kwargs)

    return _view
