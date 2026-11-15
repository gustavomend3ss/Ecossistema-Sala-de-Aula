import 'package:flutter/foundation.dart' show kIsWeb;

/// Endereço da API.
///
/// Publicado (Vercel): a API fica no mesmo domínio, em /api, e nada precisa
/// ser informado. Em desenvolvimento, passe o endereço ao rodar:
///   flutter run -d chrome --dart-define=API_URL=http://localhost:8000
///   flutter run -d emulator-5554 --dart-define=API_URL=http://10.0.2.2:8000
const String _apiDefinida = String.fromEnvironment('API_URL', defaultValue: '');

String get apiUrl {
  if (_apiDefinida.isNotEmpty) return _apiDefinida;
  if (kIsWeb) return '${Uri.base.origin}/api';
  return 'http://10.0.2.2:8000';
}
