"""
Vendas e itens de venda do Empório BR. Ver docs/projeto_django_spec.md §2.6 e §2.7.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from catalogo.models import Produto
from estoque.models import Lote


class Venda(models.Model):
    data = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vendas')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        db_table = 'vendas'
        ordering = ['-data']
        indexes = [models.Index(fields=['-data'])]

    def __str__(self):
        return f'Venda #{self.pk} | R$ {self.total}'

    def recalcular_total(self):
        self.total = self.itens.aggregate(t=Coalesce(Sum('subtotal'), Decimal('0.00')))['t']
        return self.total


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_venda')
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, null=True, blank=True, related_name='itens_venda')
    quantidade = models.PositiveIntegerField()
    # Preços congelados no momento da venda: alterar o cadastro do produto não reescreve o histórico.
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    # Custo congelado: o relatório de lucro não deve usar Produto.preco_custo ATUAL,
    # o que distorceria o lucro de vendas antigas quando o custo do produto mudar.
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    # Coluna calculada pelo PostgreSQL; permite Sum('subtotal') direto nos relatórios.
    subtotal = models.GeneratedField(
        expression=F('quantidade') * F('preco_unitario'),
        output_field=models.DecimalField(max_digits=12, decimal_places=2),
        db_persist=True,
    )

    class Meta:
        db_table = 'itens_venda'
        verbose_name = 'item de venda'
        verbose_name_plural = 'itens de venda'
        constraints = [
            models.CheckConstraint(condition=Q(quantidade__gt=0), name='item_venda_quantidade_positiva'),
        ]

    def __str__(self):
        return f'Venda #{self.venda_id} · {self.produto} x{self.quantidade}'
