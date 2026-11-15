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
}
