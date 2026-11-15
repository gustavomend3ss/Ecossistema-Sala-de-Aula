/// Formatação em português do Brasil, sem dependências externas.

String fmtNum(double? v, {int casas = 1}) {
  if (v == null) return '—';
  return v.toStringAsFixed(casas).replaceAll('.', ',');
}

String fmtPct(double? v) {
  if (v == null) return '—';
  if (v == v.roundToDouble()) return '${v.toInt()}%';
  return '${fmtNum(v)}%';
}

String _dois(int n) => n.toString().padLeft(2, '0');

String fmtDataHora(String iso) {
  final d = DateTime.tryParse(iso);
  if (d == null) return iso;
  final l = d.toLocal();
  return '${_dois(l.day)}/${_dois(l.month)}/${l.year} às ${_dois(l.hour)}:${_dois(l.minute)}';
}

String fmtData(String iso) {
  final d = DateTime.tryParse(iso);
  if (d == null) return iso;
  return '${_dois(d.day)}/${_dois(d.month)}';
}

/// Converte "7,5" ou "7.5" em 7.5. Devolve null se não for número.
double? lerNumero(String texto) =>
    double.tryParse(texto.trim().replaceAll(',', '.'));

const rotuloPrioridade = {
  'prioridade_alta': 'Prioridade alta',
  'alerta_media': 'Alerta de média',
  'alerta_frequencia': 'Alerta de frequência',
  'conferir_dados': 'Conferir dados',
  'sem_alerta': 'Sem alerta',
};

const rotuloDecisao = {
  'confirmado': 'Alerta confirmado',
  'ajustar_registro': 'Ajustar registro',
  'sem_acao': 'Sem ação necessária',
};

const descricaoRegra = {
  'R1': 'Média avaliável menor que o mínimo → alerta de média',
  'R2': 'Frequência avaliável menor que o mínimo → alerta de frequência',
  'R3': 'R1 e R2 ao mesmo tempo → prioridade alta de conferência',
  'R4': 'Dado ausente ou inconsistente → indicador não avaliável',
  'R5': 'Registro ou critério atualizado → nova análise; anterior mantida',
};
