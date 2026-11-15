# Ecossistema de Gestão Acadêmica com Assistente Docente

Projeto semestral integrado de **Desenvolvimento de Sistemas Web** e **Inteligência Artificial**, Engenharia de Computação, FAINOR, 2026.2, sob orientação do Prof. Msc. Wallas Fróes de Oliveira.

Equipe de Web: Daniel Soares Oliveira, Gustavo Mendes, Matheus Caires e Rauan Brandão.
Equipe de IA: os quatro de Web, com Camila Ramos, Guilherme Pereira e Samuel Cotinguiba.

A plataforma organiza turmas, notas, chamada, atividades com prazo e acesso por perfil. O assistente docente calcula média, frequência e situação das entregas, aplica uma base de regras por encadeamento para a frente e explica cada alerta com o dado, o critério e o fator de certeza usados. Quem decide é o professor: ele confere, revisa e registra a revisão. O assistente não altera notas.

> **Versão 0.2 (Bloco 3).** Dados fictícios. Os limites do perfil DEMO-v2 (média 6,0, frequência 80% e até 1 atividade vencida sem entrega) são didáticos e não correspondem aos critérios oficiais da FAINOR.

---

## Estrutura

```
├── api/index.py              ponto de entrada da API na Vercel (monta a API em /api)
├── backend/                  API em Python (FastAPI + SQLAlchemy)
│   ├── app/
│   │   ├── motor/            assistente: fatos, regras R1–R6, fatores de certeza, explicação
│   │   ├── servicos/         análises (R5), assistente, síntese Gemini, registros e entregas
│   │   ├── rotas/api.py      rotas REST
│   │   ├── models.py         entidades do banco
│   │   ├── seguranca.py      senha (PBKDF2), token assinado (HMAC-SHA256), vínculo
│   │   └── seed.py           dados fictícios
│   └── tests/                44 testes (pytest), incluindo T01 a T09 do Bloco 2
├── app/                      Flutter (web e Android), view / view model / repositório
│   ├── lib/data/             cliente HTTP, modelos, repositórios
│   ├── lib/ui/               login, professor (turmas, turma, matrícula, assistente), aluno
│   └── test/                 testes de widget e de modelos
├── scripts/                  build na Vercel e servidor local do build web
├── .github/workflows/ci.yml  CI: pytest (SQLite e PostgreSQL), flutter analyze, test e build
├── vercel.json               configuração do deploy
└── docker-compose.yml        PostgreSQL 16 para desenvolvimento
```

---

## Como rodar do zero

### Pré-requisitos

- Git, Python 3.11 ou mais novo e Flutter 3.22 ou mais novo (`flutter --version`)
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
| `prof.gabriel` | professor | Turmas de IA e de Web |
| `prof.helena` | professora | Só a turma de Banco de Dados (teste de bloqueio, T06) |
| `ana.lima` | aluna | A01: média 5,2 e 76% → R1, R2, R3 (certeza 0,88) |
| `bruno.reis` | aluno | A02: notas e frequência boas, 2 atividades vencidas sem entrega → R6 |
| `carla.dias` | aluna | A03: Avaliação 2 não lançada → R4 |

---

## Deploy na Vercel

O repositório já tem tudo configurado (`vercel.json`, `api/index.py` e `scripts/`). A Vercel instala o Flutter, compila o app e publica a API como função Python no mesmo domínio.

1. Entre em <https://vercel.com/new> com a conta do GitHub.
2. Importe o repositório `Ecossistema-Sala-de-Aula`. Não mude nenhuma configuração: o `vercel.json` já define instalação, build e pasta de saída.
3. Em **Environment Variables**, adicione `SECRET_KEY` com um texto aleatório longo (opcional, mas recomendado).
4. Clique em **Deploy**. O primeiro build leva alguns minutos, porque baixa o Flutter.

Variáveis opcionais:

| Variável | Para quê |
|---|---|
| `DATABASE_URL` | PostgreSQL persistente (Supabase ou Neon). Sem ela, o banco é um SQLite em `/tmp`, recriado com os dados fictícios quando a função esfria. |
| `GEMINI_API_KEY` | Liga a síntese em texto e a classificação de perguntas pelo Gemini. Sem ela, tudo funciona com as regras. |
| `DATA_REFERENCIA` | Fixa a data usada nos prazos (AAAA-MM-DD), útil para gravar uma demonstração. |

---

## Testes

```bash
cd backend && pytest -q          # 44 testes da API e do motor de regras
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
| `POST /turmas/{id}/assistente` | Pergunta ao assistente |
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
| `POST /conferencias/{id}/resposta` | Resposta do professor |
| `GET /aluno/desempenho` | Área do aluno |

Na Vercel e no servidor local, todas ficam sob `/api` (por exemplo, `/api/sessoes`).

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
