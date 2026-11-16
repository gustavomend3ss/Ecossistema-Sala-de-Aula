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

/// Conversa com o assistente docente. O contexto (disciplina, estudantes da
/// resposta anterior, escolha pendente) fica no servidor, preso à conversa e
/// ao usuário; aqui guardamos só o id da conversa e as trocas exibidas.
class AssistenteViewModel extends ChangeNotifier {
  AssistenteViewModel(this._repos);
  final Repositorios _repos;

  final List<MensagemChat> mensagens = [];
  int? conversaId;

  List<TurmaResumo> turmas = [];
  List<ConversaResumo> historico = [];
  bool carregando = true;
  bool abrindoConversa = false;
  String? erro;

  bool get enviando => mensagens.isNotEmpty && mensagens.last.pendente;

  /// Fontes da última resposta, para o painel lateral.
  List<Fonte> get fontes {
    for (final m in mensagens.reversed) {
      if (m.resposta != null) return m.resposta!.fontes;
    }
    return const [];
  }

  Future<void> carregar() async {
    carregando = true;
    erro = null;
    notifyListeners();
    try {
      turmas = await _repos.turmas.listar();
      historico = await _repos.assistente.conversas();
    } on ApiException catch (e) {
      erro = e.mensagem;
    } finally {
      carregando = false;
      notifyListeners();
    }
  }

  Future<void> _atualizarHistorico() async {
    try {
      historico = await _repos.assistente.conversas();
      notifyListeners();
    } on ApiException {
      // O histórico é secundário: a conversa atual continua funcionando.
    }
  }

  void novaConversa() {
    if (enviando) return;
    mensagens.clear();
    conversaId = null;
    notifyListeners();
  }

  Future<void> abrirConversa(int id) async {
    if (enviando || id == conversaId) return;
    abrindoConversa = true;
    notifyListeners();
    try {
      final trocas = await _repos.assistente.abrir(id);
      mensagens
        ..clear()
        ..addAll([
          for (final t in trocas)
            MensagemChat(pergunta: t.pergunta, horario: t.criadaEm, resposta: t.resposta),
        ]);
      conversaId = id;
    } on ApiException catch (e) {
      mensagens
        ..clear()
        ..add(MensagemChat(pergunta: 'Abrir conversa', horario: DateTime.now(), erro: e.mensagem));
      conversaId = null;
    } finally {
      abrindoConversa = false;
      notifyListeners();
    }
  }

  Future<void> perguntar(String texto) async {
    final pergunta = texto.trim();
    if (pergunta.length < 2 || enviando) return;
    final m = MensagemChat(pergunta: pergunta, horario: DateTime.now());
    mensagens.add(m);
    notifyListeners();
    final nova = conversaId == null;
    try {
      final r = await _repos.assistente.enviar(pergunta, conversaId: conversaId);
      m.resposta = r;
      conversaId = r.conversaId ?? conversaId;
    } on ApiException catch (e) {
      if (e.status == 404 && conversaId != null) {
        // A conversa não existe mais (ou não é deste usuário): começa outra.
        conversaId = null;
        m.erro = 'Esta conversa não está mais disponível. Envie a pergunta de novo para começar outra.';
      } else {
        m.erro = e.mensagem;
      }
    }
    notifyListeners();
    if (nova && m.resposta != null) _atualizarHistorico();
  }
}
