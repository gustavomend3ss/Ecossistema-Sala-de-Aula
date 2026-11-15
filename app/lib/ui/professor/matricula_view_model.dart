import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/modelos.dart';
import '../../data/repositorios.dart';

class MatriculaViewModel extends ChangeNotifier {
  MatriculaViewModel(this._repos, this.matriculaId);
  final Repositorios _repos;
  final int matriculaId;

  Registros? registros;
  List<Analise> analises = [];
  List<Alteracao> historico = [];
  List<Conferencia> conferencias = [];
  bool carregando = true;
  bool analisando = false;
  bool revisando = false;
  String? erro;

  Analise? get atual => analises.isEmpty ? null : analises.first;

  Future<void> carregar({bool silencioso = false}) async {
    if (!silencioso) {
      carregando = true;
      erro = null;
      notifyListeners();
    }
    try {
      final r = await Future.wait<Object>([
        _repos.matriculas.registros(matriculaId),
        _repos.matriculas.analises(matriculaId),
        _repos.matriculas.historico(matriculaId),
        _repos.matriculas.conferencias(matriculaId),
      ]);
      registros = r[0] as Registros;
      analises = r[1] as List<Analise>;
      historico = r[2] as List<Alteracao>;
      conferencias = r[3] as List<Conferencia>;
      erro = null;
    } on ApiException catch (e) {
      erro = e.mensagem;
    } finally {
      carregando = false;
      notifyListeners();
    }
  }

  Future<String?> analisar() async {
    analisando = true;
    notifyListeners();
    try {
      await _repos.matriculas.analisar(matriculaId);
      await carregar(silencioso: true);
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    } finally {
      analisando = false;
      notifyListeners();
    }
  }

  Future<String?> revisar(String decisao, String observacao) async {
    final a = atual;
    if (a == null) return 'Faça uma análise antes de registrar a revisão.';
    revisando = true;
    notifyListeners();
    try {
      await _repos.matriculas.revisar(a.id, decisao, observacao);
      await carregar(silencioso: true);
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    } finally {
      revisando = false;
      notifyListeners();
    }
  }

  Future<String?> salvarNota(int avaliacaoId, double valor) =>
      _salvar(() => _repos.matriculas.salvarNota(matriculaId, avaliacaoId, valor));

  Future<String?> salvarPresenca(int aulaId, bool presente) =>
      _salvar(() => _repos.matriculas.salvarPresenca(matriculaId, aulaId, presente));

  Future<String?> marcarEntrega(int atividadeId, bool entregue) =>
      _salvar(() => _repos.matriculas.marcarEntrega(matriculaId, atividadeId, entregue));

  Future<String?> _salvar(Future<Registros> Function() acao) async {
    try {
      registros = await acao();
      // A análise vigente passa a aparecer como desatualizada (R5).
      await carregar(silencioso: true);
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    }
  }

  Future<String?> responder(int pedidoId, String resposta) async {
    try {
      await _repos.matriculas.responderConferencia(pedidoId, resposta);
      await carregar(silencioso: true);
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    }
  }
}
