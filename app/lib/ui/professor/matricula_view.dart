import 'package:flutter/material.dart';

import '../../data/modelos.dart';
import '../../data/repositorios.dart';
import '../core/casca.dart';
import '../core/componentes.dart';
import '../core/dialogos.dart';
import '../core/formato.dart';
import '../core/tema.dart';
import 'matricula_view_model.dart';

/// Telas "Análise e motivos" e "Revisão e histórico" de uma matrícula.
class MatriculaView extends StatefulWidget {
  const MatriculaView({super.key, required this.repos, required this.matriculaId, this.trilha});
  final Repositorios repos;
  final int matriculaId;
  final String? trilha;

  @override
  State<MatriculaView> createState() => _MatriculaViewState();
}

class _MatriculaViewState extends State<MatriculaView> {
  late final MatriculaViewModel _vm = MatriculaViewModel(widget.repos, widget.matriculaId)..carregar();

  @override
  void dispose() {
    _vm.dispose();
    super.dispose();
  }

  void _avisar(String? erro, String sucesso) {
    if (!mounted) return;
    mostrarMensagem(context, erro ?? sucesso, erro: erro != null);
  }

  Future<void> _analisar() async => _avisar(await _vm.analisar(), 'Nova análise gravada.');

  Future<void> _editarNota(RegistroNota n, Registros r) async {
    final v = await dialogoNota(context,
        aluno: '${r.codigo} • ${r.aluno}', avaliacao: n.nome, atual: n.valor, notaMaxima: n.notaMaxima);
    if (v == null) return;
    _avisar(await _vm.salvarNota(n.avaliacaoId, v), 'Nota salva. Peça uma nova análise para atualizar os alertas.');
  }

  Future<void> _responder(Conferencia c) async {
    final texto = await dialogoTexto(context,
        titulo: 'Responder pedido',
        rotulo: 'Resposta ao aluno',
        contexto: '${c.referenciaRotulo}: "${c.mensagem}"',
        botao: 'Responder',
        minimo: 2);
    if (texto == null) return;
    _avisar(await _vm.responder(c.id, texto), 'Resposta enviada.');
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _vm,
      builder: (context, _) {
        final r = _vm.registros;
        if (r == null) {
          return Pagina(children: [
            const SizedBox(height: 60),
            _vm.erro != null
                ? EstadoErro(mensagem: _vm.erro!, aoTentar: _vm.carregar)
                : const EstadoCarregando(),
          ]);
        }
        final largo = MediaQuery.sizeOf(context).width >= 1100;
        final analise = _SecaoAnalise(vm: _vm, aoAnalisar: _analisar);
        final revisao = _SecaoRevisao(vm: _vm, aoAvisar: _avisar);
        return Pagina(children: [
          CabecalhoPagina(
            trilha: widget.trilha == null ? null : '${widget.trilha} / ${r.codigo}',
            titulo: r.aluno,
            subtitulo: '${r.codigo} • ${r.disciplina} ${r.periodo} • registros v${r.versaoRegistros}',
            acoes: [
              FilledButton.icon(
                onPressed: _vm.analisando ? null : _analisar,
                icon: _vm.analisando
                    ? const SizedBox(
                        width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.psychology_outlined, size: 20),
                label: Text(_vm.analisando ? 'Analisando...' : 'Analisar agora'),
              ),
            ],
          ),
          const SizedBox(height: 20),
          _Indicadores(r: r),
          const SizedBox(height: 16),
          if (largo)
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(flex: 3, child: analise),
              const SizedBox(width: 16),
              Expanded(flex: 2, child: revisao),
            ])
          else ...[
            analise,
            const SizedBox(height: 16),
            revisao,
          ],
          const SizedBox(height: 16),
          _SecaoRegistros(
            r: r,
            aoEditarNota: (n) => _editarNota(n, r),
            aoPresenca: (aulaId, p) async {
              _avisar(await _vm.salvarPresenca(aulaId, p), 'Presença salva.');
            },
            aoEntrega: (atividadeId, entregue) async {
              _avisar(await _vm.marcarEntrega(atividadeId, entregue),
                  entregue ? 'Entrega registrada com a data de hoje.' : 'Entrega desmarcada.');
            },
          ),
          const SizedBox(height: 16),
          _SecaoConferencias(itens: _vm.conferencias, aoResponder: _responder),
          const SizedBox(height: 16),
          _SecaoHistorico(analises: _vm.analises, alteracoes: _vm.historico),
          const SizedBox(height: 24),
        ]);
      },
    );
  }
}

// ------------------------------------------------------------- indicadores
class _Indicadores extends StatelessWidget {
  const _Indicadores({required this.r});
  final Registros r;

  @override
  Widget build(BuildContext context) {
    final i = r.indicadores;
    final pendMedia = i.pendencias.any((p) => p.indicador == 'media');
    final pendFreq = i.pendencias.any((p) => p.indicador == 'frequencia');
    final cartoes = [
      CartaoIndicador(
        titulo: 'Média atual',
        valor: fmtNum(i.media),
        icone: Icons.bar_chart,
        subtitulo: pendMedia ? 'Não avaliável: falta nota' : 'Média ponderada das avaliações',
      ),
      CartaoIndicador(
        titulo: 'Frequência',
        valor: fmtPct(i.frequencia),
        icone: Icons.person_outline,
        subtitulo: pendFreq
            ? 'Não avaliável: presença sem registro'
            : '${i.presencas} de ${i.unidadesConsideradas} unidades-aula com presença',
      ),
      CartaoIndicador(
        titulo: 'Entregas',
        valor: i.atividadesVencidas == 0 ? '—' : fmtPct(i.taxaEntrega),
        icone: Icons.assignment_turned_in_outlined,
        subtitulo: i.atividadesVencidas == 0
            ? 'Nenhuma atividade vencida'
            : '${i.atividadesSemEntrega} de ${i.atividadesVencidas} vencidas sem entrega',
      ),
      CartaoIndicador(
        titulo: 'Completude',
        valor: i.completude == 'completa' ? 'Completa' : 'Parcial',
        icone: Icons.fact_check_outlined,
        subtitulo: i.pendencias.isEmpty ? 'Todos os dados lançados' : '${i.pendencias.length} pendência(s)',
      ),
    ];
    return LayoutBuilder(builder: (context, c) {
      if (c.maxWidth < 700) {
        return Column(children: [
          for (final w in cartoes) Padding(padding: const EdgeInsets.only(bottom: 12), child: w),
        ]);
      }
      if (c.maxWidth < 1000) {
        final largura = (c.maxWidth - 16) / 2;
        return Wrap(spacing: 16, runSpacing: 16, children: [
          for (final w in cartoes) SizedBox(width: largura, child: w),
        ]);
      }
      return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        for (var k = 0; k < cartoes.length; k++) ...[
          if (k > 0) const SizedBox(width: 16),
          Expanded(child: cartoes[k]),
        ],
      ]);
    });
  }
}

// ---------------------------------------------------------------- análise
class _SecaoAnalise extends StatelessWidget {
  const _SecaoAnalise({required this.vm, required this.aoAnalisar});
  final MatriculaViewModel vm;
  final VoidCallback aoAnalisar;

  @override
  Widget build(BuildContext context) {
    final a = vm.atual;
    if (a == null) {
      return Secao(
        titulo: 'Análise e motivos',
        child: Column(children: [
          const EstadoVazio(
            texto: 'Ainda não há análise para esta matrícula.\n'
                'O assistente calcula os indicadores com os dados do servidor e explica cada alerta.',
            icone: Icons.psychology_outlined,
          ),
          FilledButton(onPressed: vm.analisando ? null : aoAnalisar, child: const Text('Analisar agora')),
        ]),
      );
    }
    final regrasAlerta = a.acionadas.where((x) => x.regra != 'R5').toList();
    final r5 = a.acionadas.where((x) => x.regra == 'R5').toList();
    return Secao(
      titulo: 'Análise e motivos',
      subtitulo: 'Análise #${a.id} • ${fmtDataHora(a.criadoEm)} • por ${a.solicitadoPor}',
      acao: ChipAcompanhamento(prioridade: a.prioridade, desatualizada: a.desatualizada),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (a.desatualizada)
          _Faixa(
            cor: Cores.azul,
            fundo: Cores.azulClaro,
            icone: Icons.update,
            texto: 'Os registros mudaram depois desta análise (usou a versão v${a.versaoRegistros}). '
                'Ela continua no histórico, mas peça uma nova análise antes de decidir (R5).',
          ),
        if (a.desatualizada) const SizedBox(height: 12),
        // Motivo: dado + critério, sem adivinhar causa.
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: a.prioridade == 'sem_alerta' ? Cores.fundo : Cores.vermelhoClaro,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(a.prioridade == 'sem_alerta' ? Icons.check_circle_outline : Icons.report_outlined,
                color: a.prioridade == 'sem_alerta' ? Cores.verde : Cores.vermelho),
            const SizedBox(width: 10),
            Expanded(child: Text(a.motivo, style: const TextStyle(fontSize: 15, height: 1.45))),
          ]),
        ),
        const SizedBox(height: 16),
        BarraCerteza(valor: a.certeza),
        const SizedBox(height: 18),
        const Text('Regras acionadas', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        if (regrasAlerta.isEmpty && a.pendencias.isEmpty)
          const Text('Nenhuma regra de alerta foi acionada.', style: TextStyle(color: Cores.textoSuave)),
        for (final x in regrasAlerta)
          _LinhaRegra(regra: x.regra, evidencia: _evidencia(x), fc: x.fc),
        for (final p in a.pendencias)
          _LinhaRegra(
            regra: 'R4',
            evidencia: '${p.indicador == 'media' ? 'Média' : 'Frequência'} não avaliável: ${p.motivo}',
          ),
        for (final x in r5)
          _LinhaRegra(
            regra: 'R5',
            evidencia: 'Registros v${x.evidencia['versao_registros_anterior']} → '
                'v${x.evidencia['versao_registros_atual']} desde a análise #${x.evidencia['analise_anterior_id']}, '
                'que foi mantida no histórico.',
          ),
        const SizedBox(height: 14),
        Wrap(spacing: 8, runSpacing: 8, children: [
          EtiquetaPequena(texto: 'Critérios ${a.versaoCriterios}', cor: Cores.texto, fundo: Cores.cinzaClaro),
          EtiquetaPequena(
              texto: 'Média mín. ${fmtNum(a.mediaMinima)} • Freq. mín. ${fmtPct(a.frequenciaMinima)}',
              cor: Cores.texto,
              fundo: Cores.cinzaClaro),
          EtiquetaPequena(texto: 'Até ${a.atrasosMaximos} sem entrega', cor: Cores.texto, fundo: Cores.cinzaClaro),
          EtiquetaPequena(texto: 'Registros v${a.versaoRegistros}', cor: Cores.texto, fundo: Cores.cinzaClaro),
        ]),
        const SizedBox(height: 14),
        _Sintese(a: a),
      ]),
    );
  }

  String _evidencia(RegraAcionada x) {
    final ev = x.evidencia;
    if (ev['derivado_de'] != null) {
      return 'Derivada de R1 e R2 (alerta de média + alerta de frequência).';
    }
    final partes = <String>[];
    for (final v in ev.values) {
      if (v is Map && v['indicador'] == 'entregas') {
        partes.add('${v['valor']} atividades vencidas sem entrega > limite de ${v['limite']}');
      } else if (v is Map) {
        final ind = v['indicador'] == 'media' ? 'Média' : 'Frequência';
        final valor = (v['valor'] as num).toDouble();
        final limite = (v['limite'] as num).toDouble();
        final ehMedia = v['indicador'] == 'media';
        final txtValor = ehMedia ? fmtNum(valor) : fmtPct(valor);
        final txtLimite = ehMedia ? fmtNum(limite) : fmtPct(limite);
        partes.add('$ind $txtValor < $txtLimite');
      }
    }
    return partes.join('; ');
  }
}

class _LinhaRegra extends StatelessWidget {
  const _LinhaRegra({required this.regra, required this.evidencia, this.fc});
  final String regra;
  final String evidencia;
  final double? fc;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: 38,
          padding: const EdgeInsets.symmetric(vertical: 4),
          alignment: Alignment.center,
          decoration: BoxDecoration(color: Cores.texto, borderRadius: BorderRadius.circular(6)),
          child: Text(regra, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12.5)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(descricaoRegra[regra] ?? regra, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 2),
            Text(evidencia, style: const TextStyle(color: Cores.textoSuave)),
          ]),
        ),
        if (fc != null)
          Padding(
            padding: const EdgeInsets.only(left: 8),
            child: Tooltip(
              message: 'Fator de certeza desta conclusão',
              child: EtiquetaPequena(texto: 'FC ${fmtCerteza(fc!)}', cor: Cores.texto, fundo: Cores.cinzaClaro),
            ),
          ),
      ]),
    );
  }
}

class _Sintese extends StatelessWidget {
  const _Sintese({required this.a});
  final Analise a;

  @override
  Widget build(BuildContext context) {
    final s = a.sintese;
    if (s != null) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          border: Border.all(color: Cores.borda),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.auto_awesome_outlined, size: 18, color: Cores.textoSuave),
            SizedBox(width: 6),
            Text('Síntese auxiliar (Gemini, conferida pela API)',
                style: TextStyle(fontWeight: FontWeight.w600, color: Cores.textoSuave)),
          ]),
          const SizedBox(height: 8),
          Text(s, style: const TextStyle(height: 1.45)),
        ]),
      );
    }
    final st = a.sinteseStatus;
    final String texto;
    if (st.startsWith('descartada')) {
      texto = 'Síntese em texto descartada na conferência (${st.replaceFirst('descartada: ', '')}). '
          'Vale o relatório estruturado acima.';
    } else if (st.startsWith('indisponivel')) {
      texto = 'Serviço de síntese indisponível agora. Vale o relatório estruturado acima.';
    } else {
      texto = 'Síntese em texto desativada. O relatório estruturado acima é completo.';
    }
    return AvisoInfo(texto: texto, icone: Icons.auto_awesome_outlined);
  }
}

class _Faixa extends StatelessWidget {
  const _Faixa({required this.cor, required this.fundo, required this.icone, required this.texto});
  final Color cor;
  final Color fundo;
  final IconData icone;
  final String texto;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: fundo, borderRadius: BorderRadius.circular(10)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icone, color: cor, size: 20),
        const SizedBox(width: 8),
        Expanded(child: Text(texto, style: TextStyle(color: cor))),
      ]),
    );
  }
}

// ---------------------------------------------------------------- revisão
class _SecaoRevisao extends StatefulWidget {
  const _SecaoRevisao({required this.vm, required this.aoAvisar});
  final MatriculaViewModel vm;
  final void Function(String?, String) aoAvisar;

  @override
  State<_SecaoRevisao> createState() => _SecaoRevisaoState();
}

class _SecaoRevisaoState extends State<_SecaoRevisao> {
  final _obs = TextEditingController();
  String _decisao = 'confirmado';

  @override
  void dispose() {
    _obs.dispose();
    super.dispose();
  }

  Future<void> _registrar() async {
    if (_obs.text.trim().length < 3) {
      widget.aoAvisar('Escreva uma observação de pelo menos 3 caracteres.', '');
      return;
    }
    final erro = await widget.vm.revisar(_decisao, _obs.text.trim());
    if (erro == null) _obs.clear();
    widget.aoAvisar(erro, 'Revisão registrada com autor e data.');
  }

  @override
  Widget build(BuildContext context) {
    final a = widget.vm.atual;
    return Secao(
      titulo: 'Revisão do professor',
      subtitulo: 'O assistente não decide nem altera notas. A decisão é sua.',
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (a == null)
          const Text('Faça uma análise para poder registrar a revisão.', style: TextStyle(color: Cores.textoSuave))
        else ...[
          DropdownButtonFormField<String>(
            value: _decisao,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Decisão'),
            items: [
              for (final e in rotuloDecisao.entries) DropdownMenuItem(value: e.key, child: Text(e.value)),
            ],
            onChanged: (v) => setState(() => _decisao = v ?? _decisao),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _obs,
            maxLines: 3,
            maxLength: 1000,
            decoration: const InputDecoration(
              labelText: 'Observação',
              hintText: 'Ex.: conversar com a aluna após a aula; conferir a Avaliação 2.',
              alignLabelWithHint: true,
            ),
          ),
          FilledButton(
            onPressed: widget.vm.revisando ? null : _registrar,
            child: Text(widget.vm.revisando ? 'Registrando...' : 'Registrar revisão'),
          ),
          if (a.revisoes.isNotEmpty) ...[
            const SizedBox(height: 18),
            Text('Revisões desta análise (${a.revisoes.length})', style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            for (final rv in a.revisoes.reversed)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${rotuloDecisao[rv.decisao] ?? rv.decisao} • ${rv.autor}',
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  Text(rv.observacao),
                  Text(fmtDataHora(rv.criadoEm), style: const TextStyle(color: Cores.textoSuave, fontSize: 12)),
                ]),
              ),
          ],
        ],
      ]),
    );
  }
}

// --------------------------------------------------------------- registros
class _SecaoRegistros extends StatefulWidget {
  const _SecaoRegistros({
    required this.r,
    required this.aoEditarNota,
    required this.aoPresenca,
    required this.aoEntrega,
  });
  final Registros r;
  final void Function(RegistroNota) aoEditarNota;
  final void Function(int, bool) aoPresenca;
  final void Function(int, bool) aoEntrega;

  @override
  State<_SecaoRegistros> createState() => _SecaoRegistrosState();
}

class _SecaoRegistrosState extends State<_SecaoRegistros> {
  bool _verAulas = false;

  @override
  Widget build(BuildContext context) {
    final r = widget.r;
    return Secao(
      titulo: 'Registros',
      subtitulo: 'Corrigir um registro gera nova versão; a análise anterior fica no histórico.',
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Text('Avaliações', style: TextStyle(fontWeight: FontWeight.w700)),
        for (final n in r.avaliacoes)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(n.nome),
            subtitle: Text('Peso ${fmtNum(n.peso)} • ${n.obrigatoria ? 'obrigatória' : 'opcional'}'),
            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
              Text(
                n.valor == null ? 'Não lançada' : fmtNum(n.valor),
                style: TextStyle(
                    fontWeight: FontWeight.w700, color: n.valor == null ? Cores.vermelho : Cores.texto),
              ),
              IconButton(
                tooltip: n.valor == null ? 'Lançar nota' : 'Corrigir nota',
                icon: const Icon(Icons.edit_outlined),
                onPressed: () => widget.aoEditarNota(n),
              ),
            ]),
          ),
        const Divider(),
        const Text('Atividades', style: TextStyle(fontWeight: FontWeight.w700)),
        if (r.atividades.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text('Nenhuma atividade nesta turma.', style: TextStyle(color: Cores.textoSuave)),
          ),
        for (final a in r.atividades)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(a.titulo),
                  Text(
                    'Prazo ${fmtData(a.prazo)}${a.entregueEm != null ? ' • entregue em ${fmtData(a.entregueEm!)}' : ''}',
                    style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5),
                  ),
                ]),
              ),
              ChipSituacao(situacao: a.situacao),
              Tooltip(
                message: 'Marcar como entregue',
                child: Checkbox(value: a.entregue, onChanged: (v) => widget.aoEntrega(a.atividadeId, v ?? false)),
              ),
            ]),
          ),
        const Divider(),
        Row(children: [
          const Expanded(child: Text('Presenças', style: TextStyle(fontWeight: FontWeight.w700))),
          TextButton(
            onPressed: () => setState(() => _verAulas = !_verAulas),
            child: Text(_verAulas ? 'Ocultar aulas' : 'Ver aulas (${r.aulas.length})'),
          ),
        ]),
        Text(
          '${r.aulas.where((a) => a.presente == true).length} presenças, '
          '${r.aulas.where((a) => a.presente == false).length} faltas, '
          '${r.aulas.where((a) => a.presente == null).length} sem registro',
          style: const TextStyle(color: Cores.textoSuave),
        ),
        if (_verAulas)
          for (final a in r.aulas.reversed)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(children: [
                Expanded(child: Text('Aula ${a.ordem} • ${fmtData(a.data)} • ${a.tema}', overflow: TextOverflow.ellipsis)),
                SegmentedButton<bool>(
                  showSelectedIcon: false,
                  emptySelectionAllowed: true,
                  segments: const [
                    ButtonSegment(value: true, label: Text('P')),
                    ButtonSegment(value: false, label: Text('F')),
                  ],
                  selected: {if (a.presente != null) a.presente!},
                  onSelectionChanged: (s) {
                    if (s.isNotEmpty) widget.aoPresenca(a.aulaId, s.first);
                  },
                ),
              ]),
            ),
      ]),
    );
  }
}

// ----------------------------------------------------------- conferências
class _SecaoConferencias extends StatelessWidget {
  const _SecaoConferencias({required this.itens, required this.aoResponder});
  final List<Conferencia> itens;
  final void Function(Conferencia) aoResponder;

  @override
  Widget build(BuildContext context) {
    return Secao(
      titulo: 'Pedidos de conferência do aluno',
      subtitulo: 'O pedido fica ligado ao registro e não altera nenhuma nota.',
      child: itens.isEmpty
          ? const Text('Nenhum pedido.', style: TextStyle(color: Cores.textoSuave))
          : Column(children: [
              for (final c in itens)
                Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: c.aberta ? Cores.azulClaro : Cores.fundo,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(
                        child: Text('${c.referenciaRotulo} • ${c.autor}',
                            style: const TextStyle(fontWeight: FontWeight.w700)),
                      ),
                      EtiquetaPequena(
                        texto: c.aberta ? 'Aberto' : 'Respondido',
                        cor: c.aberta ? Cores.azul : Cores.verde,
                        fundo: c.aberta ? Colors.white : Cores.verdeClaro,
                      ),
                    ]),
                    const SizedBox(height: 6),
                    Text('"${c.mensagem}"'),
                    Text(fmtDataHora(c.criadoEm), style: const TextStyle(color: Cores.textoSuave, fontSize: 12)),
                    if (c.resposta != null) ...[
                      const SizedBox(height: 8),
                      Text('Resposta: ${c.resposta}', style: const TextStyle(fontWeight: FontWeight.w500)),
                    ],
                    if (c.aberta) ...[
                      const SizedBox(height: 8),
                      OutlinedButton(onPressed: () => aoResponder(c), child: const Text('Responder')),
                    ],
                  ]),
                ),
            ]),
    );
  }
}

// --------------------------------------------------------------- histórico
class _SecaoHistorico extends StatelessWidget {
  const _SecaoHistorico({required this.analises, required this.alteracoes});
  final List<Analise> analises;
  final List<Alteracao> alteracoes;

  @override
  Widget build(BuildContext context) {
    return Secao(
      titulo: 'Histórico',
      subtitulo: 'Nenhuma análise é apagada. Compare o que mudou depois de cada correção.',
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text('Análises (${analises.length})', style: const TextStyle(fontWeight: FontWeight.w700)),
        if (analises.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text('Nenhuma análise ainda.', style: TextStyle(color: Cores.textoSuave)),
          ),
        for (final a in analises)
          Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: Text('#${a.id} • ${fmtDataHora(a.criadoEm)}'),
              subtitle: Text(
                'Média ${fmtNum(a.media)} • Freq. ${fmtPct(a.frequencia)} • '
                '${a.regras.isEmpty ? 'sem regras' : a.regras.join(', ')} • certeza ${fmtCerteza(a.certeza)} • v${a.versaoRegistros}'
                '${a.revisoes.isEmpty ? '' : ' • ${a.revisoes.length} revisão(ões)'}',
              ),
              trailing: ChipAcompanhamento(prioridade: a.prioridade),
              childrenPadding: const EdgeInsets.only(bottom: 12),
              expandedCrossAxisAlignment: CrossAxisAlignment.start,
              children: [Text(a.motivo, style: const TextStyle(color: Cores.textoSuave))],
            ),
          ),
        const Divider(height: 28),
        Text('Correções nos registros (${alteracoes.length})', style: const TextStyle(fontWeight: FontWeight.w700)),
        if (alteracoes.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text('Nenhuma correção registrada.', style: TextStyle(color: Cores.textoSuave)),
          ),
        for (final h in alteracoes)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(switch (h.tipo) {
              'nota' => Icons.edit_note,
              'entrega' => Icons.assignment_turned_in_outlined,
              _ => Icons.how_to_reg_outlined,
            }),
            title: Text('${h.referencia}: ${h.anterior ?? 'sem registro'} → ${h.novo}'),
            subtitle: Text('${h.autor} • ${fmtDataHora(h.criadoEm)}'),
          ),
      ]),
    );
  }
}
