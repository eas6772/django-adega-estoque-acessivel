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
