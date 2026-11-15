import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'config.dart';
import 'data/api_client.dart';
import 'estado_app.dart';
import 'ui/aluno/casca_aluno.dart';
import 'ui/core/tema.dart';
import 'ui/login/login_view.dart';
import 'ui/professor/casca_professor.dart';

void main() {
  runApp(EcossistemaApp(estado: EstadoApp(ApiClient(apiUrl))));
}

class EcossistemaApp extends StatelessWidget {
  const EcossistemaApp({super.key, required this.estado});
  final EstadoApp estado;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FAINOR • Gestão Acadêmica',
      debugShowCheckedModeBanner: false,
      theme: temaFainor(),
      locale: const Locale('pt', 'BR'),
      supportedLocales: const [Locale('pt', 'BR')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: ListenableBuilder(
        listenable: estado,
        builder: (context, _) {
          final u = estado.usuario;
          if (u == null) return LoginView(estado: estado);
          if (u.professor) return CascaProfessor(estado: estado, usuario: u);
          return CascaAluno(estado: estado, usuario: u);
        },
      ),
    );
  }
}
