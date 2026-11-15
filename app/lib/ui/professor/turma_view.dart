import 'package:flutter/material.dart';

import '../../data/modelos.dart';
import '../../data/repositorios.dart';
import '../core/casca.dart';
import '../core/componentes.dart';
import '../core/dialogos.dart';
import '../core/formato.dart';
import '../core/tema.dart';
import 'matricula_view.dart';
import 'turma_view_model.dart';

class TurmaView extends StatefulWidget {
  const TurmaView({super.key, required this.repos, required this.turmaId, required this.titulo});
  final Repositorios repos;
  final int turmaId;
  final String titulo;

  @override
  State<TurmaView> createState() => _TurmaViewState();
}

class _TurmaViewState extends State<TurmaView> {
  late final TurmaViewModel _vm = TurmaViewModel(widget.repos, widget.turmaId)..carregar();

  @override
  void dispose() {
    _vm.dispose();
    super.dispose();
  }

  Future<void> _analisar() async {
    final msg = await _vm.analisarTurma();
    if (mounted) mostrarMensagem(context, msg);
  }

  Future<void> _abrirMatricula(EstudanteLinha e) async {
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => MatriculaView(
        repos: widget.repos,
        matriculaId: e.matriculaId,
        trilha: 'Turmas / ${widget.titulo}',
      ),
    ));
    _vm.carregar(silencioso: true);
  }

  Future<void> _editarNota(EstudanteLinha e, AvaliacaoInfo a) async {
    final valor = await dialogoNota(context,
        aluno: '${e.codigo} • ${e.aluno}',
        avaliacao: a.nome,
        atual: e.notas['${a.id}'],
        notaMaxima: a.notaMaxima);
    if (valor == null) return;
    final erro = await _vm.salvarNota(e.matriculaId, a.id, valor);
    if (!mounted) return;
    mostrarMensagem(context, erro ?? 'Nota salva. A análise anterior fica no histórico.', erro: erro != null);
  }

  Future<void> _presenca(EstudanteLinha e, int aulaId, bool presente) async {
    final erro = await _vm.salvarPresenca(e.matriculaId, aulaId, presente);
    if (erro != null && mounted) mostrarMensagem(context, erro, erro: true);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _vm,
      builder: (context, _) {
        final t = _vm.turma;
        if (t == null) {
          return Pagina(children: [
            CabecalhoPagina(titulo: widget.titulo, trilha: 'Turmas / ${widget.titulo}'),
            const SizedBox(height: 40),
            _vm.erro != null
                ? EstadoErro(mensagem: _vm.erro!, aoTentar: _vm.carregar)
                : const EstadoCarregando(),
          ]);
        }
        return Pagina(children: [
          CabecalhoPagina(
            trilha: 'Turmas / ${t.disciplina}',
            titulo: t.disciplina,
            subtitulo: '${t.periodo} • ${t.descricao} • ${t.estudantes.length} estudantes',
            acoes: [
              FilledButton.icon(
                onPressed: _vm.analisando ? null : _analisar,
                icon: _vm.analisando
                    ? const SizedBox(
                        width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.bar_chart, size: 20),
                label: Text(_vm.analisando ? 'Analisando...' : 'Analisar turma'),
              ),
            ],
          ),
          const SizedBox(height: 20),
          _Abas(
            indice: _vm.aba,
            rotulos: const ['Estudantes', 'Notas', 'Frequência', 'Critérios'],
            aoTrocar: _vm.trocarAba,
          ),
          const SizedBox(height: 18),
          switch (_vm.aba) {
            0 => _AbaEstudantes(turma: t, aoAbrir: _abrirMatricula),
            1 => _AbaNotas(turma: t, salvando: _vm.salvando, aoEditar: _editarNota),
            2 => _AbaFrequencia(
                turma: t,
                aulaId: _vm.aulaSelecionada,
                salvando: _vm.salvando,
                aoSelecionarAula: _vm.selecionarAula,
                aoMarcar: _presenca,
                aoTodosPresentes: (aulaId) async {
                  final msg = await _vm.todosPresentes(aulaId);
                  if (msg != null && context.mounted) mostrarMensagem(context, msg);
                },
              ),
            _ => _AbaCriterios(criterios: t.criterios),
          },
        ]);
      },
    );
  }
}

// ----------------------------------------------------------------- abas
class _Abas extends StatelessWidget {
  const _Abas({required this.indice, required this.rotulos, required this.aoTrocar});
  final int indice;
  final List<String> rotulos;
  final ValueChanged<int> aoTrocar;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: Cores.borda))),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          for (var i = 0; i < rotulos.length; i++)
            InkWell(
              onTap: () => aoTrocar(i),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
                margin: const EdgeInsets.only(right: 18),
                decoration: BoxDecoration(
                  border: Border(
                    bottom: BorderSide(color: i == indice ? Cores.vermelho : Colors.transparent, width: 2.5),
                  ),
                ),
                child: Text(rotulos[i],
                    style: TextStyle(
                        fontSize: 15,
                        fontWeight: i == indice ? FontWeight.w700 : FontWeight.w500,
                        color: i == indice ? Cores.vermelho : Cores.texto)),
              ),
            ),
        ]),
      ),
    );
  }
}

// ----------------------------------------------------------- estudantes
class _AbaEstudantes extends StatelessWidget {
  const _AbaEstudantes({required this.turma, required this.aoAbrir});
  final TurmaDetalhe turma;
  final void Function(EstudanteLinha) aoAbrir;

  @override
  Widget build(BuildContext context) {
    final largo = MediaQuery.sizeOf(context).width >= 760;
    final c = turma.criterios;
    final lista = largo ? _tabela() : _cartoes();
    final conferencias = turma.estudantes.fold<int>(0, (s, e) => s + e.conferenciasAbertas);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Cartao(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          lista,
          const Padding(
            padding: EdgeInsets.fromLTRB(18, 4, 18, 16),
            child: AvisoInfo(texto: 'Nota não lançada permanece como dado ausente, nunca como zero.'),
          ),
        ]),
      ),
      const SizedBox(height: 16),
      Wrap(spacing: 16, runSpacing: 16, children: [
        SizedBox(
          width: largo ? 420 : double.infinity,
          child: _CartaoInfo(
            icone: Icons.description_outlined,
            titulo: 'Critérios utilizados',
            linha: '${c.versao} • Média ${fmtNum(c.mediaMinima)} • Frequência ${fmtPct(c.frequenciaMinima)}',
            detalhe: 'Configuração aplicada para esta turma.',
          ),
        ),
        SizedBox(
          width: largo ? 420 : double.infinity,
          child: _CartaoInfo(
            icone: Icons.mark_email_unread_outlined,
            titulo: 'Pedidos de conferência',
            linha: conferencias == 0 ? 'Nenhum pedido aberto' : '$conferencias pedido(s) aberto(s)',
            detalhe: 'Abra a matrícula para ler e responder.',
          ),
        ),
      ]),
    ]);
  }

  Widget _tabela() {
    const cab = TextStyle(color: Cores.textoSuave, fontWeight: FontWeight.w600, fontSize: 13);
    return LayoutBuilder(builder: (context, c) {
      return SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: ConstrainedBox(
          constraints: BoxConstraints(minWidth: c.maxWidth),
          child: DataTable(
            showCheckboxColumn: false,
            headingRowColor: WidgetStateProperty.all(Cores.fundo),
            headingRowHeight: 48,
            dataRowMinHeight: 58,
            dataRowMaxHeight: 72,
            columns: const [
              DataColumn(label: Text('Estudante', style: cab)),
              DataColumn(label: Text('Média', style: cab)),
              DataColumn(label: Text('Frequência', style: cab)),
              DataColumn(label: Text('Completude', style: cab)),
              DataColumn(label: Text('Acompanhamento', style: cab)),
              DataColumn(label: Text('')),
            ],
            rows: [
              for (final e in turma.estudantes)
                DataRow(onSelectChanged: (_) => aoAbrir(e), cells: [
                  DataCell(Row(mainAxisSize: MainAxisSize.min, children: [
                    Text('${e.codigo}  •  ${e.aluno}', style: const TextStyle(fontWeight: FontWeight.w500)),
                    if (e.conferenciasAbertas > 0) ...[
                      const SizedBox(width: 8),
                      const Tooltip(
                        message: 'Pedido de conferência aberto',
                        child: Icon(Icons.mark_email_unread_outlined, size: 18, color: Cores.azul),
                      ),
                    ],
                  ])),
                  DataCell(Text(fmtNum(e.media))),
                  DataCell(Text(fmtPct(e.frequencia))),
                  DataCell(Text(e.completude == 'completa' ? 'Completa' : 'Parcial')),
                  DataCell(ChipAcompanhamento(
                    prioridade: e.acompanhamento?.prioridade,
                    desatualizada: e.acompanhamento?.desatualizada ?? false,
                  )),
                  DataCell(IconButton(
                    tooltip: 'Ver análise e registros',
                    icon: const Icon(Icons.visibility_outlined),
                    onPressed: () => aoAbrir(e),
                  )),
                ]),
            ],
          ),
        ),
      );
    });
  }

  Widget _cartoes() {
    return Column(children: [
      for (final e in turma.estudantes) ...[
        ListTile(
          onTap: () => aoAbrir(e),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          title: Text('${e.codigo} • ${e.aluno}', style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Média ${fmtNum(e.media)} • Frequência ${fmtPct(e.frequencia)} • '
                  '${e.completude == 'completa' ? 'Completa' : 'Parcial'}'),
              const SizedBox(height: 8),
              ChipAcompanhamento(
                prioridade: e.acompanhamento?.prioridade,
                desatualizada: e.acompanhamento?.desatualizada ?? false,
              ),
            ]),
          ),
          trailing: const Icon(Icons.chevron_right),
        ),
        const Divider(height: 1),
      ],
    ]);
  }
}

class _CartaoInfo extends StatelessWidget {
  const _CartaoInfo({required this.icone, required this.titulo, required this.linha, required this.detalhe});
  final IconData icone;
  final String titulo;
  final String linha;
  final String detalhe;

  @override
  Widget build(BuildContext context) {
    return Cartao(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: Cores.fundo, borderRadius: BorderRadius.circular(10)),
            child: Icon(icone),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(titulo, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15.5)),
              const SizedBox(height: 4),
              Text(linha),
              Text(detalhe, style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- notas
class _AbaNotas extends StatelessWidget {
  const _AbaNotas({required this.turma, required this.salvando, required this.aoEditar});
  final TurmaDetalhe turma;
  final Set<String> salvando;
  final void Function(EstudanteLinha, AvaliacaoInfo) aoEditar;

  @override
  Widget build(BuildContext context) {
    const cab = TextStyle(color: Cores.textoSuave, fontWeight: FontWeight.w600, fontSize: 13);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Cartao(
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowColor: WidgetStateProperty.all(Cores.fundo),
            columns: [
              const DataColumn(label: Text('Estudante', style: cab)),
              for (final a in turma.avaliacoes)
                DataColumn(
                  label: Text('${a.nome}\npeso ${fmtNum(a.peso)}', style: cab),
                  numeric: true,
                ),
              const DataColumn(label: Text('Média', style: cab), numeric: true),
            ],
            rows: [
              for (final e in turma.estudantes)
                DataRow(cells: [
                  DataCell(Text('${e.codigo} • ${e.aluno}')),
                  for (final a in turma.avaliacoes)
                    DataCell(
                      salvando.contains('n${e.matriculaId}-${a.id}')
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                          : _CelulaNota(valor: e.notas['${a.id}']),
                      onTap: () => aoEditar(e, a),
                    ),
                  DataCell(Text(fmtNum(e.media), style: const TextStyle(fontWeight: FontWeight.w700))),
                ]),
            ],
          ),
        ),
      ),
      const SizedBox(height: 12),
      const AvisoInfo(
        texto: 'Toque em uma nota para lançar ou corrigir. Valores fora da escala são rejeitados, '
            'e cada correção gera nova versão do registro.',
      ),
    ]);
  }
}

class _CelulaNota extends StatelessWidget {
  const _CelulaNota({required this.valor});
  final double? valor;

  @override
  Widget build(BuildContext context) {
    if (valor == null) {
      return const Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.add_circle_outline, size: 16, color: Cores.vermelho),
        SizedBox(width: 4),
        Text('Não lançada', style: TextStyle(color: Cores.vermelho, fontWeight: FontWeight.w600)),
      ]);
    }
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Text(fmtNum(valor)),
      const SizedBox(width: 6),
      const Icon(Icons.edit_outlined, size: 14, color: Cores.textoSuave),
    ]);
  }
}

// ----------------------------------------------------------- frequência
class _AbaFrequencia extends StatelessWidget {
  const _AbaFrequencia({
    required this.turma,
    required this.aulaId,
    required this.salvando,
    required this.aoSelecionarAula,
    required this.aoMarcar,
    required this.aoTodosPresentes,
  });

  final TurmaDetalhe turma;
  final int? aulaId;
  final Set<String> salvando;
  final ValueChanged<int?> aoSelecionarAula;
  final void Function(EstudanteLinha, int, bool) aoMarcar;
  final void Function(int) aoTodosPresentes;

  @override
  Widget build(BuildContext context) {
    if (turma.aulas.isEmpty) {
      return const EstadoVazio(texto: 'Nenhuma aula registrada nesta turma.');
    }
    final aula = turma.aulas.firstWhere((a) => a.id == aulaId, orElse: () => turma.aulas.last);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Secao(
        titulo: 'Chamada rápida',
        subtitulo: 'Escolha a aula e marque presença ou falta. Cada toque já é salvo.',
        acao: OutlinedButton.icon(
          onPressed: () => aoTodosPresentes(aula.id),
          icon: const Icon(Icons.done_all, size: 18),
          label: const Text('Todos presentes'),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          DropdownButtonFormField<int>(
            value: aula.id,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Aula'),
            items: [
              for (final a in turma.aulas.reversed)
                DropdownMenuItem(
                  value: a.id,
                  child: Text('Aula ${a.ordem} • ${fmtData(a.data)} • ${a.tema}', overflow: TextOverflow.ellipsis),
                ),
            ],
            onChanged: aoSelecionarAula,
          ),
          const SizedBox(height: 12),
          for (final e in turma.estudantes)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(children: [
                Expanded(child: Text('${e.codigo} • ${e.aluno}')),
                if (salvando.contains('p${e.matriculaId}-${aula.id}'))
                  const Padding(
                    padding: EdgeInsets.only(right: 10),
                    child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                  ),
                SegmentedButton<bool>(
                  showSelectedIcon: false,
                  emptySelectionAllowed: true,
                  segments: const [
                    ButtonSegment(value: true, label: Text('Presente')),
                    ButtonSegment(value: false, label: Text('Falta')),
                  ],
                  selected: {
                    if (e.presencas['${aula.id}'] != null) e.presencas['${aula.id}']!,
                  },
                  onSelectionChanged: (s) {
                    if (s.isNotEmpty) aoMarcar(e, aula.id, s.first);
                  },
                ),
              ]),
            ),
        ]),
      ),
      const SizedBox(height: 16),
      Secao(
        titulo: 'Frequência acumulada',
        child: Column(children: [
          for (final e in turma.estudantes)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${e.codigo} • ${e.aluno}')),
                  Text(
                    e.frequencia == null
                        ? 'Não avaliável'
                        : '${fmtPct(e.frequencia)}  (${e.presentes} de ${e.registradas})',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: (e.frequencia != null && e.frequencia! < turma.criterios.frequenciaMinima)
                          ? Cores.vermelho
                          : Cores.texto,
                    ),
                  ),
                ]),
                const SizedBox(height: 6),
                LinearProgressIndicator(
                  value: (e.frequencia ?? 0) / 100,
                  minHeight: 6,
                  borderRadius: BorderRadius.circular(4),
                  backgroundColor: Cores.cinzaClaro,
                  color: (e.frequencia != null && e.frequencia! < turma.criterios.frequenciaMinima)
                      ? Cores.vermelho
                      : Cores.texto,
                ),
                if (e.pendencias.any((p) => p.indicador == 'frequencia'))
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      e.pendencias.firstWhere((p) => p.indicador == 'frequencia').motivo,
                      style: const TextStyle(color: Cores.vermelho, fontSize: 12.5),
                    ),
                  ),
              ]),
            ),
        ]),
      ),
    ]);
  }
}

// ------------------------------------------------------------- critérios
class _AbaCriterios extends StatelessWidget {
  const _AbaCriterios({required this.criterios});
  final Criterios criterios;

  @override
  Widget build(BuildContext context) {
    final c = criterios;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Secao(
        titulo: 'Perfil ${c.versao}',
        subtitulo: c.descricao,
        child: Wrap(spacing: 16, runSpacing: 16, children: [
          SizedBox(
            width: 260,
            child: CartaoIndicador(
                titulo: 'Média mínima', valor: fmtNum(c.mediaMinima), icone: Icons.description_outlined),
          ),
          SizedBox(
            width: 260,
            child: CartaoIndicador(
                titulo: 'Frequência mínima', valor: fmtPct(c.frequenciaMinima), icone: Icons.person_outline),
          ),
        ]),
      ),
      const SizedBox(height: 16),
      Secao(
        titulo: 'Base de regras',
        subtitulo: 'As condições usam "menor que": média exatamente 6,0 não aciona R1.',
        child: Column(children: [
          for (final r in descricaoRegra.entries)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                backgroundColor: Cores.fundo,
                child: Text(r.key, style: const TextStyle(fontWeight: FontWeight.w800, color: Cores.texto)),
              ),
              title: Text(r.value),
            ),
          const SizedBox(height: 8),
          const AvisoInfo(
            texto: 'Ordem de inferência: R4 (completude) antes das demais; R1 e R2 viram fatos; '
                'R3 é derivada por encadeamento para a frente; R5 cuida do histórico.',
          ),
        ]),
      ),
    ]);
  }
}
