import 'api_client.dart';
import 'modelos.dart';

Map<String, dynamic> _mapa(dynamic v) => Map<String, dynamic>.from(v as Map);
List<T> _lista<T>(dynamic v, T Function(Map<String, dynamic>) f) =>
    (v as List).map((e) => f(_mapa(e))).toList();

/// Repositórios: a única ponte entre os view models e a API.
/// Trocar a API (ex.: por Supabase) só exige mexer aqui.

class SessaoRepositorio {
  SessaoRepositorio(this._api);
  final ApiClient _api;

  Future<Usuario> entrar(String login, String senha) async {
    final r = _mapa(await _api.post('/sessoes', {'login': login, 'senha': senha}));
    _api.token = r['token'] as String;
    return Usuario.fromJson(_mapa(r['usuario']));
  }

  Future<void> sair() async {
    try {
      await _api.delete('/sessoes');
    } finally {
      _api.token = null;
    }
  }
}

class TurmaRepositorio {
  TurmaRepositorio(this._api);
  final ApiClient _api;

  Future<List<TurmaResumo>> listar() async =>
      _lista(await _api.get('/turmas'), TurmaResumo.fromJson);

  Future<TurmaDetalhe> detalhar(int turmaId) async =>
      TurmaDetalhe.fromJson(_mapa(await _api.get('/turmas/$turmaId')));

  Future<List<Analise>> analisarTurma(int turmaId) async =>
      _lista(await _api.post('/turmas/$turmaId/analises'), Analise.fromJson);

  Future<List<AtividadeResumo>> atividades(int turmaId) async =>
      _lista(await _api.get('/turmas/$turmaId/atividades'), AtividadeResumo.fromJson);

  Future<AtividadeResumo> criarAtividade(int turmaId, String titulo, String prazo, String descricao) async =>
      AtividadeResumo.fromJson(_mapa(await _api.post('/turmas/$turmaId/atividades',
          {'titulo': titulo, 'prazo': prazo, 'descricao': descricao})));

  Future<RespostaAssistente> perguntar(int turmaId, String pergunta) async =>
      RespostaAssistente.fromJson(
          _mapa(await _api.post('/turmas/$turmaId/assistente', {'pergunta': pergunta})));
}

class MatriculaRepositorio {
  MatriculaRepositorio(this._api);
  final ApiClient _api;

  Future<Registros> registros(int matriculaId) async =>
      Registros.fromJson(_mapa(await _api.get('/matriculas/$matriculaId/registros')));

  Future<Registros> salvarNota(int matriculaId, int avaliacaoId, double valor) async =>
      Registros.fromJson(_mapa(await _api.put(
          '/matriculas/$matriculaId/notas/$avaliacaoId', {'valor': valor})));

  Future<Registros> salvarPresenca(int matriculaId, int aulaId, bool presente) async =>
      Registros.fromJson(_mapa(await _api.put(
          '/matriculas/$matriculaId/presencas/$aulaId', {'presente': presente})));

  Future<Registros> marcarEntrega(int matriculaId, int atividadeId, bool entregue) async =>
      Registros.fromJson(_mapa(await _api.put(
          '/matriculas/$matriculaId/entregas/$atividadeId', {'entregue': entregue})));

  Future<Analise> analisar(int matriculaId) async =>
      Analise.fromJson(_mapa(await _api.post('/matriculas/$matriculaId/analises')));

  Future<List<Analise>> analises(int matriculaId) async =>
      _lista(await _api.get('/matriculas/$matriculaId/analises'), Analise.fromJson);

  Future<List<Alteracao>> historico(int matriculaId) async =>
      _lista(await _api.get('/matriculas/$matriculaId/historico'), Alteracao.fromJson);

  Future<Analise> revisar(int analiseId, String decisao, String observacao) async =>
      Analise.fromJson(_mapa(await _api.post('/analises/$analiseId/revisoes',
          {'decisao': decisao, 'observacao': observacao})));

  Future<List<Conferencia>> conferencias(int matriculaId) async =>
      _lista(await _api.get('/matriculas/$matriculaId/conferencias'), Conferencia.fromJson);

  Future<Conferencia> pedirConferencia(int matriculaId, String referencia, String mensagem) async =>
      Conferencia.fromJson(_mapa(await _api.post('/matriculas/$matriculaId/conferencias',
          {'referencia': referencia, 'mensagem': mensagem})));

  Future<Conferencia> responderConferencia(int pedidoId, String resposta) async =>
      Conferencia.fromJson(
          _mapa(await _api.post('/conferencias/$pedidoId/resposta', {'resposta': resposta})));
}

class AlunoRepositorio {
  AlunoRepositorio(this._api);
  final ApiClient _api;

  Future<List<Registros>> desempenho() async =>
      _lista(await _api.get('/aluno/desempenho'), Registros.fromJson);
}

/// Agrupa os repositórios para injetar nas telas.
class Repositorios {
  Repositorios(ApiClient api)
      : sessao = SessaoRepositorio(api),
        turmas = TurmaRepositorio(api),
        matriculas = MatriculaRepositorio(api),
        aluno = AlunoRepositorio(api);

  final SessaoRepositorio sessao;
  final TurmaRepositorio turmas;
  final MatriculaRepositorio matriculas;
  final AlunoRepositorio aluno;
}
