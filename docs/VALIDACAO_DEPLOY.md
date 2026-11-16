# Validação para deploy — 16/11/2026

As verificações locais terminaram sem bloqueios conhecidos para publicar na Vercel. O banco PostgreSQL e a `SECRET_KEY` no destino foram confirmados pelo responsável pelo projeto; os valores não foram acessados nesta revisão.

## Resultados

| Verificação | Resultado |
|---|---|
| API em SQLite | 90 testes passaram; 1 teste exclusivo de PostgreSQL foi ignorado |
| API em PostgreSQL 14.24 temporário | 91 testes passaram |
| Inicialização concorrente | 3 processos iniciaram juntos em um schema vazio e autenticaram com sucesso |
| Testes Flutter 3.50.0 / Dart 3.14.0 | 11 testes passaram |
| `flutter analyze --no-fatal-infos` | Código de saída 0; sem erros ou warnings; 20 informações de APIs descontinuadas |
| `flutter build web --release --no-web-resources-cdn` | Build de produção gerado com sucesso |
| Navegador Chrome, build compilado e API local | Login do professor e carregamento das 4 turmas; login da aluna e carregamento de notas, frequência, atividades e pedidos; respostas da API verificadas com status 200; sem exceções JavaScript detectadas |
| Configuração Vercel | Validada contra o esquema oficial; contrato do caminho público `/api` coberto por teste |
| Dependências Python e diff | `pip check` e `git diff --check` passaram |

O código e os testes Flutter foram executados em uma cópia temporária, conferida como idêntica às pastas `app/lib` e `app/test` do repositório. Arquivos gerados pelo SDK não foram adicionados ao projeto. O CI continua configurado para PostgreSQL 16; a execução local usou a versão 14.24 disponível na máquina.

## Correções adicionais de deploy

- Substituído o rewrite interno da API por uma transformação `request.path`. Em Vercel Services, o rewrite escolhe a rota, mas não remove o prefixo observado pelo código. Agora `/api/sessoes` chega ao FastAPI como `/sessoes`.
- A inicialização do FastAPI passou a chamar `garantir_banco()`, reaproveitando a trava PostgreSQL existente. Antes da correção, 2 das 3 instâncias simuladas falharam tentando criar a mesma tabela em um banco vazio. O teste de regressão usa um schema temporário exclusivo e o remove ao terminar.
- O download do Flutter no build usa checkout seletivo de `bin` e `packages`, evitando baixar o código do engine que não é necessário para compilar esta aplicação.

As correções funcionais anteriores também estão incluídas: invalidação das análises por atividade nova ou vencimento, contagem de R6, rejeição de textos vazios, tratamento de estudante inexistente e fallback da redação numérica do Gemini para o texto das regras.

## Limites e publicação

As mensagens de APIs Flutter descontinuadas são informativas e não impediram os testes nem a compilação; a migração dessas APIs ficou fora desta correção pontual. As chamadas ao Gemini foram simuladas nos testes: não houve chamada ao serviço real nem consumo de sua chave.

Esta revisão valida o código local e o build web, não uma publicação já executada. O roteamento da Vercel foi conferido pelo contrato da configuração, pelo esquema e pela documentação, sem executar o runtime da Vercel. Depois de publicar, ainda cabe conferir `/api/`, login e as duas áreas no endereço publicado. A integração real com o PostgreSQL remoto e os logs do deploy só poderão ser confirmados nessa etapa.

Não há garantia de ausência total de bugs. O resultado é a aprovação das verificações descritas acima. Nenhum commit, push ou deploy foi executado nesta revisão.

## Referências

- [Roteamento de Vercel Services](https://vercel.com/docs/services/routing)
- [Transformação de caminho dentro de um serviço](https://vercel.com/docs/project-configuration/vercel-json#request-path-transform-in-a-service)
- [Esquema oficial de vercel.json](https://openapi.vercel.sh/vercel.json)
