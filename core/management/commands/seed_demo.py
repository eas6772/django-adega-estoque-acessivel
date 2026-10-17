"""
Carrega dados de demonstração (usuários, catálogo, estoque e algumas vendas).

Idempotente: se já existirem produtos, não cria nada (use --forcar para recriar o
catálogo que faltar). Passa pelos serviços do app (registrar_entrada/registrar_venda),
então movimentações e vendas ficam coerentes com o que o sistema gera de verdade.

Senhas: --senha-admin/--senha-caixa ou as variáveis DEMO_ADMIN_SENHA/DEMO_CAIXA_SENHA.
Só são exigidas quando o usuário ainda não existe; senhas de usuários existentes não mudam.
"""
import os
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque.servicos import registrar_entrada
from vendas.servicos import registrar_venda

CATEGORIAS = ['Cervejas', 'Destilados', 'Petiscos', 'Refrigerantes', 'Sucos', 'Tabacaria', 'Vinhos']

# nome, categoria, fabricante, código de barras, custo, margem %, mínimo, máximo
PRODUTOS = [
    ('Amendoim Torrado', 'Petiscos', 'Dori', None, '4.00', '29.99', 10, 80),
    ('Cerveja IPA Long Neck', 'Cervejas', 'Colorado', '7891000000042', '7.50', '30.00', 12, 96),
    ('Cerveja Pilsen Lata', 'Cervejas', 'Brahma', '7891000000035', '3.00', '30.00', 24, 240),
    ('Gin London Dry', 'Destilados', 'Tanqueray', '7891000000066', '95.00', '24.97', 2, 15),
    ('Queijo Provolone', 'Petiscos', 'Tirolez', None, '18.00', '30.00', 3, 20),
    ('Vinho Branco Suave', 'Vinhos', 'Salton', '7891000000028', '22.00', '30.00', 5, 50),
    ('Vinho Tinto Seco', 'Vinhos', 'Aurora', '7891000000011', '24.98', '30.00', 5, 60),
    ('Whisky 12 anos', 'Destilados', 'Johnnie', '7891000000059', '120.00', '40.00', 3, 20),
]

# produto, nº do lote, quantidade, validade em dias a partir de hoje (None = sem validade).
# O Gin não tem lote (estoque zerado), o Vinho Branco e o Provolone ficam abaixo do mínimo
# e vencendo, para a Home e os relatórios mostrarem alertas.
LOTES = [
    ('Amendoim Torrado', 'A5', 25, 118),
    ('Cerveja IPA Long Neck', '4568904', 45, 320),
    ('Cerveja Pilsen Lata', 'C01', 100, 88),
    ('Queijo Provolone', 'Q9', 5, 13),
    ('Vinho Branco Suave', 'B100', 3, 10),
    ('Vinho Tinto Seco', 'L2409A', 3, 18),
    ('Vinho Tinto Seco', 'L2501B', 12, 200),
    ('Whisky 12 anos', 'W12', 6, None),
]

# usuário que vende, [(produto, nº do lote, quantidade)]
VENDAS = [
    ('caixa', [('Cerveja Pilsen Lata', 'C01', 4), ('Amendoim Torrado', 'A5', 1)]),
    ('caixa', [('Vinho Tinto Seco', 'L2501B', 1)]),
    ('admin', [('Whisky 12 anos', 'W12', 1), ('Cerveja Pilsen Lata', 'C01', 3)]),
]


class Command(BaseCommand):
    help = 'Carrega dados de demonstração (usuários, catálogo, estoque e vendas).'

    def add_arguments(self, parser):
        parser.add_argument('--senha-admin', help='Senha do usuário "admin" (ou DEMO_ADMIN_SENHA).')
        parser.add_argument('--senha-caixa', help='Senha do usuário "caixa" (ou DEMO_CAIXA_SENHA).')
        parser.add_argument('--forcar', action='store_true',
                            help='Carrega o catálogo mesmo que já existam produtos.')

    @transaction.atomic
    def handle(self, *args, **opcoes):
        admin = self._usuario('admin', Usuario.Perfil.ADMIN, opcoes['senha_admin'], 'DEMO_ADMIN_SENHA')
        caixa = self._usuario('caixa', Usuario.Perfil.OPERADOR, opcoes['senha_caixa'], 'DEMO_CAIXA_SENHA')

        if Produto.objects.exists() and not opcoes['forcar']:
            self.stdout.write('Já existem produtos: dados de demonstração não recarregados (use --forcar).')
            return

        categorias = {nome: Categoria.objects.get_or_create(nome=nome)[0] for nome in CATEGORIAS}
        produtos = {}
        for nome, categoria, fabricante, codigo, custo, margem, minimo, maximo in PRODUTOS:
            produtos[nome] = Produto.objects.get_or_create(
                nome=nome,
                defaults=dict(
                    categoria=categorias[categoria], fabricante=fabricante, codigo_barras=codigo,
                    preco_custo=Decimal(custo), margem_lucro=Decimal(margem),
                    estoque_minimo=minimo, estoque_maximo=maximo,
                ),
            )[0]

        hoje = timezone.localdate()
        lotes = {}
        for nome, numero, quantidade, dias in LOTES:
            validade = hoje + timedelta(days=dias) if dias is not None else None
            lotes[(nome, numero)] = registrar_entrada(
                usuario=admin, produto=produtos[nome], quantidade=quantidade,
                numero_lote=numero, data_validade=validade, motivo='Carga de demonstração',
            )

        usuarios = {'admin': admin, 'caixa': caixa}
        for quem, itens in VENDAS:
            registrar_venda(usuarios[quem], [
                {'lote_id': lotes[(nome, numero)].pk, 'quantidade': quantidade}
                for nome, numero, quantidade in itens
            ])

        self.stdout.write(self.style.SUCCESS(
            f'Dados de demonstração criados: {len(produtos)} produtos, {len(lotes)} lotes, {len(VENDAS)} vendas.'
        ))

    def _usuario(self, nome, perfil, senha_opcao, variavel):
        existente = Usuario.objects.filter(nome=nome).first()
        if existente:
            return existente
        senha = senha_opcao or os.environ.get(variavel)
        if not senha:
            raise CommandError(f'Informe a senha do usuário "{nome}" (--senha-{nome} ou {variavel}).')
        usuario = Usuario.objects.create_user(nome, senha, perfil=perfil)
        self.stdout.write(f'Usuário "{nome}" criado.')
        return usuario
