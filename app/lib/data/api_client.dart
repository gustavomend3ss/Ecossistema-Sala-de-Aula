import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// Erro vindo da API, já com mensagem pronta para mostrar ao usuário.
class ApiException implements Exception {
  ApiException(this.status, this.mensagem);

  final int status;
  final String mensagem;

  bool get naoAutenticado => status == 401;

  @override
  String toString() => mensagem;
}

/// Serviço de comunicação com a API (HTTPS + JSON).
/// O app nunca acessa o banco diretamente: tudo passa por aqui.
class ApiClient {
  ApiClient(this.baseUrl, {http.Client? cliente})
      : _http = cliente ?? http.Client();

  final String baseUrl;
  final http.Client _http;
  String? token;

  /// Chamado quando a API responde 401 (sessão expirada).
  void Function()? aoPerderSessao;

  Map<String, String> get _cabecalhos => {
        'Content-Type': 'application/json; charset=utf-8',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Uri _uri(String caminho) => Uri.parse('$baseUrl$caminho');

  Future<dynamic> get(String caminho) =>
      _enviar(() => _http.get(_uri(caminho), headers: _cabecalhos));

  Future<dynamic> post(String caminho, [Object? corpo]) => _enviar(() =>
      _http.post(_uri(caminho),
          headers: _cabecalhos, body: corpo == null ? null : jsonEncode(corpo)));

  Future<dynamic> put(String caminho, Object corpo) => _enviar(() =>
      _http.put(_uri(caminho), headers: _cabecalhos, body: jsonEncode(corpo)));

  Future<dynamic> delete(String caminho) =>
      _enviar(() => _http.delete(_uri(caminho), headers: _cabecalhos));

  Future<dynamic> _enviar(Future<http.Response> Function() chamada) async {
    http.Response r;
    try {
      r = await chamada().timeout(const Duration(seconds: 25));
    } on TimeoutException {
      throw ApiException(0, 'A API demorou demais para responder. Tente de novo.');
    } catch (_) {
      throw ApiException(0,
          'Não foi possível conectar à API em $baseUrl. Verifique se o servidor está rodando.');
    }

    final texto = utf8.decode(r.bodyBytes);
    final dynamic corpo = texto.isEmpty ? null : _tentarJson(texto);

    if (r.statusCode >= 200 && r.statusCode < 300) return corpo;

    if (r.statusCode == 401 && token != null) {
      token = null;
      aoPerderSessao?.call();
    }
    throw ApiException(r.statusCode, _mensagemDeErro(r.statusCode, corpo));
  }

  dynamic _tentarJson(String texto) {
    try {
      return jsonDecode(texto);
    } catch (_) {
      return texto;
    }
  }

  String _mensagemDeErro(int status, dynamic corpo) {
    if (corpo is Map && corpo['detail'] != null) {
      final detalhe = corpo['detail'];
      if (detalhe is String) return detalhe;
      // Erros de validação do FastAPI chegam como lista
      if (detalhe is List && detalhe.isNotEmpty) {
        return detalhe
            .map((e) => e is Map ? (e['msg'] ?? '').toString() : e.toString())
            .where((m) => m.isNotEmpty)
            .join(' ');
      }
    }
    return 'Erro inesperado na API (código $status).';
  }
}
