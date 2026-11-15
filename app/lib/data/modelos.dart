// Modelos que espelham o JSON da API. Só leitura: o app não calcula
// indicadores; ele exibe o que o servidor calculou.

double? _num(dynamic v) => v == null ? null : (v as num).toDouble();
int _int(dynamic v) => v == null ? 0 : (v as num).toInt();
String _str(dynamic v) => v == null ? '' : v.toString();
List<T> _lista<T>(dynamic v, T Function(Map<String, dynamic>) f) => v == null
    ? <T>[]
    : (v as List).map((e) => f(Map<String, dynamic>.from(e as Map))).toList();

class Usuario {
  Usuario({required this.id, required this.nome, required this.login, required this.perfil});

  factory Usuario.fromJson(Map<String, dynamic> j) => Usuario(
      id: _int(j['id']), nome: _str(j['nome']), login: _str(j['login']), perfil: _str(j['perfil']));

  final int id;
  final String nome;
  final String login;
  final String perfil;

  bool get professor => perfil == 'professor';

  String get iniciais {
    final partes = nome.replaceAll('.', '').split(' ').where((p) => p.isNotEmpty).toList();
    if (partes.isEmpty) return '?';
    if (partes.length == 1) return partes.first[0].toUpperCase();
    return (partes.first[0] + partes.last[0]).toUpperCase();
  }
}

class Criterios {
  Criterios({
    required this.versao,
    required this.descricao,
    required this.mediaMinima,
    required this.frequenciaMinima,
    required this.atrasosMaximos,
  });

  factory Criterios.fromJson(Map<String, dynamic> j) => Criterios(
        versao: _str(j['versao']),
        descricao: _str(j['descricao']),
        mediaMinima: _num(j['media_minima']) ?? 0,
        frequenciaMinima: _num(j['frequencia_minima']) ?? 0,
        atrasosMaximos: _int(j['atrasos_maximos']),
      );

  final String versao;
  final String descricao;
  final double mediaMinima;
  final double frequenciaMinima;
  final int atrasosMaximos;
}

class Pendencia {
  Pendencia({required this.indicador, required this.regra, required this.motivo});

  factory Pendencia.fromJson(Map<String, dynamic> j) =>
      Pendencia(indicador: _str(j['indicador']), regra: _str(j['regra']), motivo: _str(j['motivo']));

  final String indicador;
  final String regra;
  final String motivo;
}

class TurmaResumo {
  TurmaResumo({
    required this.id,
    required this.disciplina,
    required this.periodo,
    required this.descricao,
    required this.estudantes,
    required this.criterios,
    required this.alertas,
    required this.pendencias,
    required this.semAnaliseAtual,
    required this.conferenciasAbertas,
    this.matriculaId,
    this.codigo,
  });

  factory TurmaResumo.fromJson(Map<String, dynamic> j) => TurmaResumo(
        id: _int(j['id']),
        disciplina: _str(j['disciplina']),
        periodo: _str(j['periodo']),
        descricao: _str(j['descricao']),
        estudantes: _int(j['estudantes']),
        criterios: _str(j['criterios']),
        alertas: _int(j['alertas']),
        pendencias: _int(j['pendencias']),
        semAnaliseAtual: _int(j['sem_analise_atual']),
        conferenciasAbertas: _int(j['conferencias_abertas']),
        matriculaId: j['matricula_id'] == null ? null : _int(j['matricula_id']),
        codigo: j['codigo'] as String?,
      );

  final int id;
  final String disciplina;
  final String periodo;
  final String descricao;
  final int estudantes;
  final String criterios;
  final int alertas;
  final int pendencias;
  final int semAnaliseAtual;
  final int conferenciasAbertas;
  final int? matriculaId;
  final String? codigo;
}

class AvaliacaoInfo {
  AvaliacaoInfo({required this.id, required this.nome, required this.peso, required this.notaMaxima, required this.obrigatoria});

  factory AvaliacaoInfo.fromJson(Map<String, dynamic> j) => AvaliacaoInfo(
        id: _int(j['id']),
        nome: _str(j['nome']),
        peso: _num(j['peso']) ?? 1,
        notaMaxima: _num(j['nota_maxima']) ?? 10,
        obrigatoria: j['obrigatoria'] == true,
      );

  final int id;
  final String nome;
  final double peso;
  final double notaMaxima;
  final bool obrigatoria;
}

class AulaInfo {
  AulaInfo({required this.id, required this.ordem, required this.data, required this.tema, required this.unidades});

  factory AulaInfo.fromJson(Map<String, dynamic> j) => AulaInfo(
        id: _int(j['id']),
        ordem: _int(j['ordem']),
        data: _str(j['data']),
        tema: _str(j['tema']),
        unidades: _int(j['unidades']),
      );

  final int id;
  final int ordem;
  final String data;
  final String tema;
  final int unidades;
}

/// Atividade com prazo e a contagem de situações das entregas da turma.
class AtividadeResumo {
  AtividadeResumo({
    required this.id,
    required this.titulo,
    required this.descricao,
    required this.prazo,
    required this.vencida,
    required this.contagem,
    required this.total,
  });

  factory AtividadeResumo.fromJson(Map<String, dynamic> j) => AtividadeResumo(
        id: _int(j['id']),
        titulo: _str(j['titulo']),
        descricao: _str(j['descricao']),
        prazo: _str(j['prazo']),
        vencida: j['vencida'] == true,
        contagem: (j['contagem'] as Map? ?? {}).map((k, v) => MapEntry(k.toString(), _int(v))),
        total: _int(j['total']),
      );

  final int id;
  final String titulo;
  final String descricao;
  final String prazo;
  final bool vencida;
  final Map<String, int> contagem;
  final int total;

  int get noPrazo => contagem['entregue'] ?? 0;
  int get comAtraso => contagem['entregue_atraso'] ?? 0;
  int get semEntrega => contagem['atrasada'] ?? 0;
  int get emAberto => contagem['aberta'] ?? 0;
}

class Acompanhamento {
  Acompanhamento({required this.analiseId, required this.prioridade, required this.regras, required this.desatualizada});

  factory Acompanhamento.fromJson(Map<String, dynamic> j) => Acompanhamento(
        analiseId: _int(j['analise_id']),
        prioridade: _str(j['prioridade']),
        regras: (j['regras'] as List? ?? []).map((e) => e.toString()).toList(),
        desatualizada: j['desatualizada'] == true,
      );

  final int analiseId;
  final String prioridade;
  final List<String> regras;
  final bool desatualizada;
}

class EstudanteLinha {
  EstudanteLinha({
    required this.matriculaId,
    required this.codigo,
    required this.aluno,
    required this.notas,
    required this.presencas,
    required this.entregas,
    required this.atividadesSemEntrega,
    required this.atividadesVencidas,
    required this.media,
    required this.frequencia,
    required this.presencasCount,
    required this.unidades,
    required this.completude,
    required this.pendencias,
    required this.acompanhamento,
    required this.conferenciasAbertas,
  });

  factory EstudanteLinha.fromJson(Map<String, dynamic> j) => EstudanteLinha(
        matriculaId: _int(j['matricula_id']),
        codigo: _str(j['codigo']),
        aluno: _str(j['aluno']),
        notas: (j['notas'] as Map? ?? {}).map((k, v) => MapEntry(k.toString(), _num(v))),
        presencas: (j['presencas_por_aula'] as Map? ?? {}).map((k, v) => MapEntry(k.toString(), v as bool?)),
        entregas: (j['entregas_por_atividade'] as Map? ?? {}).map((k, v) => MapEntry(k.toString(), _str(v))),
        atividadesSemEntrega: _int(j['atividades_sem_entrega']),
        atividadesVencidas: _int(j['atividades_vencidas']),
        media: _num(j['media']),
        frequencia: _num(j['frequencia']),
        presencasCount: _int(j['presencas']),
        unidades: _int(j['unidades_consideradas']),
        completude: _str(j['completude']),
        pendencias: _lista(j['pendencias'], Pendencia.fromJson),
        acompanhamento: j['acompanhamento'] == null
            ? null
            : Acompanhamento.fromJson(Map<String, dynamic>.from(j['acompanhamento'] as Map)),
        conferenciasAbertas: _int(j['conferencias_abertas']),
      );

  final int matriculaId;
  final String codigo;
  final String aluno;
  final Map<String, double?> notas;
  final Map<String, bool?> presencas;
  final Map<String, String> entregas;
  final int atividadesSemEntrega;
  final int atividadesVencidas;
  final double? media;
  final double? frequencia;
  final int presencasCount;
  final int unidades;
  final String completude;
  final List<Pendencia> pendencias;
  final Acompanhamento? acompanhamento;
  final int conferenciasAbertas;

  int get presentes => presencas.values.where((p) => p == true).length;
  int get registradas => presencas.values.where((p) => p != null).length;
}

class TurmaDetalhe {
  TurmaDetalhe({
    required this.id,
    required this.disciplina,
    required this.periodo,
    required this.descricao,
    required this.criterios,
    required this.avaliacoes,
    required this.aulas,
    required this.atividades,
    required this.estudantes,
  });

  factory TurmaDetalhe.fromJson(Map<String, dynamic> j) => TurmaDetalhe(
        id: _int(j['id']),
        disciplina: _str(j['disciplina']),
        periodo: _str(j['periodo']),
        descricao: _str(j['descricao']),
        criterios: Criterios.fromJson(Map<String, dynamic>.from(j['criterios'] as Map)),
        avaliacoes: _lista(j['avaliacoes'], AvaliacaoInfo.fromJson),
        aulas: _lista(j['aulas'], AulaInfo.fromJson),
        atividades: _lista(j['atividades'], AtividadeResumo.fromJson),
        estudantes: _lista(j['estudantes'], EstudanteLinha.fromJson),
      );

  final int id;
  final String disciplina;
  final String periodo;
  final String descricao;
  final Criterios criterios;
  final List<AvaliacaoInfo> avaliacoes;
  final List<AulaInfo> aulas;
  final List<AtividadeResumo> atividades;
  final List<EstudanteLinha> estudantes;
}

class Indicadores {
  Indicadores({
    required this.media,
    required this.frequencia,
    required this.presencas,
    required this.unidadesConsideradas,
    required this.atividadesVencidas,
    required this.atividadesSemEntrega,
    required this.taxaEntrega,
    required this.completude,
    required this.pendencias,
  });

  factory Indicadores.fromJson(Map<String, dynamic> j) => Indicadores(
        media: _num(j['media']),
        frequencia: _num(j['frequencia']),
        presencas: _int(j['presencas']),
        unidadesConsideradas: _int(j['unidades_consideradas']),
        atividadesVencidas: _int(j['atividades_vencidas']),
        atividadesSemEntrega: _int(j['atividades_sem_entrega']),
        taxaEntrega: _num(j['taxa_entrega']),
        completude: _str(j['completude']),
        pendencias: _lista(j['pendencias'], Pendencia.fromJson),
      );

  final double? media;
  final double? frequencia;
  final int presencas;
  final int unidadesConsideradas;
  final int atividadesVencidas;
  final int atividadesSemEntrega;
  final double? taxaEntrega;
  final String completude;
  final List<Pendencia> pendencias;
}

class RegistroNota {
  RegistroNota({
    required this.avaliacaoId,
    required this.nome,
    required this.peso,
    required this.notaMaxima,
    required this.obrigatoria,
    required this.valor,
  });

  factory RegistroNota.fromJson(Map<String, dynamic> j) => RegistroNota(
        avaliacaoId: _int(j['avaliacao_id']),
        nome: _str(j['nome']),
        peso: _num(j['peso']) ?? 1,
        notaMaxima: _num(j['nota_maxima']) ?? 10,
        obrigatoria: j['obrigatoria'] == true,
        valor: _num(j['valor']),
      );

  final int avaliacaoId;
  final String nome;
  final double peso;
  final double notaMaxima;
  final bool obrigatoria;
  final double? valor;
}

class RegistroAula {
  RegistroAula({required this.aulaId, required this.ordem, required this.data, required this.tema, required this.unidades, required this.presente});

  factory RegistroAula.fromJson(Map<String, dynamic> j) => RegistroAula(
        aulaId: _int(j['aula_id']),
        ordem: _int(j['ordem']),
        data: _str(j['data']),
        tema: _str(j['tema']),
        unidades: _int(j['unidades']),
        presente: j['presente'] as bool?,
      );

  final int aulaId;
  final int ordem;
  final String data;
  final String tema;
  final int unidades;
  final bool? presente;
}

class RegistroAtividade {
  RegistroAtividade({
    required this.atividadeId,
    required this.titulo,
    required this.prazo,
    required this.entregueEm,
    required this.situacao,
  });

  factory RegistroAtividade.fromJson(Map<String, dynamic> j) => RegistroAtividade(
        atividadeId: _int(j['atividade_id']),
        titulo: _str(j['titulo']),
        prazo: _str(j['prazo']),
        entregueEm: j['entregue_em'] as String?,
        situacao: _str(j['situacao']),
      );

  final int atividadeId;
  final String titulo;
  final String prazo;
  final String? entregueEm;
  final String situacao;

  bool get entregue => entregueEm != null;
}

class Registros {
  Registros({
    required this.matriculaId,
    required this.codigo,
    required this.aluno,
    required this.turmaId,
    required this.disciplina,
    required this.periodo,
    required this.versaoRegistros,
    required this.avaliacoes,
    required this.aulas,
    required this.atividades,
    required this.indicadores,
  });

  factory Registros.fromJson(Map<String, dynamic> j) => Registros(
        matriculaId: _int(j['matricula_id']),
        codigo: _str(j['codigo']),
        aluno: _str(j['aluno']),
        turmaId: _int(j['turma_id']),
        disciplina: _str(j['disciplina']),
        periodo: _str(j['periodo']),
        versaoRegistros: _int(j['versao_registros']),
        avaliacoes: _lista(j['avaliacoes'], RegistroNota.fromJson),
        aulas: _lista(j['aulas'], RegistroAula.fromJson),
        atividades: _lista(j['atividades'], RegistroAtividade.fromJson),
        indicadores: Indicadores.fromJson(Map<String, dynamic>.from(j['indicadores'] as Map)),
      );

  final int matriculaId;
  final String codigo;
  final String aluno;
  final int turmaId;
  final String disciplina;
  final String periodo;
  final int versaoRegistros;
  final List<RegistroNota> avaliacoes;
  final List<RegistroAula> aulas;
  final List<RegistroAtividade> atividades;
  final Indicadores indicadores;
}

class RegraAcionada {
  RegraAcionada({required this.regra, required this.corpo, required this.cabeca, required this.evidencia, required this.fc});

  factory RegraAcionada.fromJson(Map<String, dynamic> j) => RegraAcionada(
        regra: _str(j['regra']),
        corpo: (j['corpo'] as List? ?? []).map((e) => e.toString()).toList(),
        cabeca: _str(j['cabeca']),
        evidencia: Map<String, dynamic>.from(j['evidencia'] as Map? ?? {}),
        fc: _num(j['fc']) ?? 1,
      );

  final String regra;
  final List<String> corpo;
  final String cabeca;
  final Map<String, dynamic> evidencia;
  final double fc;
}

class Revisao {
  Revisao({required this.id, required this.autor, required this.decisao, required this.observacao, required this.criadoEm});

  factory Revisao.fromJson(Map<String, dynamic> j) => Revisao(
        id: _int(j['id']),
        autor: _str(j['autor']),
        decisao: _str(j['decisao']),
        observacao: _str(j['observacao']),
        criadoEm: _str(j['criado_em']),
      );

  final int id;
  final String autor;
  final String decisao;
  final String observacao;
  final String criadoEm;
}

class Analise {
  Analise({
    required this.id,
    required this.criadoEm,
    required this.solicitadoPor,
    required this.versaoRegistros,
    required this.versaoCriterios,
    required this.desatualizada,
    required this.media,
    required this.frequencia,
    required this.presencas,
    required this.unidades,
    required this.atividadesVencidas,
    required this.atividadesSemEntrega,
    required this.certeza,
    required this.prioridade,
    required this.regras,
    required this.acionadas,
    required this.pendencias,
    required this.motivo,
    required this.sintese,
    required this.sinteseStatus,
    required this.mediaMinima,
    required this.frequenciaMinima,
    required this.atrasosMaximos,
    required this.revisoes,
  });

  factory Analise.fromJson(Map<String, dynamic> j) {
    final c = Map<String, dynamic>.from(j['criterios'] as Map? ?? {});
    return Analise(
      id: _int(j['id']),
      criadoEm: _str(j['criado_em']),
      solicitadoPor: _str(j['solicitado_por']),
      versaoRegistros: _int(j['versao_registros']),
      versaoCriterios: _str(j['versao_criterios']),
      desatualizada: j['desatualizada'] == true,
      media: _num(j['media']),
      frequencia: _num(j['frequencia']),
      presencas: _int(j['presencas']),
      unidades: _int(j['unidades_consideradas']),
      atividadesVencidas: _int(j['atividades_vencidas']),
      atividadesSemEntrega: _int(j['atividades_sem_entrega']),
      certeza: _num(j['certeza']) ?? 0,
      prioridade: _str(j['prioridade']),
      regras: (j['regras'] as List? ?? []).map((e) => e.toString()).toList(),
      acionadas: _lista(j['acionadas'], RegraAcionada.fromJson),
      pendencias: _lista(j['pendencias'], Pendencia.fromJson),
      motivo: _str(j['motivo']),
      sintese: j['sintese'] as String?,
      sinteseStatus: _str(j['sintese_status']),
      mediaMinima: _num(c['media_minima']) ?? 0,
      frequenciaMinima: _num(c['frequencia_minima']) ?? 0,
      atrasosMaximos: _int(c['atrasos_maximos']),
      revisoes: _lista(j['revisoes'], Revisao.fromJson),
    );
  }

  final int id;
  final String criadoEm;
  final String solicitadoPor;
  final int versaoRegistros;
  final String versaoCriterios;
  final bool desatualizada;
  final double? media;
  final double? frequencia;
  final int presencas;
  final int unidades;
  final int atividadesVencidas;
  final int atividadesSemEntrega;
  final double certeza;
  final String prioridade;
  final List<String> regras;
  final List<RegraAcionada> acionadas;
  final List<Pendencia> pendencias;
  final String motivo;
  final String? sintese;
  final String sinteseStatus;
  final double mediaMinima;
  final double frequenciaMinima;
  final int atrasosMaximos;
  final List<Revisao> revisoes;
}

class Alteracao {
  Alteracao({required this.tipo, required this.referencia, required this.anterior, required this.novo, required this.autor, required this.criadoEm});

  factory Alteracao.fromJson(Map<String, dynamic> j) => Alteracao(
        tipo: _str(j['tipo']),
        referencia: _str(j['referencia']),
        anterior: j['valor_anterior'] as String?,
        novo: _str(j['valor_novo']),
        autor: _str(j['autor']),
        criadoEm: _str(j['criado_em']),
      );

  final String tipo;
  final String referencia;
  final String? anterior;
  final String novo;
  final String autor;
  final String criadoEm;
}

class Conferencia {
  Conferencia({
    required this.id,
    required this.autor,
    required this.referenciaRotulo,
    required this.mensagem,
    required this.status,
    required this.resposta,
    required this.criadoEm,
  });

  factory Conferencia.fromJson(Map<String, dynamic> j) => Conferencia(
        id: _int(j['id']),
        autor: _str(j['autor']),
        referenciaRotulo: _str(j['referencia_rotulo']),
        mensagem: _str(j['mensagem']),
        status: _str(j['status']),
        resposta: j['resposta'] as String?,
        criadoEm: _str(j['criado_em']),
      );

  final int id;
  final String autor;
  final String referenciaRotulo;
  final String mensagem;
  final String status;
  final String? resposta;
  final String criadoEm;

  bool get aberta => status == 'aberto';
}

class DetalheIndicador {
  DetalheIndicador({required this.rotulo, required this.valor, required this.limite, required this.alerta, required this.avaliavel});

  factory DetalheIndicador.fromJson(Map<String, dynamic> j) => DetalheIndicador(
        rotulo: _str(j['rotulo']),
        valor: _str(j['valor']),
        limite: _str(j['limite']),
        alerta: j['alerta'] == true,
        avaliavel: j['avaliavel'] != false,
      );

  final String rotulo;
  final String valor;
  final String limite;
  final bool alerta;
  final bool avaliavel;
}

class ItemAssistente {
  ItemAssistente({
    required this.matriculaId,
    required this.codigo,
    required this.aluno,
    required this.titulo,
    required this.prioridade,
    required this.certeza,
    required this.detalhes,
    required this.observacao,
  });

  factory ItemAssistente.fromJson(Map<String, dynamic> j) => ItemAssistente(
        matriculaId: _int(j['matricula_id']),
        codigo: _str(j['codigo']),
        aluno: _str(j['aluno']),
        titulo: _str(j['titulo']),
        prioridade: _str(j['prioridade']),
        certeza: _num(j['certeza']) ?? 0,
        detalhes: _lista(j['detalhes'], DetalheIndicador.fromJson),
        observacao: j['observacao'] as String?,
      );

  final int matriculaId;
  final String codigo;
  final String aluno;
  final String titulo;
  final String prioridade;
  final double certeza;
  final List<DetalheIndicador> detalhes;
  final String? observacao;
}

class Fonte {
  Fonte({required this.titulo, required this.descricao});

  factory Fonte.fromJson(Map<String, dynamic> j) =>
      Fonte(titulo: _str(j['titulo']), descricao: _str(j['descricao']));

  final String titulo;
  final String descricao;
}

class RespostaAssistente {
  RespostaAssistente({required this.pergunta, required this.intencao, required this.texto, required this.itens, required this.fontes, required this.aviso});

  factory RespostaAssistente.fromJson(Map<String, dynamic> j) => RespostaAssistente(
        pergunta: _str(j['pergunta']),
        intencao: _str(j['intencao']),
        texto: _str(j['texto']),
        itens: _lista(j['itens'], ItemAssistente.fromJson),
        fontes: _lista(j['fontes'], Fonte.fromJson),
        aviso: _str(j['aviso']),
      );

  final String pergunta;
  final String intencao;
  final String texto;
  final List<ItemAssistente> itens;
  final List<Fonte> fontes;
  final String aviso;
}
