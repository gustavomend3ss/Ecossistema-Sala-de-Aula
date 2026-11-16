import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ecossistema_academico/data/api_client.dart';
import 'package:ecossistema_academico/data/modelos.dart';
import 'package:ecossistema_academico/estado_app.dart';
import 'package:ecossistema_academico/main.dart';
import 'package:ecossistema_academico/ui/core/componentes.dart';
import 'package:ecossistema_academico/ui/core/formato.dart';

void main() {
  group('formatação pt-BR', () {
    test('números e porcentagens', () {
      expect(fmtNum(5.2), '5,2');
      expect(fmtNum(null), '—');
      expect(fmtPct(76.0), '76%');
      expect(fmtPct(92.5), '92,5%');
      expect(lerNumero('7,5'), 7.5);
      expect(lerNumero('abc'), isNull);
    });
  });

  group('modelos', () {
    test('análise do A01 vinda da API', () {
      final a = Analise.fromJson({
        'id': 1,
        'criado_em': '2026-11-03T12:00:00+00:00',
        'solicitado_por': 'Prof. Gabriel',
        'versao_registros': 1,
        'versao_criterios': 'DEMO-v1',
        'desatualizada': false,
        'media': 5.2,
        'frequencia': 76.0,
        'presencas': 19,
        'unidades_consideradas': 25,
        'prioridade': 'prioridade_alta',
        'regras': ['R1', 'R2', 'R3'],
        'acionadas': [
          {
            'regra': 'R1',
            'corpo': ['media_baixa'],
            'cabeca': 'alerta_media',
            'evidencia': {
              'media_baixa': {'indicador': 'media', 'valor': 5.2, 'limite': 6.0, 'comparacao': '<'}
            }
          }
        ],
        'pendencias': [],
        'motivo': 'A média 5,2 está abaixo do limite didático de 6,0...',
        'sintese': null,
        'sintese_status': 'desativada',
        'criterios': {'versao': 'DEMO-v1', 'media_minima': 6.0, 'frequencia_minima': 80.0},
        'revisoes': [],
      });
      expect(a.regras, ['R1', 'R2', 'R3']);
      expect(a.media, 5.2);
      expect(a.acionadas.first.evidencia.containsKey('media_baixa'), isTrue);
    });

    test('nota não lançada continua nula', () {
      final n = RegistroNota.fromJson({
        'avaliacao_id': 2, 'nome': 'Avaliação 2', 'peso': 1, 'nota_maxima': 10,
        'obrigatoria': true, 'valor': null, 'versao': 0,
      });
      expect(n.valor, isNull);
    });
  });

  test('radar de entregas da atividade', () {
    final a = AtividadeResumo.fromJson({
      'id': 3, 'titulo': 'Mapa de frames', 'descricao': '', 'prazo': '2026-11-07',
      'vencida': true, 'total': 3,
      'contagem': {'entregue': 1, 'entregue_atraso': 0, 'atrasada': 2, 'aberta': 0},
    });
    expect(a.noPrazo, 1);
    expect(a.semEntrega, 2);
    expect(fmtCerteza(0.88), '0,88');
  });

  testWidgets('situação da entrega aparece por extenso', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: Column(children: [
        ChipSituacao(situacao: 'atrasada'),
        ChipSituacao(situacao: 'entregue_atraso'),
      ])),
    ));
    expect(find.text('Sem entrega'), findsOneWidget);
    expect(find.text('Entregue com atraso'), findsOneWidget);
  });

  testWidgets('chip de acompanhamento sempre tem texto', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: ChipAcompanhamento(prioridade: 'prioridade_alta', desatualizada: true)),
    ));
    expect(find.text('Prioridade alta'), findsOneWidget);
    expect(find.text('Desatualizada'), findsOneWidget);
  });

  testWidgets('login valida campos vazios sem chamar a API', (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(EcossistemaApp(estado: EstadoApp(ApiClient('http://localhost:1'))));
    await tester.tap(find.widgetWithText(FilledButton, 'Entrar'));
    await tester.pump();
    expect(find.text('Informe o usuário.'), findsOneWidget);
    expect(find.text('Informe a senha.'), findsOneWidget);
  });

  test('resposta do assistente com seções, opções e contexto', () {
    final r = RespostaAssistente.fromJson({
      'conversa_id': 7,
      'pergunta': 'E quais deles também têm muitas faltas?',
      'tipo': 'resposta',
      'intencao': 'listar_alunos_em_risco',
      'texto': 'Em Estrutura de Dados, 2 estudantes aparecem pelo critério escolhido.',
      'secoes': [
        {
          'funcao': 'listar_alunos_em_risco',
          'titulo': 'Muitas faltas',
          'texto': '',
          'sem_dados': false,
          'itens': [
            {'matricula_id': 11, 'codigo': 'E01', 'aluno': 'Ana Beatriz Souza', 'disciplina': 'Estrutura de Dados',
             'titulo': 'Ana Beatriz Souza (E01)', 'prioridade': 'prioridade_alta', 'certeza': 0.9,
             'detalhes': [], 'observacao': null, 'linhas': ['Conversar sobre as faltas (R2).']},
          ],
        },
      ],
      'itens': [],
      'opcoes': [{'rotulo': 'Ana Lima · W05', 'valor': 'Ana Lima'}],
      'sugestoes': ['Sugira intervenções para esses estudantes'],
      'fontes': [],
      'contexto': {'disciplinas': ['Estrutura de Dados'], 'estudantes': 3, 'continuacao': true},
      'gerado_por': 'regras',
      'aviso': 'Apoio à decisão.',
    });
    expect(r.conversaId, 7);
    expect(r.secoes.single.itens.single.codigo, 'E01');
    expect(r.secoes.single.itens.single.linhas, hasLength(1));
    expect(r.opcoes.single.valor, 'Ana Lima');
    expect(r.disciplinas, ['Estrutura de Dados']);
    expect(r.continuacao, isTrue);
  });

  test('resposta antiga, sem campos novos, continua legível', () {
    final r = RespostaAssistente.fromJson({'pergunta': 'x', 'intencao': 'ajuda', 'texto': 't', 'itens': [], 'fontes': [], 'aviso': ''});
    expect(r.tipo, 'resposta');
    expect(r.secoes, isEmpty);
    expect(r.conversaId, isNull);
  });

  testWidgets('login avisa quando a sessão expirou e mostra a equipe', (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final estado = EstadoApp(ApiClient('http://localhost:1'))..sessaoExpirada = true;
    await tester.pumpWidget(EcossistemaApp(estado: estado));
    expect(find.textContaining('Sua sessão expirou'), findsOneWidget);
    expect(find.textContaining('Wallas Fróes de Oliveira'), findsOneWidget);
    expect(find.textContaining('Samuel Cotinguiba'), findsOneWidget);
  });
}
