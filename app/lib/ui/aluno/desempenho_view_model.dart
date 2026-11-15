import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/modelos.dart';
import '../../data/repositorios.dart';

class DesempenhoViewModel extends ChangeNotifier {
  DesempenhoViewModel(this._repos);
  final Repositorios _repos;

  List<Registros> matriculas = [];
  int selecionada = 0;
  Map<int, List<Conferencia>> conferencias = {};
  bool carregando = true;
  bool enviando = false;
  String? erro;

  Registros? get atual => matriculas.isEmpty ? null : matriculas[selecionada];
  List<Conferencia> get conferenciasAtuais => conferencias[atual?.matriculaId] ?? const [];

  List<(Registros, Conferencia)> get todasConferencias => [
        for (final m in matriculas)
          for (final c in conferencias[m.matriculaId] ?? const <Conferencia>[]) (m, c),
      ];

  Future<void> carregar() async {
    carregando = true;
    erro = null;
    notifyListeners();
    try {
      matriculas = await _repos.aluno.desempenho();
      if (selecionada >= matriculas.length) selecionada = 0;
      final listas = await Future.wait(
          matriculas.map((m) => _repos.matriculas.conferencias(m.matriculaId)));
      conferencias = {
        for (var i = 0; i < matriculas.length; i++) matriculas[i].matriculaId: listas[i],
      };
    } on ApiException catch (e) {
      erro = e.mensagem;
    } finally {
      carregando = false;
      notifyListeners();
    }
  }

  void selecionar(int i) {
    selecionada = i;
    notifyListeners();
  }

  Future<String?> pedirConferencia(String referencia, String mensagem) async {
    final m = atual;
    if (m == null) return 'Nenhuma matrícula selecionada.';
    enviando = true;
    notifyListeners();
    try {
      final c = await _repos.matriculas.pedirConferencia(m.matriculaId, referencia, mensagem);
      conferencias[m.matriculaId] = [c, ...conferenciasAtuais];
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    } finally {
      enviando = false;
      notifyListeners();
    }
  }
}
