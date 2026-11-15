import 'package:flutter/material.dart';

import '../../data/modelos.dart';
import '../../estado_app.dart';
import '../core/casca.dart';
import 'assistente_view.dart';
import 'turmas_view.dart';

class CascaProfessor extends StatelessWidget {
  const CascaProfessor({super.key, required this.estado, required this.usuario});
  final EstadoApp estado;
  final Usuario usuario;

  @override
  Widget build(BuildContext context) {
    return Casca(
      usuario: usuario,
      aoSair: estado.sair,
      itens: const [
        ItemMenu('Turmas', Icons.groups_outlined, Icons.groups),
        ItemMenu('Assistente', Icons.chat_bubble_outline, Icons.chat_bubble),
      ],
      paginas: [
        TurmasView(repos: estado.repos),
        AssistenteView(repos: estado.repos),
      ],
    );
  }
}
