"""
Modelos Django do Empório BR — migração de estoque_app/app/models/models.py (Flask/SQLAlchemy).

Alvo: Django >= 5.2 + PostgreSQL >= 14 (psycopg 3).

Mapa Flask -> Django
-------------------
  usuarios       -> Usuario        (modelo de usuário customizado: AUTH_USER_MODEL = 'novo_app.Usuario')
  categorias     -> Categoria
  produtos       -> Produto
  lotes          -> Lote
  movimentacoes  -> Movimentacao   (+ FK opcional para Venda)
  vendas         -> Venda
  itens_venda    -> ItemVenda      (+ custo_unitario congelado, subtotal gerado no banco)

Principais decisões
-------------------
* Dinheiro: db.Float -> DecimalField (NUMERIC no PostgreSQL). Float acumula erro de
  arredondamento em somas de relatórios (ex.: 0.1 + 0.2 != 0.3).
* Quantidades: PositiveIntegerField onde o valor nunca pode ser negativo (o Django cria
  CHECK >= 0 no PostgreSQL). Movimentacao.quantidade continua IntegerField porque
  ajustes gravam a diferença, que pode ser negativa.
* Exclusão: PROTECT em tudo que tem valor de auditoria (produto, lote, usuário).
  O sistema já trabalha com "desativar" (campo ativo) em vez de apagar.
* db_table mantém os nomes das tabelas do Flask, facilitando o script de carga dos dados.
* Datas: default=timezone.now (aware). Configurar TIME_ZONE='America/Sao_Paulo' e USE_TZ=True.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone

DUAS_CASAS = Decimal('0.01')


# ── Usuários ────────────────────────────────────────────────


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
    """Substitui Usuario(UserMixin) + Flask-Login.

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
    # do Django (128) não comporta. Ver WerkzeugScryptHasher em planejamento_views.md.
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


# ── Catálogo ────────────────────────────────────────────────


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
        """Anota `estoque_total` com uma única query (evita o N+1 de Produto.estoque_atual no Flask)."""
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
        # No Flask o cálculo era chamado manualmente em _produto_do_form; aqui é garantido.
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


# ── Estoque ─────────────────────────────────────────────────


class LoteQuerySet(models.QuerySet):
    def vendaveis(self):
        """Lotes com saldo e não vencidos, em ordem PEPS (validade mais próxima primeiro,
        lotes sem validade por último). Equivale a lotes_peps() / lotes_produto() do Flask."""
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
        """True se vence em até 30 dias (era `proximos_vencimento` no Flask)."""
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
    # Novo: no Flask a ligação com a venda existia só no texto do motivo ("Venda #12").
    venda = models.ForeignKey(
        'Venda', on_delete=models.PROTECT, null=True, blank=True, related_name='movimentacoes'
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


# ── Vendas ──────────────────────────────────────────────────


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
    # Novo: o relatório de lucro do Flask usa Produto.preco_custo ATUAL, distorcendo vendas antigas.
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
