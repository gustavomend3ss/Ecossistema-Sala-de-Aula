import 'package:flutter/material.dart';

import 'tema.dart';

/// Equipe e orientação do trabalho (FAINOR, 2026.2).
const integrantes = [
  'Camila Ramos',
  'Daniel Soares Oliveira',
  'Guilherme Pereira',
  'Gustavo Mendes',
  'Matheus Caires',
  'Rauan Brandão',
  'Samuel Cotinguiba',
];
const professorOrientador = 'Prof. Wallas Fróes de Oliveira';

class Creditos extends StatelessWidget {
  const Creditos({super.key, this.escuro = false});

  /// Texto claro sobre fundo escuro (painel lateral do login).
  final bool escuro;

  @override
  Widget build(BuildContext context) {
    final cor = escuro ? const Color(0xFFC9C9CF) : Cores.textoSuave;
    final destaque = escuro ? Colors.white : Cores.texto;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Equipe', style: TextStyle(color: destaque, fontWeight: FontWeight.w700, fontSize: 13)),
      const SizedBox(height: 4),
      Text(integrantes.join(' · '), style: TextStyle(color: cor, fontSize: 12.5, height: 1.5)),
      const SizedBox(height: 8),
      Text('Orientação: $professorOrientador', style: TextStyle(color: cor, fontSize: 12.5)),
    ]);
  }
}
