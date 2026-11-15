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

  void _rolarParaFim() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_rolagem.hasClients) {
        _rolagem.animateTo(_rolagem.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  void _enviar([String? texto]) {
    final t = texto ?? _campo.text;
    if (t.trim().length < 2) return;
    _campo.clear();
    _vm.perguntar(t);
  }

  void _abrirEvidencias(ItemAssistente item) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => MatriculaView(
        repos: widget.repos,
        matriculaId: item.matriculaId,
        trilha: 'Assistente / ${_vm.turma?.disciplina ?? ''}',
      ),
    ));
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
          if (_vm.turma == null) return const EstadoVazio(texto: 'Nenhuma turma vinculada.');
          return Padding(
            padding: EdgeInsets.fromLTRB(margem, 24, margem, 16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              CabecalhoPagina(
                titulo: 'Assistente docente',
                subtitulo: 'Pergunte sobre sua turma e confira as evidências.',
                acoes: [_SeletorTurma(vm: _vm)],
              ),
              const SizedBox(height: 18),
              Expanded(
                child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Expanded(
                    flex: 3,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                      Expanded(
                        child: Cartao(
                          child: _vm.mensagens.isEmpty
                              ? _Boas(aoEscolher: _enviar)
                              : ListView(
                                  controller: _rolagem,
                                  padding: const EdgeInsets.all(18),
                                  children: [
                                    for (final m in _vm.mensagens)
                                      _Troca(m: m, largo: largo, aoAbrir: _abrirEvidencias),
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
                    SizedBox(width: 280, child: _PainelFontes(fontes: _vm.fontes)),
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

class _SeletorTurma extends StatelessWidget {
  const _SeletorTurma({required this.vm});
  final AssistenteViewModel vm;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Cores.borda),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<int>(
          value: vm.turma?.id,
          items: [
            for (final t in vm.turmas)
              DropdownMenuItem(value: t.id, child: Text('${t.disciplina} • ${t.criterios}')),
          ],
          onChanged: (id) => vm.selecionarTurma(
              vm.turmas.where((t) => t.id == id).isEmpty ? null : vm.turmas.firstWhere((t) => t.id == id)),
        ),
      ),
    );
  }
}

class _Boas extends StatelessWidget {
  const _Boas({required this.aoEscolher});
  final void Function(String) aoEscolher;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const CircleAvatar(
            radius: 26,
            backgroundColor: Cores.vermelho,
            child: Icon(Icons.chat_bubble_outline, color: Colors.white),
          ),
          const SizedBox(height: 14),
          const Text('Como posso ajudar com esta turma?',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          const Text('As respostas usam só os registros da turma e as regras do perfil de critérios.',
              textAlign: TextAlign.center, style: TextStyle(color: Cores.textoSuave)),
          const SizedBox(height: 18),
          Wrap(alignment: WrapAlignment.center, spacing: 8, runSpacing: 8, children: [
            for (final s in AssistenteViewModel.sugestoes)
              ActionChip(label: Text(s), onPressed: () => aoEscolher(s)),
          ]),
        ]),
      ),
    );
  }
}

String _hora(DateTime d) =>
    '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

class _Troca extends StatelessWidget {
  const _Troca({required this.m, required this.largo, required this.aoAbrir});
  final MensagemChat m;
  final bool largo;
  final void Function(ItemAssistente) aoAbrir;

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
          Text('Consultando registros e aplicando as regras...', style: TextStyle(color: Cores.textoSuave)),
        ]),
      );
    }
    if (m.erro != null) {
      return Text(m.erro!, style: const TextStyle(color: Cores.vermelho));
    }
    final r = m.resposta!;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Assistente', style: TextStyle(fontWeight: FontWeight.w700)),
      const SizedBox(height: 6),
      Container(
        constraints: const BoxConstraints(maxWidth: 620),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: Cores.borda),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(r.texto, style: const TextStyle(height: 1.45)),
          for (final item in r.itens) ...[
            const Divider(height: 26),
            _ItemResposta(item: item, aoAbrir: aoAbrir),
          ],
        ]),
      ),
      const SizedBox(height: 6),
      Text(r.aviso, style: const TextStyle(color: Cores.textoSuave, fontSize: 12)),
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
    ]);
  }
}

class _ItemResposta extends StatelessWidget {
  const _ItemResposta({required this.item, required this.aoAbrir});
  final ItemAssistente item;
  final void Function(ItemAssistente) aoAbrir;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(item.titulo, style: const TextStyle(fontWeight: FontWeight.w600)),
      const SizedBox(height: 10),
      Wrap(spacing: 10, runSpacing: 10, children: [
        for (final d in item.detalhes)
          Container(
            width: 200,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Cores.fundo, borderRadius: BorderRadius.circular(10)),
            child: Row(children: [
              Icon(d.rotulo == 'Média' ? Icons.description_outlined : Icons.person_outline, size: 22),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(d.rotulo, style: const TextStyle(fontSize: 12.5)),
                Text(
                  d.avaliavel
                      ? (d.alerta ? '${d.valor} < ${d.limite}' : '${d.valor}  (mín. ${d.limite})')
                      : 'Não avaliável',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                    color: d.alerta ? Cores.vermelho : (d.avaliavel ? Cores.texto : Cores.textoSuave),
                  ),
                ),
              ])),
            ]),
          ),
      ]),
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
            hintText: 'Pergunte sobre notas, frequência ou alertas...',
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
              padding: const EdgeInsets.only(bottom: 16),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(_icone(f.titulo), size: 22),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(f.titulo, style: const TextStyle(fontWeight: FontWeight.w600)),
                    Text(f.descricao, style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
                  ]),
                ),
              ]),
            ),
          const Divider(),
          const SizedBox(height: 8),
          const Text('O assistente usa apenas os registros da sua turma.',
              style: TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
          const SizedBox(height: 8),
          const Text('Não realiza decisões autônomas nem modifica notas.',
              style: TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
        ]),
      ),
    );
  }
}
