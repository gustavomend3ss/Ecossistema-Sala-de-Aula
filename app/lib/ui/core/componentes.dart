import 'package:flutter/material.dart';

import 'formato.dart';
import 'tema.dart';

class EstadoCarregando extends StatelessWidget {
  const EstadoCarregando({super.key, this.texto = 'Carregando...'});
  final String texto;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const CircularProgressIndicator(),
        const SizedBox(height: 12),
        Text(texto, style: const TextStyle(color: Cores.textoSuave)),
      ]),
    );
  }
}

class EstadoErro extends StatelessWidget {
  const EstadoErro({super.key, required this.mensagem, this.aoTentar});
  final String mensagem;
  final VoidCallback? aoTentar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.cloud_off_outlined, size: 40, color: Cores.vermelho),
          const SizedBox(height: 12),
          Text(mensagem, textAlign: TextAlign.center),
          if (aoTentar != null) ...[
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: aoTentar,
              icon: const Icon(Icons.refresh),
              label: const Text('Tentar de novo'),
            ),
          ],
        ]),
      ),
    );
  }
}

class EstadoVazio extends StatelessWidget {
  const EstadoVazio({super.key, required this.texto, this.icone = Icons.inbox_outlined});
  final String texto;
  final IconData icone;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icone, size: 36, color: Cores.textoSuave),
          const SizedBox(height: 10),
          Text(texto, textAlign: TextAlign.center, style: const TextStyle(color: Cores.textoSuave)),
        ]),
      ),
    );
  }
}

/// Situação de acompanhamento. Sempre tem texto: a cor nunca é a única pista.
class ChipAcompanhamento extends StatelessWidget {
  const ChipAcompanhamento({super.key, required this.prioridade, this.desatualizada = false});
  final String? prioridade;
  final bool desatualizada;

  @override
  Widget build(BuildContext context) {
    final p = prioridade;
    late final Color fundo;
    late final Color texto;
    Color? borda;
    String rotulo;
    if (p == null) {
      fundo = Colors.white;
      texto = Cores.textoSuave;
      borda = Cores.borda;
      rotulo = 'Não analisado';
    } else {
      rotulo = rotuloPrioridade[p] ?? p;
      switch (p) {
        case 'prioridade_alta':
          fundo = Cores.vermelhoClaro;
          texto = Cores.vermelho;
        case 'alerta_media':
        case 'alerta_frequencia':
        case 'alerta_entregas':
          fundo = Cores.ambarClaro;
          texto = Cores.ambar;
        case 'conferir_dados':
          fundo = Colors.white;
          texto = Cores.vermelho;
          borda = Cores.vermelho;
        default:
          fundo = Cores.cinzaClaro;
          texto = Cores.textoSuave;
      }
    }
    final chip = Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: fundo,
        borderRadius: BorderRadius.circular(20),
        border: borda == null ? null : Border.all(color: borda),
      ),
      child: Text(rotulo,
          style: TextStyle(color: texto, fontWeight: FontWeight.w600, fontSize: 12.5)),
    );
    if (!desatualizada || p == null) return chip;
    return Wrap(spacing: 6, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
      chip,
      const Tooltip(
        message: 'Registros mudaram depois desta análise. Analise de novo (R5).',
        child: EtiquetaPequena(texto: 'Desatualizada', cor: Cores.azul, fundo: Cores.azulClaro),
      ),
    ]);
  }
}

class EtiquetaPequena extends StatelessWidget {
  const EtiquetaPequena({super.key, required this.texto, required this.cor, required this.fundo});
  final String texto;
  final Color cor;
  final Color fundo;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: fundo, borderRadius: BorderRadius.circular(6)),
      child: Text(texto, style: TextStyle(color: cor, fontSize: 11.5, fontWeight: FontWeight.w600)),
    );
  }
}

class CartaoIndicador extends StatelessWidget {
  const CartaoIndicador({
    super.key,
    required this.titulo,
    required this.valor,
    required this.icone,
    this.subtitulo,
    this.alerta = false,
  });

  final String titulo;
  final String valor;
  final IconData icone;
  final String? subtitulo;
  final bool alerta;

  @override
  Widget build(BuildContext context) {
    return Cartao(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: Cores.fundo, borderRadius: BorderRadius.circular(10)),
            child: Icon(icone, color: Cores.texto),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(titulo, style: const TextStyle(color: Cores.textoSuave, fontSize: 13)),
              const SizedBox(height: 4),
              Text(valor,
                  style: TextStyle(
                      fontSize: 30,
                      fontWeight: FontWeight.w700,
                      color: alerta ? Cores.vermelho : Cores.texto)),
              if (subtitulo != null)
                Text(subtitulo!, style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
            ]),
          ),
        ]),
      ),
    );
  }
}

class Secao extends StatelessWidget {
  const Secao({super.key, required this.titulo, required this.child, this.acao, this.subtitulo});
  final String titulo;
  final String? subtitulo;
  final Widget child;
  final Widget? acao;

  @override
  Widget build(BuildContext context) {
    return Cartao(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(titulo, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                if (subtitulo != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(subtitulo!, style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
                  ),
              ]),
            ),
            if (acao != null) acao!,
          ]),
          const SizedBox(height: 14),
          child,
        ]),
      ),
    );
  }
}

class AvisoInfo extends StatelessWidget {
  const AvisoInfo({super.key, required this.texto, this.icone = Icons.info_outline});
  final String texto;
  final IconData icone;

  @override
  Widget build(BuildContext context) {
    return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Icon(icone, size: 16, color: Cores.textoSuave),
      const SizedBox(width: 6),
      Expanded(child: Text(texto, style: const TextStyle(color: Cores.textoSuave, fontSize: 12.5))),
    ]);
  }
}

void mostrarMensagem(BuildContext context, String texto, {bool erro = false}) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(texto),
      backgroundColor: erro ? Cores.vermelho : Cores.texto,
      behavior: SnackBarBehavior.floating,
    ));
}

/// Cabeçalho de página: título grande, linha de contexto e ação à direita.
class CabecalhoPagina extends StatelessWidget {
  const CabecalhoPagina({super.key, required this.titulo, this.subtitulo, this.acoes = const [], this.trilha});
  final String titulo;
  final String? subtitulo;
  final List<Widget> acoes;
  final String? trilha;

  @override
  Widget build(BuildContext context) {
    final largo = MediaQuery.sizeOf(context).width >= 700;
    final textos = Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (trilha != null)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(trilha!, style: const TextStyle(color: Cores.textoSuave, fontSize: 13)),
        ),
      Text(titulo,
          style: TextStyle(fontSize: largo ? 30 : 24, fontWeight: FontWeight.w800, color: Cores.texto)),
      if (subtitulo != null)
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(subtitulo!, style: const TextStyle(color: Cores.textoSuave, fontSize: 15)),
        ),
    ]);
    if (acoes.isEmpty) return textos;
    if (!largo) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        textos,
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: acoes),
      ]);
    }
    return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Expanded(child: textos),
      Wrap(spacing: 8, children: acoes),
    ]);
  }
}

/// Superfície branca com borda fina, usada no lugar de Card.
class Cartao extends StatelessWidget {
  const Cartao({super.key, required this.child, this.cor = Colors.white, this.corBorda = Cores.borda});
  final Widget child;
  final Color cor;
  final Color corBorda;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: cor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: corBorda),
      ),
      child: child,
    );
  }
}

/// Situação de uma entrega. Texto sempre visível, cor só reforça.
class ChipSituacao extends StatelessWidget {
  const ChipSituacao({super.key, required this.situacao});
  final String situacao;

  @override
  Widget build(BuildContext context) {
    final (Color cor, Color fundo) = switch (situacao) {
      'entregue' => (Cores.verde, Cores.verdeClaro),
      'entregue_atraso' => (Cores.ambar, Cores.ambarClaro),
      'atrasada' => (Cores.vermelho, Cores.vermelhoClaro),
      _ => (Cores.azul, Cores.azulClaro),
    };
    return EtiquetaPequena(texto: rotuloSituacao[situacao] ?? situacao, cor: cor, fundo: fundo);
  }
}

/// Grau de certeza da necessidade de acompanhamento (fator de certeza, 0 a 1).
class BarraCerteza extends StatelessWidget {
  const BarraCerteza({super.key, required this.valor});
  final double valor;

  @override
  Widget build(BuildContext context) {
    final cor = valor >= 0.8 ? Cores.vermelho : (valor >= 0.5 ? Cores.ambar : Cores.textoSuave);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Expanded(
          child: Text('Grau de certeza da necessidade de acompanhamento',
              style: TextStyle(fontWeight: FontWeight.w600)),
        ),
        Text(fmtCerteza(valor), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: cor)),
      ]),
      const SizedBox(height: 6),
      LinearProgressIndicator(
        value: valor,
        minHeight: 8,
        borderRadius: BorderRadius.circular(4),
        color: cor,
        backgroundColor: Cores.cinzaClaro,
      ),
      const SizedBox(height: 4),
      const Text(
        'Fatores de certeza (modelo MYCIN): cada alerta independente soma evidência, sem passar de 1.',
        style: TextStyle(color: Cores.textoSuave, fontSize: 12),
      ),
    ]);
  }
}
