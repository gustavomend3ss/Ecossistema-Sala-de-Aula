import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/modelos.dart';
import '../../data/repositorios.dart';

class MensagemChat {
  MensagemChat({required this.pergunta, required this.horario, this.resposta, this.erro});
  final String pergunta;
  final DateTime horario;
  RespostaAssistente? resposta;
  String? erro;
  bool get pendente => resposta == null && erro == null;
}

class AssistenteViewModel extends ChangeNotifier {
  AssistenteViewModel(this._repos);
  final Repositorios _repos;

  List<TurmaResumo> turmas = [];
  TurmaResumo? turma;
  final List<MensagemChat> mensagens = [];
  bool carregando = true;
  String? erro;

  bool get enviando => mensagens.isNotEmpty && mensagens.last.pendente;

  /// Fontes da última resposta, para o painel lateral.
  List<Fonte> get fontes {
    for (final m in mensagens.reversed) {
      if (m.resposta != null) return m.resposta!.fontes;
    }
    return const [];
  }

  static const sugestoes = [
    'Quem precisa de acompanhamento nesta turma?',
    'Há notas pendentes?',
    'Como está a frequência?',
    'Quais critérios você usa?',
  ];

  Future<void> carregar() async {
    carregando = true;
    erro = null;
    notifyListeners();
    try {
      turmas = await _repos.turmas.listar();
      turma ??= turmas.isEmpty ? null : turmas.first;
    } on ApiException catch (e) {
      erro = e.mensagem;
    } finally {
      carregando = false;
      notifyListeners();
    }
  }

  void selecionarTurma(TurmaResumo? t) {
    if (t == null || t.id == turma?.id) return;
    turma = t;
    mensagens.clear();
    notifyListeners();
  }

  Future<void> perguntar(String texto) async {
    final t = turma;
    final pergunta = texto.trim();
    if (t == null || pergunta.length < 2 || enviando) return;
    final m = MensagemChat(pergunta: pergunta, horario: DateTime.now());
    mensagens.add(m);
    notifyListeners();
    try {
      m.resposta = await _repos.turmas.perguntar(t.id, pergunta);
    } on ApiException catch (e) {
      m.erro = e.mensagem;
    }
    notifyListeners();
  }
}
