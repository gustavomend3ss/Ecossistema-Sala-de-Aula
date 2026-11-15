import 'package:flutter/material.dart';

import '../../data/modelos.dart';
import '../../estado_app.dart';
import '../core/casca.dart';
import 'desempenho_view.dart';
import 'desempenho_view_model.dart';

class CascaAluno extends StatefulWidget {
  const CascaAluno({super.key, required this.estado, required this.usuario});
  final EstadoApp estado;
  final Usuario usuario;

  @override
  State<CascaAluno> createState() => _CascaAlunoState();
}

class _CascaAlunoState extends State<CascaAluno> {
  // Um view model para as duas seções: o pedido feito numa aparece na outra.
  late final DesempenhoViewModel _vm = DesempenhoViewModel(widget.estado.repos)..carregar();

  @override
  void dispose() {
    _vm.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Casca(
      usuario: widget.usuario,
      aoSair: widget.estado.sair,
      itens: const [
        ItemMenu('Meu desempenho', Icons.insights_outlined, Icons.insights),
        ItemMenu('Pedidos', Icons.mark_email_read_outlined, Icons.mark_email_read),
      ],
      paginas: [
        DesempenhoView(vm: _vm),
        PedidosView(vm: _vm),
      ],
    );
  }
}
