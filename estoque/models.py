"""
Lotes e movimentações de estoque do Empório BR. Ver docs/projeto_django_spec.md §2.4 e §2.5.

`Movimentacao.venda` referencia 'vendas.Venda' por string: a dependência entre
estoque <-> vendas é circular (vendas/servicos.py importa de estoque.models, mas
estoque nunca importa de vendas em nível de módulo). O makemigrations resolve
isso sozinho, gerando estoque/0001_initial + estoque/0002_initial.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from catalogo.models import Produto


class LoteQuerySet(models.QuerySet):
    def vendaveis(self):
        """Lotes com saldo e não vencidos, em ordem PEPS (validade mais próxima primeiro,
        lotes sem validade por último)."""
        hoje = timezone.localdate()
        return (
            self.filter(quantidade__gt=0)
            .filter(Q(data_validade__isnull=True) | Q(data_validade__gte=hoje))
            .order_by(F('data_validade').asc(nulls_last=True), 'id')
        )

    def vencendo_em(self, dias=30):
        hoje = timezone.localdate()
        return self.filter(
            quantidade__gt=0,
            data_validade__gte=hoje,
            data_validade__lte=hoje + timedelta(days=dias),
        ).order_by('data_validade')


class Lote(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='lotes')
    numero_lote = models.CharField('número do lote', max_length=60, blank=True)
    quantidade = models.PositiveIntegerField(default=0)
    data_validade = models.DateField(null=True, blank=True)
    data_entrada = models.DateTimeField(default=timezone.now)

    objects = LoteQuerySet.as_manager()

    class Meta:
        db_table = 'lotes'
        ordering = ['data_validade', 'id']
        indexes = [models.Index(fields=['produto', 'data_validade'])]

    def __str__(self):
        codigo = f' [{self.numero_lote}]' if self.numero_lote else ''
        return f'Lote #{self.pk}{codigo} — {self.produto}'

    @property
    def vencido(self):
        return self.data_validade is not None and self.data_validade < timezone.localdate()

    @property
    def proximo_vencimento(self):
        """True se vence em até 30 dias."""
        if self.data_validade is None:
            return False
        return 0 <= (self.data_validade - timezone.localdate()).days <= 30


class Movimentacao(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SAIDA = 'saida', 'Saída'
        AJUSTE = 'ajuste', 'Ajuste'

    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='movimentacoes')
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, null=True, blank=True, related_name='movimentacoes')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    # Pode ser negativo: ajustes gravam a diferença (nova_qtd - qtd_anterior).
    quantidade = models.IntegerField()
    data = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='movimentacoes')
    motivo = models.CharField(max_length=200, blank=True)
    # A ligação com a venda existe de fato (FK), não só no texto do motivo.
    venda = models.ForeignKey(
        'vendas.Venda', on_delete=models.PROTECT, null=True, blank=True, related_name='movimentacoes'
    )

    class Meta:
        db_table = 'movimentacoes'
        ordering = ['-data']
        verbose_name = 'movimentação'
        verbose_name_plural = 'movimentações'
        indexes = [
            models.Index(fields=['-data']),
            models.Index(fields=['tipo', '-data']),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} | {self.quantidade}'
