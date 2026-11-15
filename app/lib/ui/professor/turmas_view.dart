import 'package:flutter/material.dart';

import '../../data/api_client.dart';
import '../../data/modelos.dart';
import '../../data/repositorios.dart';
import '../core/casca.dart';
import '../core/componentes.dart';
import '../core/tema.dart';
import 'turma_view.dart';

class TurmasViewModel extends ChangeNotifier {
  TurmasViewModel(this._repos);
  final Repositorios _repos;

  List<TurmaResumo> turmas = [];
  bool carregando = true;
  String? erro;

  Future<void> carregar() async {
    carregando = true;
    erro = null;
    notifyListeners();
    try {
      turmas = await _repos.turmas.listar();
    } on ApiException catch (e) {
      erro = e.mensagem;
    } finally {
      carregando = false;
      notifyListeners();
    }
  }
}

class TurmasView extends StatefulWidget {
  const TurmasView({super.key, required this.repos});
  final Repositorios repos;

  @override
  State<TurmasView> createState() => _TurmasViewState();
}

class _TurmasViewState extends State<TurmasView> {
  late final TurmasViewModel _vm = TurmasViewModel(widget.repos)..carregar();

  @override
  void dispose() {
    _vm.dispose();
    super.dispose();
  }

  Future<void> _abrir(TurmaResumo t) async {
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => TurmaView(repos: widget.repos, turmaId: t.id, titulo: t.disciplina),
    ));
    _vm.carregar();   // volta com contadores atualizados
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _vm,
      builder: (context, _) {
        Widget corpo;
        if (_vm.carregando && _vm.turmas.isEmpty) {
          corpo = const Padding(padding: EdgeInsets.only(top: 80), child: EstadoCarregando());
        } else if (_vm.erro != null) {
          corpo = EstadoErro(mensagem: _vm.erro!, aoTentar: _vm.carregar);
        } else if (_vm.turmas.isEmpty) {
          corpo = const EstadoVazio(texto: 'Nenhuma turma vinculada ao seu perfil.');
        } else {
          corpo = LayoutBuilder(builder: (context, c) {
            final colunas = c.maxWidth >= 1000 ? 3 : (c.maxWidth >= 640 ? 2 : 1);
            final largura = (c.maxWidth - (colunas - 1) * 16) / colunas;
            return Wrap(spacing: 16, runSpacing: 16, children: [
              for (final t in _vm.turmas)
                SizedBox(width: largura, child: _CartaoTurma(turma: t, aoAbrir: () => _abrir(t))),
            ]);
          });
        }
        return Pagina(children: [
          CabecalhoPagina(
            titulo: 'Turmas',
            subtitulo: 'Turmas vinculadas ao seu perfil',
            acoes: [
              OutlinedButton.icon(
                onPressed: _vm.carregando ? null : _vm.carregar,
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Atualizar'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          corpo,
        ]);
      },
    );
  }
}

class _CartaoTurma extends StatelessWidget {
  const _CartaoTurma({required this.turma, required this.aoAbrir});
  final TurmaResumo turma;
  final VoidCallback aoAbrir;

  @override
  Widget build(BuildContext context) {
    final t = turma;
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: aoAbrir,
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Cores.borda),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                child: Text(t.disciplina,
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              ),
              const Icon(Icons.chevron_right, color: Cores.textoSuave),
            ]),
            const SizedBox(height: 4),
            Text('${t.periodo} • ${t.descricao} • ${t.estudantes} estudantes',
                style: const TextStyle(color: Cores.textoSuave)),
            const SizedBox(height: 16),
            Wrap(spacing: 8, runSpacing: 8, children: [
              if (t.alertas > 0)
                EtiquetaPequena(
                    texto: '${t.alertas} com alerta', cor: Cores.vermelho, fundo: Cores.vermelhoClaro),
              if (t.pendencias > 0)
                EtiquetaPequena(
                    texto: '${t.pendencias} com pendência', cor: Cores.ambar, fundo: Cores.ambarClaro),
              if (t.conferenciasAbertas > 0)
                EtiquetaPequena(
                    texto: '${t.conferenciasAbertas} pedido(s) de conferência',
                    cor: Cores.azul,
                    fundo: Cores.azulClaro),
              if (t.semAnaliseAtual > 0)
                EtiquetaPequena(
                    texto: '${t.semAnaliseAtual} sem análise atual',
                    cor: Cores.textoSuave,
                    fundo: Cores.cinzaClaro),
              if (t.alertas + t.pendencias + t.conferenciasAbertas + t.semAnaliseAtual == 0)
                const EtiquetaPequena(texto: 'Tudo em dia', cor: Cores.verde, fundo: Cores.verdeClaro),
            ]),
            const SizedBox(height: 14),
            Text('Critérios ${t.criterios}', style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
          ]),
        ),
      ),
    );
  }
}
