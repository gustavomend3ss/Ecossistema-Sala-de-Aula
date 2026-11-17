# Ecossistema de Gestão Acadêmica com Assistente Docente

**Demonstração no ar:** https://ecossistema-sala-de-aula.vercel.app (senha de todos os usuários: `demo123`)

Projeto semestral integrado de **Desenvolvimento de Sistemas Web** e **Inteligência Artificial**, Engenharia de Computação, FAINOR, 2026.2.

**Equipe:** Camila Ramos, Daniel Soares Oliveira, Guilherme Pereira, Gustavo Mendes, Matheus Caires, Rauan Brandão e Samuel Cotinguiba.

**Professor:** Wallas Fróes de Oliveira.

A plataforma organiza turmas, notas, chamada, atividades com prazo e acesso por perfil. O assistente docente calcula média, frequência e situação das entregas, aplica uma base de regras por encadeamento para a frente e explica cada alerta com o dado, o critério e o fator de certeza usados. Quem decide é o professor: ele confere, revisa e registra a revisão. O assistente não altera notas.

> **Versão 0.3 (Bloco 3, assistente híbrido).** Dados fictícios. Os limites do perfil DEMO-v2 (média 6,0, frequência 80% e até 1 atividade vencida sem entrega) são didáticos e não correspondem aos critérios oficiais da FAINOR.

---

## Estrutura

```
├── backend/                  API em Python (FastAPI + SQLAlchemy)
│   ├── app/
│   │   ├── motor/            assistente: fatos, regras R1–R6, fatores de certeza, explicação
│   │   ├── servicos/         análises (R5), assistente híbrido, síntese Gemini, registros e entregas
│   │   │   ├── entidades.py  RapidFuzz: disciplinas e estudantes citados na pergunta
│   │   │   ├── consultas.py  funções autorizadas (notas, frequência, risco, alertas...)
│   │   │   ├── gemini.py     plano da pergunta e redação conferida
│   │   │   └── conversa.py   orquestra a conversa e guarda o contexto
│   │   ├── rotas/api.py      rotas REST
│   │   ├── models.py         entidades do banco
│   │   ├── seguranca.py      senha (PBKDF2), token assinado (HMAC-SHA256), vínculo
│   │   └── seed.py           dados fictícios
│   └── tests/                91 testes (pytest): motor, API, assistente, regressões e deploy
├── app/                      Flutter (web e Android), view / view model / repositório
│   ├── lib/data/             cliente HTTP, modelos, repositórios
│   ├── lib/ui/               login, professor (turmas, turma, matrícula, assistente), aluno
│   └── test/                 testes de widget e de modelos
├── scripts/                  servidor local do build web
├── .github/workflows/ci.yml  CI: pytest (SQLite e PostgreSQL), flutter analyze, test e build
├── vercel.json               configuração do deploy
└── docker-compose.yml        PostgreSQL 16 para desenvolvimento
```

---

## Como rodar do zero

### Pré-requisitos

- Git, Python 3.12 e Flutter 3.50.0 (Dart 3.14.0), as versões usadas na integração contínua (Ubuntu 24.04). As dependências da API estão com versão fixa em `backend/requirements.txt`
- Docker, só se quiser PostgreSQL local (sem ele, a API usa SQLite)

### 1. Clonar

```bash
git clone https://github.com/gustavomend3ss/Ecossistema-Sala-de-Aula.git
cd Ecossistema-Sala-de-Aula
```

### 2. API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # sem Docker, apague a linha DATABASE_URL
python -m app.seed                  # recria o banco com os dados fictícios
uvicorn app.main:app --reload --port 8000
```

A documentação interativa das rotas fica em <http://localhost:8000/docs>.

Para usar PostgreSQL: `docker compose up -d db` na raiz e mantenha a linha `DATABASE_URL` do `.env`.

### 3. App Flutter

As pastas de plataforma não vão para o repositório. Gere uma vez:

```bash
cd app
flutter create . --project-name ecossistema_academico --org br.edu.fainor --platforms=web,android
flutter pub get
```

Navegador:

```bash
flutter run -d chrome --dart-define=API_URL=http://localhost:8000
```

Android (emulador):

```bash
flutter run -d emulator-5554 --dart-define=API_URL=http://10.0.2.2:8000
```

> No Android, a API local roda em HTTP. Em `android/app/src/main/AndroidManifest.xml`, adicione `<uses-permission android:name="android.permission.INTERNET"/>` dentro de `<manifest>` e `android:usesCleartextTraffic="true"` na tag `<application>`. Só para desenvolvimento.

### 4. Build web servido junto com a API (igual à Vercel)

```bash
cd app && flutter build web --release --no-web-resources-cdn && cd ..
pip install -r backend/requirements.txt
python scripts/servidor_local.py     # abre em http://localhost:8080
```

### Usuários de demonstração

Senha de todos: `demo123`

| Usuário | Perfil | O que mostra |
|---|---|---|
| `prof.gabriel` | professor | Turmas de IA, Web, Estrutura de Dados e Computação Gráfica (esta sem notas nem aulas, para o caso "sem dados") |
| `prof.helena` | professora | Só a turma de Banco de Dados (teste de bloqueio, T06) |
| `ana.lima` | aluna | A01: média 5,2 e 76% → R1, R2, R3 (certeza 0,88) |
| `bruno.reis` | aluno | A02: notas e frequência boas, 2 atividades vencidas sem entrega → R6 |
| `carla.dias` | aluna | A03: Avaliação 2 não lançada → R4 |

---

## Deploy na Vercel

O projeto está ligado ao GitHub: cada envio à `main` gera uma nova publicação em https://ecossistema-sala-de-aula.vercel.app.

O `vercel.json` usa os **Vercel Services**: um projeto com dois serviços no mesmo domínio.

| Serviço | Pasta | O que é | Rota pública |
|---|---|---|---|
| `web` | `app/` | App Flutter compilado como site estático (download seletivo do SDK no build) | `/` |
| `api` | `backend/` | FastAPI (`app.main:app`) como função Python | `/api/*`, com o prefixo `/api` retirado antes de chegar à API |

O app chama a API em `/api` na própria origem, então não há endereço para configurar nem CORS. Não há bindings: o único cliente da API é o navegador.

O serviço `api` tem um rewrite próprio (`/api/:path(.*)?` para `/:path`) que retira o `/api` antes de a requisição chegar ao FastAPI. Testamos trocá-lo por uma transformação `request.path` e, na produção, o prefixo passou a chegar à API e todas as rotas deram 404; por isso o rewrite ficou.

1. Entre em <https://vercel.com/new> com a conta do GitHub.
2. Importe o repositório `Ecossistema-Sala-de-Aula`. Não mude nenhuma configuração: o `vercel.json` já define instalação, build e pasta de saída.
3. Em **Environment Variables**, adicione `SECRET_KEY` com um texto aleatório longo (opcional, mas recomendado) e, se quiser o Gemini, `GEMINI_API_KEY`.
4. Em **Storage**, ligue um PostgreSQL (Neon, pelo Marketplace). A Vercel cria `DATABASE_URL` sozinha; na primeira requisição a API cria as tabelas e carrega os dados fictícios.
5. Clique em **Deploy**. O primeiro build leva alguns minutos, porque baixa o Flutter.

Variáveis opcionais:

| Variável | Para quê |
|---|---|
| `DATABASE_URL` (ou `POSTGRES_URL`) | PostgreSQL persistente (Neon ou Supabase). Necessário quando a Vercel abre mais de uma instância: sem ele, cada instância tem o próprio SQLite em `/tmp` e a sessão "cai" ao trocar de instância. |
| `GEMINI_API_KEY` | Liga o Gemini no assistente (interpretação e redação) e na síntese das análises. Sem ela, tudo funciona com as regras. |
| `GEMINI_MODEL`, `GEMINI_TIMEOUT` | Modelo (padrão `gemini-2.5-flash`) e tempo máximo de espera em segundos (padrão 15). |
| `FUZZY_ACEITE`, `FUZZY_SUGESTAO`, `FUZZY_MARGEM` | Limiares do RapidFuzz (padrão 85, 70 e 4). |
| `DATA_REFERENCIA` | Fixa a data usada nos prazos (AAAA-MM-DD), útil para gravar uma demonstração. |

---

## Segurança

Medidas proporcionais a um projeto acadêmico com dados fictícios:

- Senhas guardadas só como PBKDF2-SHA256 (200 mil iterações, sal por usuário).
- Token de sessão assinado com HMAC-SHA256 e validade de 12 h; fica só na memória do app.
- `SECRET_KEY` assina os tokens. Na Vercel, defina essa variável; sem ela, a chave é derivada do endereço do banco (igual em todas as instâncias). A chave de desenvolvimento do repositório nunca é usada lá.
- Assistente: o Gemini só escolhe funções de uma lista fechada e só lê os fatos já filtrados pela permissão do usuário (código, primeiro nome e indicadores; sem login, e-mail ou id). A pergunta vai delimitada, com instrução para ignorar comandos dentro dela, e pedidos de alteração de dados são recusados antes de chegar ao modelo. O texto do Gemini é conferido contra os fatos e descartado se trouxer número, código ou nome que não está no resultado. Os logs registram só intenção, quantidade de itens e tempo.
- Conversas do assistente ficam presas ao usuário: abrir ou continuar a conversa de outra pessoa dá 404.
- Login bloqueado por 15 min após 5 senhas erradas para o mesmo usuário e endereço (resposta 429).
- Acesso conferido no servidor em toda rota: professor só vê turmas vinculadas e aluno só a própria matrícula (404 para o resto).
- Validação com Pydantic e sanitização de texto livre no servidor.
- Na Vercel: CORS fechado (app e API no mesmo domínio), `/docs` desligado e cabeçalhos `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` e HSTS; respostas da API com `Cache-Control: no-store`.
- Nenhuma chave no repositório: `backend/.env` está no `.gitignore`.

As senhas `demo123` são públicas de propósito, para a demonstração. Em uso real, os usuários teriam senhas próprias.

## Testes

```bash
cd backend && pytest -q          # 92 passam em SQLite; 1 teste adicional exige PostgreSQL
python evidencias.py             # saída obtida de cada cenário (T01 a T09, C1 a C10)
TEST_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/banco pytest -q   # os 93, em PostgreSQL
cd app && flutter analyze && flutter test
```

O GitHub Actions roda os testes da API em SQLite e PostgreSQL 16, a análise estática, os testes e o build web do Flutter a cada push. Os relatórios ficam no ramo `ci-output`.

| Caso | Onde está |
|---|---|
| T01: A01 completo → R1, R2, R3 | `test_motor.py::test_t01_*`, `test_api.py::test_t01_*` |
| T02: média 6,0 e 80% → sem alerta | `test_motor.py::test_t02_fronteira_menor_que` |
| T03: nota ausente não vira zero | `test_motor.py::test_t03_*` |
| T04: nenhuma aula → sem divisão por zero | `test_motor.py::test_t04_*` |
| T05: correção → nova análise, anterior preservada | `test_motor.py::test_t05_*`, `test_api.py::test_t05_*` |
| T06: acesso bloqueado no servidor | `test_api.py::test_t06_*` |
| T07: nota 11 rejeitada | `test_api.py::test_t07_*` |
| T08: pedido de conferência não altera nota | `test_api.py::test_t08_*` |
| T09: síntese errada ou serviço fora do ar | `test_api.py::test_t09_*` |
| R6, fatores de certeza, entregas, tokens | `test_motor.py` (R6/FC), `test_api.py` (entregas, tokens) |
| Assistente: 10 cenários (disciplina certa, com erro, nomes parecidos, inexistente, várias intenções, continuidade, sem dados, sem permissão, Gemini fora do ar, Gemini inconsistente) | `test_assistente.py::test_c1_*` a `test_c10_*` |
| Regressões: criação e vencimento de atividades, limite do prazo, textos vazios, estudante inexistente e valores incorretos na redação | `test_regressoes.py` |
| Deploy: transformação do caminho público `/api`, login, consulta, inicialização serverless e três instâncias iniciando juntas em PostgreSQL | `test_deploy.py` |

---

## Rotas da API

| Método e rota | Finalidade |
|---|---|
| `POST /sessoes` | Autenticar e receber o token |
| `GET /turmas` | Turmas do usuário |
| `GET /turmas/{id}` | Estudantes, notas, presenças, entregas e situação |
| `GET /turmas/{id}/atividades` | Radar de entregas |
| `POST /turmas/{id}/atividades` | Criar atividade (título, prazo, descrição) |
| `POST /turmas/{id}/analises` | Analisar a turma inteira |
| `POST /assistente/mensagens` | Pergunta ao assistente (`pergunta`, `conversa_id` opcional) |
| `GET /assistente/conversas` | Conversas do usuário |
| `GET /assistente/conversas/{id}` | Trocas de uma conversa |
| `POST /turmas/{id}/assistente` | Rota antiga, por turma (mantida por compatibilidade) |
| `GET /matriculas/{id}/registros` | Notas, presenças e atividades da matrícula |
| `PUT /matriculas/{id}/notas/{avaliacao_id}` | Lançar ou corrigir nota |
| `PUT /matriculas/{id}/presencas/{aula_id}` | Lançar ou corrigir presença |
| `PUT /matriculas/{id}/entregas/{atividade_id}` | Marcar ou desmarcar entrega |
| `POST /matriculas/{id}/analises` | Nova análise |
| `GET /matriculas/{id}/analises` | Histórico de análises |
| `GET /matriculas/{id}/historico` | Correções feitas nos registros |
| `POST /analises/{id}/revisoes` | Revisão do professor |
| `POST /matriculas/{id}/conferencias` | Pedido de conferência do aluno |
| `GET /matriculas/{id}/conferencias` | Pedidos da matrícula |
| `PUT /conferencias/{id}` | Aluno edita o próprio pedido (só enquanto não foi respondido) |
| `DELETE /conferencias/{id}` | Aluno remove o próprio pedido (só enquanto não foi respondido) |
| `POST /conferencias/{id}/resposta` | Resposta do professor |
| `GET /aluno/desempenho` | Área do aluno |

Na Vercel e no servidor local, todas ficam sob `/api` (por exemplo, `/api/sessoes`).

---

## Assistente docente (híbrido)

O professor escreve do jeito dele. A pergunta passa por cinco etapas:

1. **Intenção.** O Gemini monta um plano com funções de uma lista fechada (`consultar_notas`, `consultar_frequencia`, `listar_alunos_em_risco`, `explicar_alerta`, `sugerir_intervencao`...). Sem Gemini, ou se ele falhar, as regras de palavras-chave fazem o mesmo papel.
2. **Entidades (RapidFuzz).** Os trechos que citam disciplina ou estudante são comparados com os registros reais do professor: `token_sort_ratio` para nomes inteiros, `token_set_ratio` com penalidade de cobertura para nomes parciais, siglas e códigos de matrícula. A pergunta inteira nunca é comparada. Nome ambíguo vira pergunta de volta com botões; nota baixa de semelhança não gera consulta.
3. **Consulta.** As funções leem só as turmas vinculadas ao usuário e usam o motor de regras R1 a R6 para decidir. O motor não mudou e continua sendo a única fonte de decisão.
4. **Redação.** O Gemini explica o resultado em linguagem natural. Antes de mostrar, o texto é conferido: código, nome ou suposição que não estão nos fatos fazem o texto ser descartado. Valores numéricos de indicadores ficam nos cartões e no texto das regras: se a redação livre os repetir, ela é substituída pelo texto das regras, evitando trocas de valores entre alunos ou indicadores. Números da pergunta não são tratados como fatos. Códigos de matrícula e de regras podem aparecer normalmente.
5. **Contexto.** A conversa guarda, no banco e só para aquele usuário, a disciplina, os estudantes da última resposta e a escolha pendente. Assim "e quais deles também têm muitas faltas?" filtra a lista anterior.

Exemplos que funcionam: "Mostre os alunos com baixo desempenho em estrututa de dados" → "E quais deles também têm muitas faltas?" → "Sugira intervenções para eles"; "Como está a Ana?" (pergunta qual das duas Anas); "notas de computação gráfica" (avisa que não há notas lançadas).

---

## Base de regras

| Regra | Condição → conclusão | Fator de certeza |
|---|---|---|
| R1 | média avaliável < mínimo → alerta de média | 0,7 |
| R2 | frequência avaliável < mínimo → alerta de frequência | 0,6 |
| R3 | R1 e R2 → prioridade alta de conferência | 0,9 |
| R4 | dado ausente ou inconsistente → indicador não avaliável | — |
| R5 | registro ou critério mudou → nova análise, anterior mantida | — |
| R6 | atividades vencidas sem entrega > limite → alerta de entregas | 0,5 |

O fator de certeza de uma conclusão é o menor fator do corpo da regra vezes o fator da regra. Os alertas independentes (média, frequência e entregas) se combinam em um grau de certeza da necessidade de acompanhamento, pela fórmula do MYCIN: `FC = FC1 + FC2 × (1 − FC1)`. Com poucos dados, o fato vale menos: 4 aulas registradas dão certeza 0,4 ao fato "frequência baixa", porque o grupo fixou 10 aulas como referência.
