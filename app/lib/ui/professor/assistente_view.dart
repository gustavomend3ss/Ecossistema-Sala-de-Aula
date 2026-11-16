import 'package:flutter/material.dart';

import '../../data/modelos.dart';
import '../../data/repositorios.dart';
import '../core/componentes.dart';
import '../core/tema.dart';
import 'assistente_view_model.dart';
import 'matricula_view.dart';

class AssistenteView extends StatefulWidget {
  const AssistenteView({super.key, required this.repos});
  final Repositorios repos;

  @override
  State<AssistenteView> createState() => _AssistenteViewState();
}

class _AssistenteViewState extends State<AssistenteView> {
  late final AssistenteViewModel _vm = AssistenteViewModel(widget.repos)..carregar();
  final _campo = TextEditingController();
  final _rolagem = ScrollController();
  final _ultimaTroca = GlobalKey();

  @override
  void initState() {
    super.initState();
    _vm.addListener(_rolarParaFim);
  }

  @override
  void dispose() {
    _vm.removeListener(_rolarParaFim);
    _vm.dispose();
    _campo.dispose();
    _rolagem.dispose();
    super.dispose();
  }

  /// Leva a troca mais recente para o topo da conversa, para a resposta ser
  /// lida desde o começo (rolar até o fim escondia o início de respostas longas).
  void _rolarParaFim() {
    void alinhar() {
      final alvo = _ultimaTroca.currentContext;
      if (alvo != null) {
        Scrollable.ensureVisible(alvo,
            alignment: 0, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_ultimaTroca.currentContext == null && _rolagem.hasClients) {
        // A lista só constrói o que está perto da tela: vai ao fim e alinha depois.
        _rolagem.jumpTo(_rolagem.position.maxScrollExtent);
        WidgetsBinding.instance.addPostFrameCallback((_) => alinhar());
      } else {
        alinhar();
      }
    });
  }

  void _enviar([String? texto]) {
    final t = texto ?? _campo.text;
    if (t.trim().length < 2 || _vm.enviando) return;
    if (texto == null) _campo.clear();
    _vm.perguntar(t);
  }

  void _abrirEvidencias(ItemAssistente item) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => MatriculaView(
        repos: widget.repos,
        matriculaId: item.matriculaId,
        trilha: item.disciplina.isEmpty ? 'Assistente' : 'Assistente / ${item.disciplina}',
      ),
    ));
  }

  void _abrirHistoricoEmFolha() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (contexto) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
          child: _ListaHistorico(
            vm: _vm,
            aoAbrir: (id) {
              Navigator.of(contexto).pop();
              _vm.abrirConversa(id);
            },
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final largo = MediaQuery.sizeOf(context).width >= 1100;
    final margem = MediaQuery.sizeOf(context).width >= 700 ? 32.0 : 16.0;
    return Scaffold(
      backgroundColor: Cores.fundo,
      body: ListenableBuilder(
        listenable: _vm,
        builder: (context, _) {
          if (_vm.carregando) return const EstadoCarregando();
          if (_vm.erro != null) return EstadoErro(mensagem: _vm.erro!, aoTentar: _vm.carregar);
          if (_vm.turmas.isEmpty) return const EstadoVazio(texto: 'Nenhuma turma vinculada.');
          return Padding(
            padding: EdgeInsets.fromLTRB(margem, 24, margem, 16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              CabecalhoPagina(
                titulo: 'Assistente docente',
                subtitulo: margem > 16 ? 'Pergunte do seu jeito sobre as suas turmas e confira as evidências.' : null,
                acoes: [
                  if (!largo && _vm.historico.isNotEmpty)
                    OutlinedButton.icon(
                      onPressed: _vm.enviando ? null : _abrirHistoricoEmFolha,
                      icon: const Icon(Icons.history, size: 18),
                      label: const Text('Histórico'),
                    ),
                  FilledButton.icon(
                    onPressed: _vm.enviando || _vm.mensagens.isEmpty ? null : _vm.novaConversa,
                    icon: const Icon(Icons.add_comment_outlined, size: 18),
                    label: const Text('Nova conversa'),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Expanded(
                child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Expanded(
                    flex: 3,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                      Expanded(
                        child: Cartao(
                          child: _vm.abrindoConversa
                              ? const EstadoCarregando()
                              : _vm.mensagens.isEmpty
                                  ? _Boas(turmas: _vm.turmas)
                                  : ListView(
                                      controller: _rolagem,
                                      padding: const EdgeInsets.all(18),
                                      children: [
                                        for (var i = 0; i < _vm.mensagens.length; i++)
                                          _Troca(
                                            key: i == _vm.mensagens.length - 1 ? _ultimaTroca : null,
                                            m: _vm.mensagens[i],
                                            ultima: i == _vm.mensagens.length - 1,
                                            largo: largo,
                                            aoAbrir: _abrirEvidencias,
                                            aoEnviar: _enviar,
                                          ),
                                      ],
                                    ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      _Entrada(controle: _campo, enviando: _vm.enviando, aoEnviar: _enviar),
                    ]),
                  ),
                  if (largo) ...[
                    const SizedBox(width: 16),
                    SizedBox(
                      width: 300,
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        Expanded(
                          child: Cartao(
                            child: Padding(
                              padding: const EdgeInsets.all(18),
                              child: _ListaHistorico(vm: _vm, aoAbrir: _vm.abrirConversa),
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        _PainelFontes(fontes: _vm.fontes),
                      ]),
                    ),
                  ],
                ]),
              ),
            ]),
          );
        },
      ),
    );
  }
}

/// Tela inicial: explica o que dá para perguntar, sem lista de perguntas prontas.
class _Boas extends StatelessWidget {
  const _Boas({required this.turmas});
  final List<TurmaResumo> turmas;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const CircleAvatar(
              radius: 26,
              backgroundColor: Cores.vermelho,
              child: Icon(Icons.chat_bubble_outline, color: Colors.white),
            ),
            const SizedBox(height: 14),
            const Text('O que você quer saber das suas turmas?',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            const Text(
              'Escreva com as suas palavras. Dá para citar a disciplina ou o estudante, mesmo com erro de '
              'digitação, e continuar o assunto na pergunta seguinte ("e quais deles também têm faltas?").',
              textAlign: TextAlign.center,
              style: TextStyle(color: Cores.textoSuave, height: 1.45),
            ),
            const SizedBox(height: 18),
            const Text('Turmas vinculadas a você', style: TextStyle(fontSize: 12.5, color: Cores.textoSuave)),
            const SizedBox(height: 8),
            Wrap(alignment: WrapAlignment.center, spacing: 6, runSpacing: 6, children: [
              for (final t in turmas)
                EtiquetaPequena(texto: t.disciplina, cor: Cores.texto, fundo: Cores.cinzaClaro),
            ]),
            const SizedBox(height: 18),
            const Text(
              'As respostas saem dos registros e das regras R1 a R6. O assistente não altera notas nem decide '
              'por você.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Cores.textoSuave, fontSize: 12.5),
            ),
          ]),
        ),
      ),
    );
  }
}

String _hora(DateTime d) =>
    '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

class _Troca extends StatelessWidget {
  const _Troca({
    super.key,
    required this.m,
    required this.ultima,
    required this.largo,
    required this.aoAbrir,
    required this.aoEnviar,
  });
  final MensagemChat m;
  final bool ultima;
  final bool largo;
  final void Function(ItemAssistente) aoAbrir;
  final void Function([String?]) aoEnviar;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      // Pergunta do professor
      Align(
        alignment: Alignment.centerRight,
        child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('Você  ${_hora(m.horario)}', style: const TextStyle(color: Cores.textoSuave, fontSize: 12)),
          const SizedBox(height: 4),
          Container(
            constraints: const BoxConstraints(maxWidth: 520),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(color: Cores.cinzaClaro, borderRadius: BorderRadius.circular(12)),
            child: Text(m.pergunta),
          ),
        ]),
      ),
      const SizedBox(height: 16),
      // Resposta do assistente
      Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const CircleAvatar(
          radius: 18,
          backgroundColor: Cores.vermelho,
          child: Icon(Icons.chat_bubble_outline, color: Colors.white, size: 18),
        ),
        const SizedBox(width: 12),
        Expanded(child: _corpoResposta(context)),
      ]),
      const SizedBox(height: 24),
    ]);
  }

  Widget _corpoResposta(BuildContext context) {
    if (m.pendente) {
      return const Padding(
        padding: EdgeInsets.only(top: 8),
        child: Row(children: [
          SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 10),
          Flexible(
            child: Text('Consultando registros e aplicando as regras...',
                style: TextStyle(color: Cores.textoSuave)),
          ),
        ]),
      );
    }
    if (m.erro != null) {
      return Container(
        constraints: const BoxConstraints(maxWidth: 620),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Cores.vermelhoClaro, borderRadius: BorderRadius.circular(10)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.error_outline, color: Cores.vermelho, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(m.erro!, style: const TextStyle(color: Cores.vermelho))),
        ]),
      );
    }
    final r = m.resposta!;
    final (icone, cor, fundo) = switch (r.tipo) {
      'sem_dados' => (Icons.info_outline, Cores.ambar, Cores.ambarClaro),
      'fora_do_escopo' || 'sem_permissao' => (Icons.lock_outline, Cores.textoSuave, Cores.cinzaClaro),
      'esclarecimento' => (Icons.help_outline, Cores.azul, Cores.azulClaro),
      _ => (null, Cores.texto, Colors.white),
    };
    final secoes = r.secoes.where((s) => s.itens.isNotEmpty).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
        const Text('Assistente', style: TextStyle(fontWeight: FontWeight.w700)),
        if (r.disciplinas.isNotEmpty)
          Tooltip(
            message: 'Recorte usado nesta resposta',
            child: EtiquetaPequena(
              texto: (r.continuacao ? 'Continuação · ' : '') +
                  (r.disciplinas.length > 2 ? '${r.disciplinas.length} turmas' : r.disciplinas.join(', ')),
              cor: Cores.azul,
              fundo: Cores.azulClaro,
            ),
          ),
      ]),
      const SizedBox(height: 6),
      Container(
        constraints: const BoxConstraints(maxWidth: 680),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: fundo,
          border: Border.all(color: fundo == Colors.white ? Cores.borda : fundo),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (icone != null) ...[
              Icon(icone, color: cor, size: 20),
              const SizedBox(width: 8),
            ],
            Expanded(child: Text(r.texto, style: TextStyle(height: 1.45, color: cor))),
          ]),
          if (r.opcoes.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final o in r.opcoes)
                OutlinedButton(
                  onPressed: ultima ? () => aoEnviar(o.valor) : null,
                  child: Text(o.rotulo),
                ),
            ]),
          ],
          for (final s in secoes) _Secao(secao: s, mostrarTitulo: secoes.length > 1, aoAbrir: aoAbrir),
          if (secoes.isEmpty)
            for (final item in r.itens) ...[
              const Divider(height: 26),
              _ItemResposta(item: item, aoAbrir: aoAbrir),
            ],
        ]),
      ),
      const SizedBox(height: 6),
      Text(
        r.aviso + (r.geradoPor == 'gemini' ? ' Texto redigido pelo Gemini e conferido com os registros.' : ''),
        style: const TextStyle(color: Cores.textoSuave, fontSize: 12),
      ),
      if (!largo && r.fontes.isNotEmpty) ...[
        const SizedBox(height: 10),
        Wrap(spacing: 6, runSpacing: 6, children: [
          for (final f in r.fontes)
            Tooltip(
              message: f.descricao,
              child: EtiquetaPequena(texto: f.titulo, cor: Cores.texto, fundo: Cores.cinzaClaro),
            ),
        ]),
      ],
      if (ultima && r.sugestoes.isNotEmpty) ...[
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final s in r.sugestoes)
            ActionChip(
              avatar: const Icon(Icons.subdirectory_arrow_right, size: 16),
              label: Text(s),
              onPressed: () => aoEnviar(s),
            ),
        ]),
      ],
    ]);
  }
}

/// Uma seção da resposta. Listas longas começam recolhidas.
class _Secao extends StatefulWidget {
  const _Secao({required this.secao, required this.mostrarTitulo, required this.aoAbrir});
  final SecaoAssistente secao;
  final bool mostrarTitulo;
  final void Function(ItemAssistente) aoAbrir;

  @override
  State<_Secao> createState() => _SecaoState();
}

class _SecaoState extends State<_Secao> {
  static const _visiveis = 4;
  bool _aberta = false;

  @override
  Widget build(BuildContext context) {
    final itens = widget.secao.itens;
    final mostrar = _aberta ? itens : itens.take(_visiveis).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (widget.mostrarTitulo) ...[
        const SizedBox(height: 18),
        Text(widget.secao.titulo,
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Cores.textoSuave)),
      ],
      for (final item in mostrar) ...[
        const Divider(height: 26),
        _ItemResposta(
          item: item,
          aoAbrir: widget.aoAbrir,
          sugestao: widget.secao.funcao == 'sugerir_intervencao',
        ),
      ],
      if (itens.length > _visiveis)
        TextButton(
          style: TextButton.styleFrom(padding: EdgeInsets.zero, foregroundColor: Cores.azul),
          onPressed: () => setState(() => _aberta = !_aberta),
          child: Text(_aberta ? 'Mostrar menos' : 'Mostrar mais ${itens.length - _visiveis}'),
        ),
    ]);
  }
}

class _ItemResposta extends StatelessWidget {
  const _ItemResposta({required this.item, required this.aoAbrir, this.sugestao = false});
  final ItemAssistente item;
  final void Function(ItemAssistente) aoAbrir;

  /// Linhas de sugestão de intervenção (ícone de ideia) ou de registro (marcador).
  final bool sugestao;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(item.titulo, style: const TextStyle(fontWeight: FontWeight.w600)),
      if (item.disciplina.isNotEmpty)
        Text(item.disciplina, style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
      const SizedBox(height: 10),
      Wrap(spacing: 10, runSpacing: 10, children: [
        for (final d in item.detalhes)
          Container(
            width: 190,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Cores.fundo, borderRadius: BorderRadius.circular(10)),
            child: Row(children: [
              Icon(
                switch (d.rotulo) {
                  'Média' => Icons.description_outlined,
                  'Frequência' => Icons.person_outline,
                  _ => Icons.assignment_late_outlined,
                },
                size: 22,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(d.rotulo, style: const TextStyle(fontSize: 12.5)),
                  Text(
                    d.avaliavel
                        ? (d.alerta ? '${d.valor} ${d.comparacao} ${d.limite}' : '${d.valor}  (${d.tipoLimite} ${d.limite})')
                        : 'Não avaliável',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                      color: d.alerta ? Cores.vermelho : (d.avaliavel ? Cores.texto : Cores.textoSuave),
                    ),
                  ),
                ]),
              ),
            ]),
          ),
      ]),
      for (final linha in item.linhas)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: sugestao
                  ? const Icon(Icons.lightbulb_outline, size: 16, color: Cores.ambar)
                  : const Icon(Icons.chevron_right, size: 16, color: Cores.textoSuave),
            ),
            const SizedBox(width: 8),
            Expanded(child: Text(linha, style: const TextStyle(height: 1.4))),
          ]),
        ),
      if (item.observacao != null) ...[
        const SizedBox(height: 8),
        Text(item.observacao!, style: const TextStyle(color: Cores.textoSuave)),
      ],
      const SizedBox(height: 6),
      TextButton.icon(
        style: TextButton.styleFrom(foregroundColor: Cores.vermelho, padding: EdgeInsets.zero),
        onPressed: () => aoAbrir(item),
        icon: const Icon(Icons.open_in_new, size: 16),
        label: Text('Consultar evidências de ${item.codigo}'),
      ),
    ]);
  }
}

class _Entrada extends StatelessWidget {
  const _Entrada({required this.controle, required this.enviando, required this.aoEnviar});
  final TextEditingController controle;
  final bool enviando;
  final void Function([String?]) aoEnviar;

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Expanded(
        child: TextField(
          controller: controle,
          enabled: !enviando,
          maxLength: 500,
          decoration: const InputDecoration(
            hintText: 'Ex.: quem está com muitas faltas em estrutura de dados?',
            counterText: '',
          ),
          onSubmitted: (_) => aoEnviar(),
        ),
      ),
      const SizedBox(width: 8),
      IconButton.filled(
        tooltip: 'Enviar',
        style: IconButton.styleFrom(
          backgroundColor: Cores.vermelho,
          padding: const EdgeInsets.all(14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        onPressed: enviando ? null : () => aoEnviar(),
        icon: const Icon(Icons.send, color: Colors.white),
      ),
    ]);
  }
}

class _ListaHistorico extends StatelessWidget {
  const _ListaHistorico({required this.vm, required this.aoAbrir});
  final AssistenteViewModel vm;
  final void Function(int) aoAbrir;

  String _quando(DateTime? d) {
    if (d == null) return '';
    final hoje = DateTime.now();
    if (d.year == hoje.year && d.month == hoje.month && d.day == hoje.day) return 'hoje, ${_hora(d)}';
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
      const Text('Conversas', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
      const SizedBox(height: 10),
      if (vm.historico.isEmpty)
        const Text('Suas conversas ficam guardadas aqui, só para você.',
            style: TextStyle(color: Cores.textoSuave, fontSize: 12.5))
      else
        Flexible(
          child: ListView(shrinkWrap: true, children: [
            for (final c in vm.historico)
              Material(
                color: c.id == vm.conversaId ? Cores.cinzaClaro : Colors.transparent,
                borderRadius: BorderRadius.circular(8),
                child: ListTile(
                  dense: true,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  title: Text(c.titulo, maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: Text('${_quando(c.atualizadaEm)} · ${c.mensagens} '
                      '${c.mensagens == 1 ? 'pergunta' : 'perguntas'}'),
                  onTap: vm.enviando ? null : () => aoAbrir(c.id),
                ),
              ),
          ]),
        ),
    ]);
  }
}

class _PainelFontes extends StatelessWidget {
  const _PainelFontes({required this.fontes});
  final List<Fonte> fontes;

  IconData _icone(String titulo) {
    if (titulo.startsWith('Regras')) return Icons.menu_book_outlined;
    if (titulo.startsWith('Perfil')) return Icons.storage_outlined;
    return Icons.description_outlined;
  }

  @override
  Widget build(BuildContext context) {
    return Cartao(
      cor: const Color(0xFFF0F0F2),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Fontes desta resposta', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
          const SizedBox(height: 14),
          if (fontes.isEmpty)
            const Text('As fontes aparecem aqui depois da primeira pergunta.',
                style: TextStyle(color: Cores.textoSuave)),
          for (final f in fontes)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(_icone(f.titulo), size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(f.titulo, style: const TextStyle(fontWeight: FontWeight.w600)),
                    Text(f.descricao,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
                  ]),
                ),
              ]),
            ),
          const Divider(),
          const SizedBox(height: 6),
          const Text('Usa só os registros das suas turmas. Não altera notas nem toma decisões.',
              style: TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
        ]),
      ),
    );
  }
}
