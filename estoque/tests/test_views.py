"""
Testes de forms, views e API de estoque. Ver docs/projeto_django_spec.md §3.1 e §3.2.
"""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Produto
from core.models import Usuario
from estoque.forms import AjusteForm, FiltroMovimentacaoForm
from estoque.models import Lote, Movimentacao


class EstoqueBase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(nome='admin', senha='senha123', perfil='admin')
        self.operador = Usuario.objects.create_user(nome='operador', senha='senha123')
        self.categoria = Categoria.objects.create(nome='Vinhos')
        self.produto = Produto.objects.create(nome='Vinho', categoria=self.categoria)

    def entrar(self, nome):
        self.client.login(username=nome, password='senha123')


class VisaoGeralTestCase(EstoqueBase):
    def setUp(self):
        super().setUp()
        self.entrar('operador')
        self.baixo = Produto.objects.create(nome='Baixo', categoria=self.categoria)
        self.zerado = Produto.objects.create(nome='Zerado', categoria=self.categoria)
        self.ok = Produto.objects.create(nome='Ok', categoria=self.categoria)
        Lote.objects.create(produto=self.baixo, quantidade=3)
        Lote.objects.create(produto=self.ok, quantidade=50)

    def nomes(self, **filtros):
        resposta = self.client.get(reverse('estoque:visao_geral'), filtros)
        return [p.nome for p in resposta.context['produtos']]

    def test_sem_filtro_lista_todos_os_ativos(self):
        self.assertEqual(self.nomes(), ['Baixo', 'Ok', 'Vinho', 'Zerado'])

    def test_filtro_baixo_exclui_zerado(self):
        # 'Vinho' (sem lote) está zerado, então não entra em "baixo".
        self.assertEqual(self.nomes(status='baixo'), ['Baixo'])

    def test_filtro_zerado(self):
        self.assertEqual(self.nomes(status='zerado'), ['Vinho', 'Zerado'])

    def test_filtro_baixo_mostra_quantidade_sugerida_e_pdf(self):
        self.baixo.estoque_minimo, self.baixo.estoque_maximo = 5, 20
        self.baixo.save()
        resposta = self.client.get(reverse('estoque:visao_geral'), {'status': 'baixo'})
        self.assertEqual(resposta.context['produtos'][0].qtd_compra, 17)  # 20 - 3
        self.assertContains(resposta, '<th scope="col">Comprar</th>', html=True)
        self.assertContains(resposta, reverse('relatorios:reposicao_pdf'))

    def test_quantidade_sugerida_nunca_e_negativa(self):
        self.zerado.estoque_minimo = self.zerado.estoque_maximo = 0
        self.zerado.save()
        resposta = self.client.get(reverse('estoque:visao_geral'), {'status': 'zerado'})
        compras = {p.nome: p.qtd_compra for p in resposta.context['produtos']}
        self.assertEqual(compras['Zerado'], 0)

    def test_sem_filtro_nao_mostra_reposicao(self):
        resposta = self.client.get(reverse('estoque:visao_geral'))
        self.assertNotContains(resposta, 'Comprar')
        self.assertNotContains(resposta, reverse('relatorios:reposicao_pdf'))

    def test_produto_inativo_nao_aparece(self):
        self.ok.ativo = False
        self.ok.save()
        self.assertNotIn('Ok', self.nomes())


class EntradaViewTestCase(EstoqueBase):
    def test_operador_registra_entrada(self):
        self.entrar('operador')
        resposta = self.client.post(reverse('estoque:entrada'), {
            'produto': self.produto.pk, 'quantidade': '8', 'numero_lote': 'L9',
            'data_validade': '2030-05-01', 'motivo': 'Compra',
        })
        self.assertRedirects(resposta, reverse('estoque:visao_geral'))
        lote = Lote.objects.get()
        self.assertEqual((lote.quantidade, lote.numero_lote, lote.data_validade),
                         (8, 'L9', date(2030, 5, 1)))
        mov = Movimentacao.objects.get()
        self.assertEqual((mov.tipo, mov.usuario_id), ('entrada', self.operador.pk))

    def test_quantidade_zero_ou_negativa_rejeitada(self):
        self.entrar('operador')
        for quantidade in ['0', '-3']:
            with self.subTest(quantidade=quantidade):
                resposta = self.client.post(reverse('estoque:entrada'), {
                    'produto': self.produto.pk, 'quantidade': quantidade,
                })
                self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Lote.objects.count(), 0)

    def test_produto_inativo_nao_aceita_entrada(self):
        self.entrar('operador')
        self.produto.ativo = False
        self.produto.save()
        resposta = self.client.post(reverse('estoque:entrada'), {
            'produto': self.produto.pk, 'quantidade': '1',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Lote.objects.count(), 0)

    def test_produto_preselecionado_pela_querystring(self):
        self.entrar('operador')
        resposta = self.client.get(reverse('estoque:entrada'), {'produto_id': self.produto.pk})
        self.assertEqual(resposta.context['form'].initial['produto'], str(self.produto.pk))


class AjusteViewTestCase(EstoqueBase):
    def setUp(self):
        super().setUp()
        self.lote = Lote.objects.create(produto=self.produto, quantidade=10)

    def test_form_rejeita_lote_de_outro_produto(self):
        outro = Produto.objects.create(nome='Outro', categoria=self.categoria)
        form = AjusteForm({'produto': outro.pk, 'lote': self.lote.pk,
                           'nova_quantidade': '1', 'motivo': 'x'})
        self.assertFalse(form.is_valid())
        self.assertIn('lote', form.errors)

    def test_admin_ajusta_lote(self):
        self.entrar('admin')
        resposta = self.client.post(reverse('estoque:ajuste'), {
            'produto': self.produto.pk, 'lote': self.lote.pk,
            'nova_quantidade': '4', 'motivo': 'Contagem física',
        })
        self.assertRedirects(resposta, reverse('estoque:visao_geral'))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade, 4)
        self.assertEqual(Movimentacao.objects.get().quantidade, -6)

    def test_motivo_e_obrigatorio(self):
        self.entrar('admin')
        resposta = self.client.post(reverse('estoque:ajuste'), {
            'produto': self.produto.pk, 'lote': self.lote.pk,
            'nova_quantidade': '4', 'motivo': '',
        })
        self.assertEqual(resposta.status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade, 10)

    def test_operador_nao_ajusta(self):
        self.entrar('operador')
        resposta = self.client.post(reverse('estoque:ajuste'), {
            'produto': self.produto.pk, 'lote': self.lote.pk,
            'nova_quantidade': '0', 'motivo': 'x',
        })
        self.assertEqual(resposta.status_code, 403)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade, 10)


class ValidadeViewTestCase(EstoqueBase):
    def setUp(self):
        super().setUp()
        self.lote = Lote.objects.create(
            produto=self.produto, quantidade=3, data_validade=date(2030, 1, 1),
        )
        self.url = reverse('estoque:lote_validade', args=[self.lote.pk])

    def test_admin_altera_validade_com_auditoria(self):
        self.entrar('admin')
        resposta = self.client.post(self.url, {'data_validade': '2031-02-03', 'motivo': 'Erro'})
        self.assertRedirects(resposta, reverse('estoque:visao_geral'))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.data_validade, date(2031, 2, 3))
        self.assertEqual(self.lote.quantidade, 3)
        self.assertEqual(Movimentacao.objects.get().quantidade, 0)

    def test_motivo_obrigatorio(self):
        self.entrar('admin')
        self.client.post(self.url, {'data_validade': '2031-02-03', 'motivo': ''})
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.data_validade, date(2030, 1, 1))

    def test_operador_recebe_403(self):
        self.entrar('operador')
        self.assertEqual(self.client.get(self.url).status_code, 403)


class MovimentacaoListTestCase(EstoqueBase):
    def setUp(self):
        super().setUp()
        self.entrar('operador')
        agora = timezone.now()
        self.antiga = Movimentacao.objects.create(
            produto=self.produto, tipo='entrada', quantidade=5, usuario=self.admin,
            data=agora - timedelta(days=10),
        )
        self.recente = Movimentacao.objects.create(
            produto=self.produto, tipo='ajuste', quantidade=-1, usuario=self.admin, data=agora,
        )
        self.url = reverse('estoque:movimentacao_lista')

    def ids(self, **filtros):
        resposta = self.client.get(self.url, filtros)
        return {m.pk for m in resposta.context['movimentacoes']}

    def test_sem_filtro_lista_tudo(self):
        self.assertEqual(self.ids(), {self.antiga.pk, self.recente.pk})

    def test_filtro_por_tipo(self):
        self.assertEqual(self.ids(tipo='ajuste'), {self.recente.pk})

    def test_filtro_por_periodo(self):
        inicio = (timezone.localdate() - timedelta(days=2)).isoformat()
        self.assertEqual(self.ids(data_inicio=inicio), {self.recente.pk})
        fim = (timezone.localdate() - timedelta(days=5)).isoformat()
        self.assertEqual(self.ids(data_fim=fim), {self.antiga.pk})

    def test_periodo_invertido_e_invalido(self):
        form = FiltroMovimentacaoForm({'data_inicio': '2026-02-01', 'data_fim': '2026-01-01'})
        self.assertFalse(form.is_valid())
        self.assertIn('data_fim', form.errors)


class ApiLotesProdutoTestCase(EstoqueBase):
    def setUp(self):
        super().setUp()
        self.entrar('operador')
        self.hoje = timezone.localdate()
        self.url = reverse('estoque:api_lotes_produto', args=[self.produto.pk])

    def lote(self, quantidade=5, dias=None, numero=''):
        validade = None if dias is None else self.hoje + timedelta(days=dias)
        return Lote.objects.create(produto=self.produto, quantidade=quantidade,
                                   data_validade=validade, numero_lote=numero)

    def test_formato_e_ordem_peps(self):
        self.lote(numero='SEM')
        self.lote(dias=21, numero='A')
        self.lote(dias=3, numero='B')
        dados = self.client.get(self.url).json()
        self.assertEqual([d['numero_lote'] for d in dados], ['B', 'A', 'SEM'])
        primeiro = dados[0]
        self.assertEqual(set(primeiro), {
            'id', 'numero_lote', 'quantidade', 'data_validade', 'data_validade_fmt',
            'dias_para_vencer', 'data_entrada',
        })
        self.assertEqual(primeiro['dias_para_vencer'], 3)
        self.assertEqual(primeiro['data_validade_fmt'],
                         (self.hoje + timedelta(days=3)).strftime('%d/%m/%Y'))

    def test_lote_sem_validade(self):
        self.lote()
        item = self.client.get(self.url).json()[0]
        self.assertIsNone(item['data_validade'])
        self.assertIsNone(item['dias_para_vencer'])
        self.assertEqual(item['data_validade_fmt'], 'Sem validade')

    def test_exclui_vencido_e_zerado(self):
        self.lote(dias=-1)
        self.lote(quantidade=0, dias=5)
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_nao_mistura_lotes_de_outro_produto(self):
        outro = Produto.objects.create(nome='Outro', categoria=self.categoria)
        Lote.objects.create(produto=outro, quantidade=9)
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_produto_inexistente_404(self):
        resposta = self.client.get(reverse('estoque:api_lotes_produto', args=[999999]))
        self.assertEqual(resposta.status_code, 404)

    def test_metodo_post_nao_permitido(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)
