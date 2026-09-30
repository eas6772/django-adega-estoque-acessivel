"""
Utilitários de template compartilhados por todos os apps: ícone decorativo,
formatação monetária em pt-BR e o ícone correspondente a cada nível de
mensagem. Usados pelos templates da Etapa 3.
"""
from decimal import Decimal, InvalidOperation

from django import template
from django.utils.formats import number_format
from django.utils.safestring import mark_safe

register = template.Library()

_ICONES_POR_TAG = {
    'success': 'check-circle-fill',
    'info': 'info-circle-fill',
    'danger': 'exclamation-triangle-fill',
    'warning': 'exclamation-triangle-fill',
}


@register.simple_tag
def icone(nome, classe_extra=''):
    """
    Ícone puramente decorativo (aria-hidden). `nome`/`classe_extra` nunca
    vêm de dado do usuário — só de literais escritos no próprio template —
    por isso é seguro montar o HTML diretamente aqui.
    """
    return mark_safe(f'<i class="bi bi-{nome} {classe_extra}" aria-hidden="true"></i>')


@register.filter(name='brl')
def brl(valor):
    """Formata um valor monetário como 'R$ 1.234,56' (pt-BR)."""
    try:
        valor_decimal = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return ''
    return f'R$ {number_format(valor_decimal, decimal_pos=2)}'


@register.filter(name='icone_mensagem')
def icone_mensagem(tag_mensagem):
    """Nome do ícone Bootstrap Icons correspondente à tag de
    django.contrib.messages (já convertida por MESSAGE_TAGS)."""
    return _ICONES_POR_TAG.get(tag_mensagem, 'info-circle-fill')
