import 'package:flutter/material.dart';

import 'formato.dart';
import 'tema.dart';

/// Pede uma nota. Valida a escala antes de enviar; o servidor valida de novo.
Future<double?> dialogoNota(
  BuildContext context, {
  required String aluno,
  required String avaliacao,
  required double? atual,
  required double notaMaxima,
}) {
  final controle = TextEditingController(text: atual == null ? '' : fmtNum(atual));
  final form = GlobalKey<FormState>();
  return showDialog<double>(
    context: context,
    builder: (ctx) {
      void salvar() {
        if (form.currentState?.validate() ?? false) {
          Navigator.of(ctx).pop(lerNumero(controle.text));
        }
      }

      return AlertDialog(
        title: Text(atual == null ? 'Lançar nota' : 'Corrigir nota'),
        content: Form(
          key: form,
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('$aluno • $avaliacao', style: const TextStyle(color: Cores.textoSuave)),
            const SizedBox(height: 16),
            TextFormField(
              controller: controle,
              autofocus: true,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: 'Nota (0 a ${fmtNum(notaMaxima)})',
                helperText: atual == null ? null : 'Valor atual: ${fmtNum(atual)}. A correção gera nova versão.',
              ),
              validator: (v) {
                final n = lerNumero(v ?? '');
                if (n == null) return 'Digite um número, por exemplo 7,5.';
                if (n < 0 || n > notaMaxima) {
                  return 'A nota precisa estar entre 0 e ${fmtNum(notaMaxima)}.';
                }
                return null;
              },
              onFieldSubmitted: (_) => salvar(),
            ),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancelar')),
          FilledButton(onPressed: salvar, child: const Text('Salvar')),
        ],
      );
    },
  );
}

/// Texto livre com validação de tamanho mínimo.
Future<String?> dialogoTexto(
  BuildContext context, {
  required String titulo,
  required String rotulo,
  String? contexto,
  String botao = 'Enviar',
  int minimo = 5,
}) {
  final controle = TextEditingController();
  final form = GlobalKey<FormState>();
  return showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(titulo),
      content: SizedBox(
        width: 460,
        child: Form(
          key: form,
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (contexto != null) ...[
              Text(contexto, style: const TextStyle(color: Cores.textoSuave)),
              const SizedBox(height: 14),
            ],
            TextFormField(
              controller: controle,
              autofocus: true,
              maxLines: 4,
              maxLength: 1000,
              decoration: InputDecoration(labelText: rotulo, alignLabelWithHint: true),
              validator: (v) => (v == null || v.trim().length < minimo)
                  ? 'Escreva pelo menos $minimo caracteres.'
                  : null,
            ),
          ]),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancelar')),
        FilledButton(
          onPressed: () {
            if (form.currentState?.validate() ?? false) {
              Navigator.of(ctx).pop(controle.text.trim());
            }
          },
          child: Text(botao),
        ),
      ],
    ),
  );
}

class OpcaoReferencia {
  const OpcaoReferencia(this.valor, this.rotulo);
  final String valor;
  final String rotulo;
}

class PedidoConferenciaDados {
  const PedidoConferenciaDados(this.referencia, this.mensagem);
  final String referencia;
  final String mensagem;
}

/// Pedido de conferência do aluno, ligado a um registro específico (RF07).
Future<PedidoConferenciaDados?> dialogoConferencia(
  BuildContext context, {
  required List<OpcaoReferencia> opcoes,
  String? inicial,
  String? mensagem,
  bool editar = false,
}) {
  final controle = TextEditingController(text: mensagem ?? '');
  final form = GlobalKey<FormState>();
  String referencia = inicial ?? opcoes.first.valor;
  return showDialog<PedidoConferenciaDados>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setLocal) => AlertDialog(
        title: Text(editar ? 'Editar pedido' : 'Solicitar conferência'),
        content: SizedBox(
          width: 480,
          child: Form(
            key: form,
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text(
                'O pedido chega ao professor da turma. Nenhuma nota é alterada automaticamente.',
                style: TextStyle(color: Cores.textoSuave),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: referencia,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Registro'),
                items: [
                  for (final o in opcoes) DropdownMenuItem(value: o.valor, child: Text(o.rotulo)),
                ],
                onChanged: (v) => setLocal(() => referencia = v ?? referencia),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: controle,
                maxLines: 4,
                maxLength: 1000,
                decoration: const InputDecoration(
                  labelText: 'O que você quer que o professor confira?',
                  alignLabelWithHint: true,
                ),
                validator: (v) => (v == null || v.trim().length < 5)
                    ? 'Descreva o que precisa ser conferido (mínimo de 5 caracteres).'
                    : null,
              ),
            ]),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancelar')),
          FilledButton(
            onPressed: () {
              if (form.currentState?.validate() ?? false) {
                Navigator.of(ctx).pop(PedidoConferenciaDados(referencia, controle.text.trim()));
              }
            },
            child: Text(editar ? 'Salvar alterações' : 'Enviar pedido'),
          ),
        ],
      ),
    ),
  );
}


/// Confirmação simples antes de uma ação que não pode ser desfeita.
Future<bool> dialogoConfirmacao(BuildContext context,
    {required String titulo, required String texto, required String acao}) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(titulo),
      content: Text(texto),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancelar')),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: Cores.vermelho),
          onPressed: () => Navigator.of(ctx).pop(true),
          child: Text(acao),
        ),
      ],
    ),
  );
  return ok ?? false;
}

class NovaAtividadeDados {
  const NovaAtividadeDados(this.titulo, this.prazo, this.descricao);
  final String titulo;
  final String prazo; // AAAA-MM-DD
  final String descricao;
}

/// Formulário de nova atividade: título, prazo (seletor de data) e descrição.
Future<NovaAtividadeDados?> dialogoAtividade(BuildContext context) {
  final titulo = TextEditingController();
  final descricao = TextEditingController();
  final prazoTexto = TextEditingController();
  final form = GlobalKey<FormState>();
  DateTime? prazo;
  String dois(int n) => n.toString().padLeft(2, '0');

  return showDialog<NovaAtividadeDados>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setLocal) => AlertDialog(
        title: const Text('Nova atividade'),
        content: SizedBox(
          width: 460,
          child: Form(
            key: form,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextFormField(
                controller: titulo,
                autofocus: true,
                maxLength: 120,
                decoration: const InputDecoration(labelText: 'Título', hintText: 'Ex.: Lista 3: lógica'),
                validator: (v) => (v == null || v.trim().length < 3)
                    ? 'O título precisa de pelo menos 3 caracteres.'
                    : null,
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: prazoTexto,
                readOnly: true,
                decoration: const InputDecoration(
                  labelText: 'Prazo',
                  suffixIcon: Icon(Icons.event_outlined),
                ),
                validator: (_) => prazo == null ? 'Escolha a data de entrega.' : null,
                onTap: () async {
                  final hoje = DateTime.now();
                  final escolhido = await showDatePicker(
                    context: ctx,
                    initialDate: prazo ?? hoje.add(const Duration(days: 7)),
                    firstDate: hoje.subtract(const Duration(days: 365)),
                    lastDate: hoje.add(const Duration(days: 365)),
                  );
                  if (escolhido != null) {
                    setLocal(() {
                      prazo = escolhido;
                      prazoTexto.text = '${dois(escolhido.day)}/${dois(escolhido.month)}/${escolhido.year}';
                    });
                  }
                },
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: descricao,
                maxLines: 3,
                maxLength: 400,
                decoration: const InputDecoration(labelText: 'Descrição (opcional)', alignLabelWithHint: true),
              ),
            ]),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancelar')),
          FilledButton(
            onPressed: () {
              if (form.currentState?.validate() ?? false) {
                final p = prazo!;
                Navigator.of(ctx).pop(NovaAtividadeDados(
                  titulo.text.trim(),
                  '${p.year}-${dois(p.month)}-${dois(p.day)}',
                  descricao.text.trim(),
                ));
              }
            },
            child: const Text('Criar atividade'),
          ),
        ],
      ),
    ),
  );
}
