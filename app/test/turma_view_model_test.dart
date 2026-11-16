import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:ecossistema_academico/data/api_client.dart';
import 'package:ecossistema_academico/data/repositorios.dart';
import 'package:ecossistema_academico/ui/professor/turma_view_model.dart';

void main() {
  test('resumo da análise inclui alerta de entregas sem contar o aluno duas vezes', () async {
    final cliente = MockClient((pedido) async {
      if (pedido.method == 'POST' && pedido.url.path == '/turmas/1/analises') {
        return http.Response(jsonEncode([
          {'regras': ['R1', 'R2', 'R3']},
          {'regras': ['R6']},
          {'regras': [], 'pendencias': [{'indicador': 'media', 'regra': 'R4', 'motivo': 'Sem nota'}]},
        ]), 200);
      }
      if (pedido.method == 'GET' && pedido.url.path == '/turmas/1') {
        return http.Response(jsonEncode({'id': 1, 'criterios': {}}), 200);
      }
      throw StateError('Requisição inesperada: ${pedido.method} ${pedido.url}');
    });
    final vm = TurmaViewModel(Repositorios(ApiClient('http://teste', cliente: cliente)), 1);
    addTearDown(vm.dispose);
    addTearDown(cliente.close);

    expect(await vm.analisarTurma(), 'Análise concluída: 2 com alerta e 1 com pendência.');
    expect(vm.analisando, isFalse);
    expect(vm.turma?.id, 1);
  });
}
