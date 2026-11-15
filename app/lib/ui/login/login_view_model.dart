import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../estado_app.dart';

class LoginViewModel extends ChangeNotifier {
  LoginViewModel(this._estado);
  final EstadoApp _estado;

  bool carregando = false;
  String? erro;

  String? validarLogin(String? v) =>
      (v == null || v.trim().isEmpty) ? 'Informe o usuário.' : null;

  String? validarSenha(String? v) =>
      (v == null || v.isEmpty) ? 'Informe a senha.' : null;

  Future<void> entrar(String login, String senha) async {
    carregando = true;
    erro = null;
    notifyListeners();
    try {
      final u = await _estado.repos.sessao.entrar(login.trim().toLowerCase(), senha);
      _estado.definirUsuario(u);
    } on ApiException catch (e) {
      erro = e.mensagem;
    } finally {
      carregando = false;
      notifyListeners();
    }
  }
}
