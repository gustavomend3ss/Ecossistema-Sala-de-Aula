# Ecossistema de Gestão Acadêmica com Assistente Docente

Projeto integrado de **Desenvolvimento de Sistemas Web** e **Inteligência Artificial**, FAINOR, Engenharia de Computação, 2026.2. Prof. Wallas Fróes de Oliveira.

A plataforma organiza turmas, notas, frequência e acesso por perfil. O assistente calcula média e frequência, aplica as regras R1 a R5 por encadeamento para a frente e explica cada alerta com o dado e o critério usados. Quem decide é o professor: ele confere, revisa e registra a revisão. O assistente não altera notas.

> **Versão 0.1 — primeira versão funcional.** Todos os dados são fictícios. Os limites de 6,0 e 80% (perfil DEMO-v1) são didáticos e não correspondem aos critérios oficiais da FAINOR.

---

## Estrutura

```
ecossistema-academico/
├── backend/                  API em Python (FastAPI) + motor de regras
│   ├── app/
│   │   ├── motor/            ← parte de IA: fatos, regras, inferência, explicação
│   │   │   ├── motor.py      cálculo dos indicadores, R1–R4, encadeamento para a frente
│   │   │   └── explicacao.py motivo em texto (dado + critério, sem adivinhar causa)
│   │   ├── servicos/
│   │   │   ├── analises.py   cópia fixa dos dados → motor → R5 → grava (nunca sobrescreve)
│   │   │   ├── assistente.py perguntas sobre a turma, respostas com fontes
│   │   │   ├── sintese.py    adaptador opcional do Gemini + conferência da síntese
│   │   │   └── registros.py  notas e presenças com versão e histórico
│   │   ├── rotas/api.py      rotas REST (Quadro 4 do Bloco 2 + extensões)
│   │   ├── models.py         12 entidades + sessão + histórico de alterações
│   │   ├── seguranca.py      token, hash de senha, verificação de vínculo
│   │   └── seed.py           dados fictícios (A01, A02 e A03 do Quadro 7)
│   └── tests/                T01 a T09 (pytest)
├── app/                      Flutter (web + Android), arquitetura view / view model / repositório
│   ├── lib/
│   │   ├── data/             api_client, modelos, repositórios
│   │   └── ui/               core, login, professor, aluno
│   └── test/                 testes de widget e de modelos
└── docker-compose.yml        PostgreSQL 16
```

---

## Como rodar do zero

### Pré-requisitos

- Python 3.11 ou mais novo
- Flutter 3.22 ou mais novo (`flutter --version`)
- Docker (opcional, para o PostgreSQL; sem ele a API usa SQLite)

### 1. Banco de dados (opcional)

```bash
docker compose up -d db
```

### 2. API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # sem Docker, apague a linha DATABASE_URL
python -m app.seed                 # recria o banco com os dados fictícios
uvicorn app.main:app --reload --port 8000
```

A documentação interativa das rotas fica em <http://localhost:8000/docs>.

### 3. Aplicativo Flutter

As pastas de plataforma (`web/` e `android/`) não vão no repositório. Gere uma vez:

```bash
cd app
flutter create . --project-name ecossistema_academico --platforms=web,android
flutter pub get
```

O `flutter create .` só cria arquivos que estão faltando; ele não sobrescreve `lib/` nem `test/`.

**Navegador (foco de Desenvolvimento Web):**

```bash
flutter run -d chrome --dart-define=API_URL=http://localhost:8000
```

**Android (solução mobile pedida em IA)**, no emulador:

```bash
flutter run -d emulator-5554 --dart-define=API_URL=http://10.0.2.2:8000
```

> No Android, a API local roda em HTTP. Em `android/app/src/main/AndroidManifest.xml`, adicione dentro de `<manifest>` a linha `<uses-permission android:name="android.permission.INTERNET"/>` e, na tag `<application>`, o atributo `android:usesCleartextTraffic="true"`. Use isso só em desenvolvimento.

### Usuários de demonstração

Senha de todos: `demo123`

| Usuário | Perfil | O que mostra |
|---|---|---|
| `prof.gabriel` | professor | Turmas de IA e de Web |
| `prof.helena` | professora | Só a turma de Banco de Dados (serve para testar o bloqueio do T06) |
| `ana.lima` | aluna | A01: média 5,2 e 76% → R1, R2 e R3 |
| `bruno.reis` | aluno | A02: média 7,5 e 92% → sem alerta |
| `carla.dias` | aluna | A03: Avaliação 2 não lançada → R4 |

A turma de Web tem casos extras: W02 é a fronteira do T02 (6,0 e 80%, sem alerta), W03 aciona só R2 e W04 tem uma presença sem registro.

---

## Testes

```bash
cd backend && pytest -q          # 29 testes: motor + API (T01 a T09)
cd app && flutter test           # formatação, modelos e widgets
```

Para rodar os testes da API no PostgreSQL em vez do SQLite:

```bash
TEST_DATABASE_URL=postgresql+psycopg://ecossistema:ecossistema@localhost:5432/ecossistema pytest -q
```

| Caso (Quadro 9) | Onde está |
|---|---|
| T01: A01 completo → R1, R2, R3 | `test_motor.py::test_t01_*`, `test_api.py::test_t01_*` |
| T02: média 6,0 e 80% → sem alerta | `test_motor.py::test_t02_fronteira_menor_que` |
| T03: nota ausente não vira zero | `test_motor.py::test_t03_*` |
| T04: nenhuma aula → sem divisão por zero | `test_motor.py::test_t04_*` |
| T05: correção → nova análise, anterior preservada | `test_motor.py::test_t05_*`, `test_api.py::test_t05_*` |
| T06: acesso bloqueado no servidor | `test_api.py::test_t06_*` (3 testes) |
| T07: nota 11 rejeitada | `test_api.py::test_t07_*` |
| T08: pedido de conferência não altera nota | `test_api.py::test_t08_*` |
| T09: síntese errada ou serviço fora do ar | `test_api.py::test_t09_*` (4 testes) |

---

## Rotas da API

Rotas do Quadro 4 do Bloco 2:

| Método e rota | Finalidade |
|---|---|
| `POST /sessoes` | Autenticar e iniciar a sessão |
| `GET /turmas` | Turmas que o usuário pode acessar |
| `GET /matriculas/{id}/registros` | Notas e presenças, conferindo o vínculo |
| `PUT /matriculas/{id}/notas/{avaliacao_id}` | Salvar ou corrigir uma nota |
| `PUT /matriculas/{id}/presencas/{aula_id}` | Salvar ou corrigir uma presença |
| `POST /matriculas/{id}/analises` | Calcular e gravar a análise com os dados do servidor |
| `GET /matriculas/{id}/analises` | Histórico de análises |
| `POST /analises/{id}/revisoes` | Revisão do professor |
| `POST /matriculas/{id}/conferencias` | Pedido de conferência do aluno |

Extensões que as telas precisaram:

| Método e rota | Por quê |
|---|---|
| `GET /turmas/{id}` | Tela da turma: estudantes, notas, presenças e situação em uma chamada |
| `POST /turmas/{id}/analises` | Botão "Analisar turma" |
| `POST /turmas/{id}/assistente` | Tela do assistente (perguntas sobre a turma) |
| `GET /matriculas/{id}/historico` | Correções feitas nos registros (quem, quando, de quanto para quanto) |
| `GET /matriculas/{id}/conferencias` | Professor lê os pedidos; aluno acompanha os seus |
| `POST /conferencias/{id}/resposta` | Professor responde o pedido |
| `GET /aluno/desempenho` | Tela "Meu desempenho" |
| `DELETE /sessoes`, `GET /me` | Sair e consultar a sessão |

---

## Como o assistente funciona (parte de IA)

1. **Autorizar e buscar.** A API confere o token e o vínculo e lê uma cópia fixa dos registros.
2. **Completude (R4).** Se faltar nota obrigatória, se nenhuma aula estiver registrada ou se houver valor inconsistente, o indicador fica *não avaliável*, com a pendência explícita. Nota ausente nunca vira zero.
3. **Cálculo.** Média ponderada `Σ(nota × peso) ÷ Σ peso` e frequência `presenças ÷ unidades-aula × 100`. Os valores são arredondados a duas casas antes da comparação, para evitar que 5,9999 seja tratado como menor que 6,0.
4. **Fatos.** As comparações viram proposições (`media_baixa`, `frequencia_baixa`).
5. **Encadeamento para a frente.** As cláusulas R1, R2 e R3 são aplicadas até não surgir conclusão nova. Cada regra acionada guarda sua evidência.
6. **R5 e histórico.** Se os registros ou critérios mudaram desde a última análise, a nova análise registra R5 e aponta a anterior, que continua gravada.
7. **Síntese (opcional).** Com `GEMINI_API_KEY`, o Gemini recebe só os fatos calculados, sem o nome do aluno, e devolve JSON. A API confere números, regras e pendências e descarta o texto que sugira causas. Se algo não bater, ou se o serviço falhar, vale o relatório estruturado.

O assistente de conversa classifica a pergunta por palavras-chave (acompanhamento, pendências, frequência, média, critérios, resumo ou um aluno citado) e monta a resposta só com o resultado do motor. Quando a análise de algum aluno está desatualizada, ele pede uma nova antes de responder. Essa é a autonomia delimitada descrita no PEAS.

---

## O que entrou e o que fica para depois

Entrou nesta versão (Quadro 1, coluna "Primeira versão"): login e acesso por perfil; turmas, matrículas, notas e frequência; análise com alertas e motivos; revisão do professor e histórico; área do aluno com pedido de conferência. Também entraram, além do previsto, a chamada rápida por aula, o assistente de conversa e a resposta do professor ao pedido de conferência.

Fica para as próximas versões: atividades e prazos (a dor apontada pelo professor no Bloco 1), notificações, importação de registros por arquivo e o perfil de critérios editável pela interface.

Fora do escopo, por decisão de projeto: aprovação ou reprovação automática, previsão de evasão, alteração de notas pelo assistente e uso de dados reais.
