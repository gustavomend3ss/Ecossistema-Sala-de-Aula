import 'package:flutter/foundation.dart';

import 'data/api_client.dart';
import 'data/modelos.dart';
import 'data/repositorios.dart';

/// Estado global mínimo: quem está logado. O resto fica nos view models.
class EstadoApp extends ChangeNotifier {
  EstadoApp(this.api) : repos = Repositorios(api) {
    api.aoPerderSessao = () {
      usuario = null;
      sessaoExpirada = true;
      notifyListeners();
    };
  }

  final ApiClient api;
  final Repositorios repos;
  Usuario? usuario;
  bool sessaoExpirada = false;

  void definirUsuario(Usuario u) {
    usuario = u;
    sessaoExpirada = false;
    notifyListeners();
  }

  Future<void> sair() async {
    try {
      await repos.sessao.sair();
    } catch (_) {
      // Mesmo sem rede, a sessão local é encerrada.
    }
    usuario = null;
    notifyListeners();
  }
}
