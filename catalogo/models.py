"""
Categorias e produtos do Empório BR. Ver docs/projeto_django_spec.md §2.3.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce, Lower

DUAS_CASAS = Decimal('0.01')


class Categoria(models.Model):
    nome = models.CharField(max_length=80)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'categorias'
        ordering = ['nome']
        constraints = [
            # "Cervejas" e "cervejas" não podem coexistir (no Flask a checagem diferencia maiúsculas).
            models.UniqueConstraint(Lower('nome'), name='categoria_nome_unico_ci'),
        ]

    def __str__(self):
        return self.nome


class ProdutoQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)

    def com_estoque(self):
        """Anota `estoque_total` com uma única query (evita o N+1 de Produto.estoque_atual)."""
        return self.annotate(estoque_total=Coalesce(Sum('lotes__quantidade'), 0))

    def abaixo_do_minimo(self):
        return self.com_estoque().filter(estoque_total__lte=F('estoque_minimo'))

    def buscar(self, termo):
        return self.filter(
            Q(nome__icontains=termo)
            | Q(fabricante__icontains=termo)
            | Q(codigo_barras__icontains=termo)
        )


class Produto(models.Model):
    nome = models.CharField(max_length=150)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='produtos')
    fabricante = models.CharField(max_length=100, blank=True)
    volume = models.CharField(max_length=30, blank=True)
    peso = models.CharField(max_length=30, blank=True)
    # null=True (e não '') para que vários produtos sem código não violem o UNIQUE.
    codigo_barras = models.CharField(max_length=50, unique=True, null=True, blank=True)

    margem_lucro = models.DecimalField(
        'margem de lucro (%)', max_digits=6, decimal_places=2, default=Decimal('30.00'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    preco_custo = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=False)

    estoque_minimo = models.PositiveIntegerField(default=5)
    estoque_maximo = models.PositiveIntegerField(default=100)
    ativo = models.BooleanField(default=True)

    objects = ProdutoQuerySet.as_manager()

    class Meta:
        db_table = 'produtos'
        ordering = ['nome']
        indexes = [models.Index(fields=['ativo', 'nome'])]
        constraints = [
            models.CheckConstraint(
                condition=Q(estoque_maximo__gte=F('estoque_minimo')),
                name='produto_estoque_max_gte_min',
            ),
            models.CheckConstraint(condition=Q(preco_custo__gte=0), name='produto_preco_custo_nao_negativo'),
            models.CheckConstraint(condition=Q(margem_lucro__gte=0), name='produto_margem_nao_negativa'),
        ]

    def __str__(self):
        return self.nome

    def calcular_preco_venda(self):
        self.preco_venda = (self.preco_custo * (1 + self.margem_lucro / 100)).quantize(
            DUAS_CASAS, rounding=ROUND_HALF_UP
        )

    def save(self, *args, **kwargs):
        self.calcular_preco_venda()
        super().save(*args, **kwargs)

    @property
    def estoque_atual(self):
        """Usa a anotação de com_estoque() quando disponível; senão faz 1 query agregada."""
        if hasattr(self, 'estoque_total'):
            return self.estoque_total
        return self.lotes.aggregate(total=Coalesce(Sum('quantidade'), 0))['total']

    @property
    def estoque_baixo(self):
        return self.estoque_atual <= self.estoque_minimo
