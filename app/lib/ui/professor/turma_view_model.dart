import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/modelos.dart';
import '../../data/repositorios.dart';

class TurmaViewModel extends ChangeNotifier {
  TurmaViewModel(this._repos, this.turmaId);
  final Repositorios _repos;
  final int turmaId;

  TurmaDetalhe? turma;
  bool carregando = true;
  bool analisando = false;
  String? erro;
  int aba = 0;
  int? aulaSelecionada;
  final Set<String> salvando = {};

  void trocarAba(int i) {
    aba = i;
    notifyListeners();
  }

  void selecionarAula(int? id) {
    aulaSelecionada = id;
    notifyListeners();
  }

  Future<void> carregar({bool silencioso = false}) async {
    if (!silencioso) {
      carregando = true;
      erro = null;
      notifyListeners();
    }
    try {
      turma = await _repos.turmas.detalhar(turmaId);
      aulaSelecionada ??= turma!.aulas.isEmpty ? null : turma!.aulas.last.id;
      erro = null;
    } on ApiException catch (e) {
      erro = e.mensagem;
    } finally {
      carregando = false;
      notifyListeners();
    }
  }

  /// Devolve uma mensagem para o usuário (sucesso ou erro).
  Future<String> analisarTurma() async {
    analisando = true;
    notifyListeners();
    try {
      final analises = await _repos.turmas.analisarTurma(turmaId);
      await carregar(silencioso: true);
      final alertas = analises.where((a) => a.regras.any((r) => r == 'R1' || r == 'R2' || r == 'R6')).length;
      final pend = analises.where((a) => a.pendencias.isNotEmpty).length;
      return 'Análise concluída: $alertas com alerta e $pend com pendência.';
    } on ApiException catch (e) {
      return e.mensagem;
    } finally {
      analisando = false;
      notifyListeners();
    }
  }

  Future<String?> salvarNota(int matriculaId, int avaliacaoId, double valor) async {
    final chave = 'n$matriculaId-$avaliacaoId';
    salvando.add(chave);
    notifyListeners();
    try {
      await _repos.matriculas.salvarNota(matriculaId, avaliacaoId, valor);
      await carregar(silencioso: true);
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    } finally {
      salvando.remove(chave);
      notifyListeners();
    }
  }

  Future<String?> salvarPresenca(int matriculaId, int aulaId, bool presente) async {
    final chave = 'p$matriculaId-$aulaId';
    salvando.add(chave);
    notifyListeners();
    try {
      await _repos.matriculas.salvarPresenca(matriculaId, aulaId, presente);
      await carregar(silencioso: true);
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    } finally {
      salvando.remove(chave);
      notifyListeners();
    }
  }

  Future<String?> marcarEntrega(int matriculaId, int atividadeId, bool entregue) async {
    final chave = 'e$matriculaId-$atividadeId';
    salvando.add(chave);
    notifyListeners();
    try {
      await _repos.matriculas.marcarEntrega(matriculaId, atividadeId, entregue);
      await carregar(silencioso: true);
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    } finally {
      salvando.remove(chave);
      notifyListeners();
    }
  }

  Future<String?> criarAtividade(String titulo, String prazo, String descricao) async {
    try {
      await _repos.turmas.criarAtividade(turmaId, titulo, prazo, descricao);
      await carregar(silencioso: true);
      return null;
    } on ApiException catch (e) {
      return e.mensagem;
    }
  }

  /// Chamada rápida: marca presença para quem ainda não tem registro na aula.
  Future<String?> todosPresentes(int aulaId) async {
    final t = turma;
    if (t == null) return null;
    final faltando = t.estudantes.where((e) => e.presencas['$aulaId'] == null).toList();
    if (faltando.isEmpty) return 'Todos os estudantes já têm registro nesta aula.';
    try {
      for (final e in faltando) {
        await _repos.matriculas.salvarPresenca(e.matriculaId, aulaId, true);
      }
      await carregar(silencioso: true);
      return '${faltando.length} presença(s) registrada(s).';
    } on ApiException catch (e) {
      return e.mensagem;
    }
  }
}
