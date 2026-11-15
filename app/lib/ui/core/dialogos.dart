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
}) {
  final controle = TextEditingController();
  final form = GlobalKey<FormState>();
  String referencia = inicial ?? opcoes.first.valor;
  return showDialog<PedidoConferenciaDados>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setLocal) => AlertDialog(
        title: const Text('Solicitar conferência'),
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
            child: const Text('Enviar pedido'),
          ),
        ],
      ),
    ),
  );
}
