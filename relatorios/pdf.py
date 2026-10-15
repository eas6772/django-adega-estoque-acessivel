"""
Geração do PDF de reposição de estoque (ReportLab). Reaproveita a mesma
consulta usada pela página HTML — nenhuma regra de negócio duplicada.
"""
import io

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from core.templatetags.ui import brl

from . import consultas


def gerar_pdf_reposicao():
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=A4)
    estilos = getSampleStyleSheet()

    elementos = [
        Paragraph('Empório BR — Relatório de reposição de estoque', estilos['Title']),
        Paragraph(
            f'Gerado em {timezone.localtime():%d/%m/%Y %H:%M}', estilos['Normal'],
        ),
        Spacer(1, 12),
    ]

    cabecalho = ['Produto', 'Categoria', 'Estoque', 'Mínimo', 'Máximo', 'Comprar']
    linhas = [cabecalho]
    for produto in consultas.produtos_para_reposicao():
        linhas.append([
            produto.nome,
            produto.categoria.nome,
            str(produto.estoque_total),
            str(produto.estoque_minimo),
            str(produto.estoque_maximo),
            str(produto.qtd_compra),
        ])

    tabela = Table(linhas, repeatRows=1)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elementos.append(tabela)

    documento.build(elementos)
    buffer.seek(0)
    return buffer


def gerar_pdf_estoque():
    """Inventário completo: todos os produtos ativos, com valor por produto e total geral."""
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=A4)
    estilos = getSampleStyleSheet()

    produtos = consultas.produtos_com_valor_estoque().order_by('nome')
    elementos = [
        Paragraph('Empório BR — Inventário de estoque', estilos['Title']),
        Paragraph(f'Gerado em {timezone.localtime():%d/%m/%Y %H:%M}', estilos['Normal']),
        Paragraph(f'Valor total em estoque: <b>{brl(consultas.valor_total_estoque(produtos))}</b>', estilos['Normal']),
        Spacer(1, 12),
    ]

    linhas = [['Produto', 'Categoria', 'Estoque', 'Custo unit.', 'Valor em estoque']]
    for produto in produtos:
        linhas.append([
            produto.nome,
            produto.categoria.nome,
            str(produto.estoque_total),
            brl(produto.preco_custo),
            brl(produto.valor_estoque),
        ])

    tabela = Table(linhas, repeatRows=1)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
    ]))
    elementos.append(tabela)

    documento.build(elementos)
    buffer.seek(0)
    return buffer
