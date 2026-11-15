import 'package:flutter/material.dart';

import '../../data/modelos.dart';
import 'tema.dart';

class ItemMenu {
  const ItemMenu(this.rotulo, this.icone, this.iconeAtivo);
  final String rotulo;
  final IconData icone;
  final IconData iconeAtivo;
}

/// Estrutura comum às duas áreas.
/// Tela larga (navegador): menu lateral escuro + barra superior.
/// Tela estreita (celular): AppBar + barra de navegação inferior.
/// Só a "view" muda entre web e Android; os view models são os mesmos.
class Casca extends StatefulWidget {
  const Casca({
    super.key,
    required this.usuario,
    required this.itens,
    required this.paginas,
    required this.aoSair,
  });

  final Usuario usuario;
  final List<ItemMenu> itens;
  final List<Widget> paginas;
  final VoidCallback aoSair;

  @override
  State<Casca> createState() => _CascaState();
}

class _CascaState extends State<Casca> {
  int _indice = 0;
  late final List<GlobalKey<NavigatorState>> _navegadores =
      List.generate(widget.paginas.length, (_) => GlobalKey<NavigatorState>());

  void _selecionar(int i) {
    if (i == _indice) {
      // Tocar de novo no item volta para a raiz da seção.
      _navegadores[i].currentState?.popUntil((r) => r.isFirst);
    }
    setState(() => _indice = i);
  }

  Widget _conteudo() {
    return IndexedStack(
      index: _indice,
      children: [
        for (var i = 0; i < widget.paginas.length; i++)
          Navigator(
            key: _navegadores[i],
            onGenerateRoute: (_) => MaterialPageRoute(builder: (_) => widget.paginas[i]),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final largo = MediaQuery.sizeOf(context).width >= 900;
    if (largo) {
      return Scaffold(
        body: Row(children: [
          _MenuLateral(itens: widget.itens, indice: _indice, aoSelecionar: _selecionar),
          Expanded(
            child: Column(children: [
              _BarraSuperior(usuario: widget.usuario, aoSair: widget.aoSair),
              const Divider(height: 1),
              Expanded(child: _conteudo()),
            ]),
          ),
        ]),
      );
    }
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: const _Marca(escura: false),
        actions: [_MenuUsuario(usuario: widget.usuario, aoSair: widget.aoSair, compacto: true)],
        bottom: const PreferredSize(
            preferredSize: Size.fromHeight(1), child: Divider(height: 1)),
      ),
      body: _conteudo(),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _indice,
        onDestinationSelected: _selecionar,
        destinations: [
          for (final it in widget.itens)
            NavigationDestination(
                icon: Icon(it.icone), selectedIcon: Icon(it.iconeAtivo), label: it.rotulo),
        ],
      ),
    );
  }
}

class _Marca extends StatelessWidget {
  const _Marca({required this.escura});
  final bool escura;

  @override
  Widget build(BuildContext context) {
    final cor = escura ? Colors.white : Cores.texto;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
      Text('FAINOR',
          style: TextStyle(color: cor, fontSize: escura ? 26 : 20, fontWeight: FontWeight.w900, letterSpacing: 0.5)),
      Text('Gestão Acadêmica',
          style: TextStyle(color: escura ? const Color(0xFFB8B8BE) : Cores.textoSuave, fontSize: 12.5)),
    ]);
  }
}

class _MenuLateral extends StatelessWidget {
  const _MenuLateral({required this.itens, required this.indice, required this.aoSelecionar});
  final List<ItemMenu> itens;
  final int indice;
  final ValueChanged<int> aoSelecionar;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 236,
      color: Cores.lateral,
      padding: const EdgeInsets.fromLTRB(14, 28, 14, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Padding(padding: EdgeInsets.only(left: 12), child: _Marca(escura: true)),
        const SizedBox(height: 36),
        for (var i = 0; i < itens.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Material(
              color: i == indice ? Cores.vermelho : Colors.transparent,
              borderRadius: BorderRadius.circular(10),
              child: InkWell(
                borderRadius: BorderRadius.circular(10),
                onTap: () => aoSelecionar(i),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
                  child: Row(children: [
                    Icon(i == indice ? itens[i].iconeAtivo : itens[i].icone, color: Colors.white, size: 21),
                    const SizedBox(width: 14),
                    Text(itens[i].rotulo,
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: i == indice ? FontWeight.w700 : FontWeight.w500)),
                  ]),
                ),
              ),
            ),
          ),
        const Spacer(),
        const Padding(
          padding: EdgeInsets.only(left: 12),
          child: Text('Dados fictícios • v0.1',
              style: TextStyle(color: Color(0xFF8A8A92), fontSize: 11.5)),
        ),
      ]),
    );
  }
}

class _BarraSuperior extends StatelessWidget {
  const _BarraSuperior({required this.usuario, required this.aoSair});
  final Usuario usuario;
  final VoidCallback aoSair;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      height: 68,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(children: [
        const Spacer(),
        _MenuUsuario(usuario: usuario, aoSair: aoSair),
      ]),
    );
  }
}

class _MenuUsuario extends StatelessWidget {
  const _MenuUsuario({required this.usuario, required this.aoSair, this.compacto = false});
  final Usuario usuario;
  final VoidCallback aoSair;
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final perfil = usuario.professor ? 'Perfil professor' : 'Perfil aluno';
    return PopupMenuButton<String>(
      tooltip: 'Conta',
      onSelected: (v) {
        if (v == 'sair') aoSair();
      },
      itemBuilder: (_) => [
        PopupMenuItem(enabled: false, child: Text('${usuario.nome} • $perfil')),
        const PopupMenuItem(value: 'sair', child: Text('Sair')),
      ],
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: Cores.vermelho,
            child: Text(usuario.iniciais,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13)),
          ),
          if (!compacto) ...[
            const SizedBox(width: 10),
            Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(usuario.nome, style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(perfil, style: const TextStyle(color: Cores.textoSuave, fontSize: 12)),
            ]),
            const SizedBox(width: 6),
            const Icon(Icons.expand_more, color: Cores.textoSuave),
          ],
        ]),
      ),
    );
  }
}

/// Conteúdo rolável com largura máxima e margens que se adaptam à tela.
class Pagina extends StatelessWidget {
  const Pagina({super.key, required this.children, this.larguraMaxima = 1180});
  final List<Widget> children;
  final double larguraMaxima;

  @override
  Widget build(BuildContext context) {
    final largo = MediaQuery.sizeOf(context).width >= 700;
    final podeVoltar = Navigator.of(context).canPop();
    return Scaffold(
      backgroundColor: Cores.fundo,
      body: SingleChildScrollView(
        padding: EdgeInsets.symmetric(horizontal: largo ? 32 : 16, vertical: largo ? 24 : 16),
        child: Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: larguraMaxima),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              if (podeVoltar)
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => Navigator.of(context).maybePop(),
                    icon: const Icon(Icons.arrow_back, size: 18),
                    label: const Text('Voltar'),
                    style: TextButton.styleFrom(foregroundColor: Cores.textoSuave),
                  ),
                ),
              ...children,
            ]),
          ),
        ),
      ),
    );
  }
}
