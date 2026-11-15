import 'package:flutter/material.dart';

import '../../data/modelos.dart';
import '../core/casca.dart';
import '../core/componentes.dart';
import '../core/dialogos.dart';
import '../core/formato.dart';
import '../core/tema.dart';
import 'desempenho_view_model.dart';

/// "Meu desempenho": o aluno vê só a própria matrícula (RF02).
/// Não mostra rótulos de alerta: mostra dados e o que ainda falta lançar.
class DesempenhoView extends StatelessWidget {
  const DesempenhoView({super.key, required this.vm});
  final DesempenhoViewModel vm;

  Future<void> _solicitar(BuildContext context, Registros r, {String? inicial}) async {
    final opcoes = <OpcaoReferencia>[
      for (final a in r.avaliacoes)
        OpcaoReferencia('avaliacao:${a.avaliacaoId}',
            '${a.nome} (${a.valor == null ? 'não lançada' : fmtNum(a.valor)})'),
      for (final a in r.aulas.where((a) => a.presente != true))
        OpcaoReferencia('aula:${a.aulaId}',
            'Aula ${a.ordem} • ${fmtData(a.data)} (${a.presente == null ? 'sem registro' : 'falta'})'),
      for (final a in r.atividades.where((a) => a.situacao == 'atrasada'))
        OpcaoReferencia('atividade:${a.atividadeId}', 'Entrega: ${a.titulo} (sem registro)'),
      const OpcaoReferencia('geral', 'Outro registro da matrícula'),
    ];
    final dados = await dialogoConferencia(context, opcoes: opcoes, inicial: inicial);
    if (dados == null) return;
    final erro = await vm.pedirConferencia(dados.referencia, dados.mensagem);
    if (context.mounted) {
      mostrarMensagem(context, erro ?? 'Pedido enviado ao professor. Sua nota não foi alterada.', erro: erro != null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: vm,
      builder: (context, _) {
        final r = vm.atual;
        if (r == null) {
          return Pagina(children: [
            const CabecalhoPagina(titulo: 'Meu desempenho'),
            const SizedBox(height: 40),
            if (vm.carregando)
              const EstadoCarregando()
            else if (vm.erro != null)
              EstadoErro(mensagem: vm.erro!, aoTentar: vm.carregar)
            else
              const EstadoVazio(texto: 'Você ainda não tem matrícula em turmas.'),
          ]);
        }
        final i = r.indicadores;
        final largo = MediaQuery.sizeOf(context).width >= 900;
        final pendMedia = i.pendencias.any((p) => p.indicador == 'media');

        final cartaoMedia = CartaoIndicador(
          titulo: 'Média atual',
          valor: fmtNum(i.media),
          icone: Icons.bar_chart,
          subtitulo: pendMedia ? 'Aguardando nota de avaliação obrigatória' : 'Média ponderada das avaliações',
        );
        final cartaoFreq = Cartao(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Minha frequência', style: TextStyle(color: Cores.textoSuave, fontSize: 13)),
              const SizedBox(height: 6),
              Text('${i.presencas} de ${i.unidadesConsideradas}',
                  style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800)),
              const Text('unidades-aula com presença', style: TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                  child: LinearProgressIndicator(
                    value: (i.frequencia ?? 0) / 100,
                    minHeight: 8,
                    borderRadius: BorderRadius.circular(4),
                    color: Cores.vermelho,
                    backgroundColor: Cores.cinzaClaro,
                  ),
                ),
                const SizedBox(width: 10),
                Text(fmtPct(i.frequencia), style: const TextStyle(fontWeight: FontWeight.w700)),
              ]),
            ]),
          ),
        );

        final avaliacoes = Secao(
          titulo: 'Minhas avaliações',
          child: Column(children: [
            for (final a in r.avaliacoes)
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(a.nome),
                subtitle: Text('Peso ${fmtNum(a.peso)}'),
                trailing: Text(
                  a.valor == null ? 'Não lançada' : fmtNum(a.valor),
                  style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                      color: a.valor == null ? Cores.ambar : Cores.texto),
                ),
              ),
            const Divider(),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Média', style: TextStyle(fontWeight: FontWeight.w700)),
              trailing: Text(fmtNum(i.media), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            ),
          ]),
        );

        final atividades = Secao(
          titulo: 'Minhas atividades',
          subtitulo: 'Prazos e situação de cada entrega.',
          child: r.atividades.isEmpty
              ? const Text('Nenhuma atividade nesta disciplina.', style: TextStyle(color: Cores.textoSuave))
              : Column(children: [
                  for (final a in r.atividades)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(a.titulo),
                      subtitle: Text(
                          'Prazo ${fmtData(a.prazo)}${a.entregueEm != null ? ' • entregue em ${fmtData(a.entregueEm!)}' : ''}'),
                      trailing: ChipSituacao(situacao: a.situacao),
                    ),
                ]),
        );

        final semEntrega = r.atividades.where((a) => a.situacao == 'atrasada').toList();
        final acompanhar = Cartao(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(Icons.lightbulb_outline),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('O que acompanhar', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  if (i.pendencias.isEmpty && semEntrega.isEmpty)
                    const Text('Todas as avaliações e presenças estão lançadas e não há atividade vencida '
                        'sem entrega. Se algum valor parecer errado, peça a conferência ao professor.')
                  else ...[
                    for (final p in i.pendencias) Text('• ${p.motivo}'),
                    for (final a in semEntrega) Text('• "${a.titulo}" venceu em ${fmtData(a.prazo)} sem entrega registrada.'),
                  ],
                ]),
              ),
              const SizedBox(width: 12),
              if (largo)
                OutlinedButton(
                  onPressed: vm.enviando ? null : () => _solicitar(context, r),
                  child: const Text('Solicitar conferência do registro'),
                ),
            ]),
          ),
        );

        return Pagina(children: [
          CabecalhoPagina(
            titulo: 'Meu desempenho',
            subtitulo: '${r.disciplina} • ${r.periodo} • matrícula ${r.codigo}',
            acoes: [
              if (vm.matriculas.length > 1)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Cores.borda),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<int>(
                      value: vm.selecionada,
                      items: [
                        for (var k = 0; k < vm.matriculas.length; k++)
                          DropdownMenuItem(value: k, child: Text(vm.matriculas[k].disciplina)),
                      ],
                      onChanged: (k) => vm.selecionar(k ?? 0),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 20),
          if (largo)
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(child: cartaoMedia),
              const SizedBox(width: 16),
              Expanded(child: cartaoFreq),
            ])
          else ...[
            cartaoMedia,
            const SizedBox(height: 12),
            cartaoFreq,
          ],
          const SizedBox(height: 16),
          avaliacoes,
          const SizedBox(height: 16),
          atividades,
          const SizedBox(height: 16),
          acompanhar,
          if (!largo) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: vm.enviando ? null : () => _solicitar(context, r),
              icon: const Icon(Icons.mark_email_unread_outlined),
              label: const Text('Solicitar conferência do registro'),
            ),
          ],
          const SizedBox(height: 16),
          const AvisoInfo(texto: 'Dados fictícios de demonstração. Você vê apenas a sua matrícula.'),
        ]);
      },
    );
  }
}

class PedidosView extends StatelessWidget {
  const PedidosView({super.key, required this.vm});
  final DesempenhoViewModel vm;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: vm,
      builder: (context, _) {
        final itens = vm.todasConferencias;
        return Pagina(larguraMaxima: 860, children: [
          CabecalhoPagina(
            titulo: 'Pedidos de conferência',
            subtitulo: 'Acompanhe o que você pediu e as respostas do professor.',
            acoes: [
              OutlinedButton.icon(
                onPressed: vm.carregando ? null : vm.carregar,
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Atualizar'),
              ),
            ],
          ),
          const SizedBox(height: 20),
          if (vm.carregando)
            const EstadoCarregando()
          else if (itens.isEmpty)
            const EstadoVazio(
              texto: 'Você ainda não fez pedidos. Use "Solicitar conferência" em Meu desempenho.',
              icone: Icons.mark_email_read_outlined,
            )
          else
            for (final (m, c) in itens)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Cartao(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Expanded(
                          child: Text('${m.disciplina} • ${c.referenciaRotulo}',
                              style: const TextStyle(fontWeight: FontWeight.w700)),
                        ),
                        EtiquetaPequena(
                          texto: c.aberta ? 'Aguardando' : 'Respondido',
                          cor: c.aberta ? Cores.azul : Cores.verde,
                          fundo: c.aberta ? Cores.azulClaro : Cores.verdeClaro,
                        ),
                      ]),
                      const SizedBox(height: 6),
                      Text('"${c.mensagem}"'),
                      Text(fmtDataHora(c.criadoEm), style: const TextStyle(color: Cores.textoSuave, fontSize: 12)),
                      if (c.resposta != null) ...[
                        const Divider(height: 22),
                        Text('Resposta do professor: ${c.resposta}'),
                      ],
                    ]),
                  ),
                ),
              ),
        ]);
      },
    );
  }
}
