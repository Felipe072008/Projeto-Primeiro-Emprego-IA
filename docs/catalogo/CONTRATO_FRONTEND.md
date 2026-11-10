# Catálogo — contrato do backend (versão 2)

## Situação desta entrega

Somente backend. Nenhuma fonte externa tem sincronização verificada nesta etapa. O motor transacional e o comando de rotina estão implementados e testados com fixtures; os adaptadores de publicação reais permanecem bloqueados. A EV.G respondeu com uma página de manutenção, em vez do CSV. A rotina NÃO está instalada em um agendador online e NÃO atualiza com este computador desligado.

O acervo manual anterior continua com os valores e prazos originais. Não foi revalidado por esta entrega. Uma inscrição antiga sem estado registrado retorna `unknown`; não apresentar isso como matrícula aberta confirmada. Não atribuir a data de avaliação de uma fonte à verificação de um anúncio.

## Rotas e filtros

As rotas continuam autenticadas por sessão: `GET /api/jobs` e `GET /api/courses`. Erros de autenticação continuam HTTP 401. As consultas leem dados locais; não fazem coleta externa nem esperam a rede das fontes.

| Parâmetro | Aplicação |
|---|---|
| `all=1` | Explorar todas as áreas; mantém o recorte territorial e a validade |
| `q=texto` | Busca em título, empresa/instituição e resumo; até 120 caracteres |
| `type=livre` ou `type=tecnico` | Cursos; mantém o filtro existente |
| `free=1` | Cursos com acesso integral gratuito; não significa certificado gratuito |
| `certificate_free=1` | Cursos com `certificate_status=free`; pode combinar com `free=1` |

As áreas, a priorização por perfil, os contratos e a busca existentes são reaproveitados. Nenhuma adequação a requisitos é garantida pela recomendação.

## Envelope

| Campo | Tipo e significado |
|---|---|
| `schema_version` | inteiro `2` |
| `jobs` / `courses` | lista de itens exibíveis, já filtrados; nunca inclui links genéricos |
| `total` | número de itens após os filtros |
| `catalog_total` | número de itens válidos antes dos filtros |
| `catalog_status` | `available` ou `unavailable`, preservado por compatibilidade |
| `data_status` | `fresh`: há itens dentro do prazo de revisão; `stale`: não há itens válidos, mas há itens vencidos; `unavailable`: não há itens válidos nem vencidos estruturalmente válidos |
| `result_status` | `results`: resultados; `no_matches`: catálogo válido, sem correspondência aos filtros; `no_data`: sem catálogo válido |
| `stale_count` | registros publicados ocultos por validade/data; não contar como oportunidades ativas |
| `sources` | avaliação da integração e resultado da última execução de cada fonte |
| `external_links` | “Consulte também”; não entram em `total` nem em `catalog_total` |
| `interest`, `recognized_areas`, `contract_type`, `contract_types`, `personalized`, `location`, `notice` | campos existentes mantidos |

`fresh` descreve os prazos dos dados locais, não a saúde de todas as fontes. Uma fonte pode falhar hoje enquanto seus últimos dados ainda estão válidos. O frontend deve usar os estados de fonte para essa informação, sem ocultar a falha nem apresentar a tentativa como confirmação.

## Itens

Campos comuns: `id` estável, `source_id`, `source_item_id`, `source` (nome para exibição), `title`, `original_url` (link individual), `description` (resumo), `areas` (IDs existentes), `area_labels`, `requirements`, `status`, `checked_on` (dia ISO), `last_verified_at` (instante ISO com fuso ou `null` no acervo antigo), `review_by` (dia limite da revisão local), `expires_on` (prazo publicado ou `null`), `verification_method` (`manual`/`sync`), `availability_status` (`open`/`closed`/`unknown`), `closed_at` (instante ou `null`), `match`, `match_reason`.

Os resultados públicos só contêm `status=published`. Itens `closed` permanecem no armazenamento para histórico e não são listados. Vencimento oculta o item sem inventar que a fonte confirmou seu encerramento. Não há rota pública para histórico de itens nesta etapa.

Vagas mantêm `company`, `city=Curitiba`, `state=PR`, `entry_level=true`, `contract_type` (`aprendiz`, `estagio`, `clt`) e os campos de apresentação existentes (`contract`, `location`, `salary`, `schedule`, `benefits`, `access_note`). Novas importações exigem evidência de oferta individual aberta e requisitos; não basta o título parecer inicial. Campos opcionais não informados podem ser `null`/ausentes; mostrar “Não informado”, sem inventar valores.

Cursos mantêm `institution`, `duration`, `description`, `course_type`, `modality`, `free`, `price`, `certificate`, `certificate_cost`, `certificate_source`, `availability`, `access_note` e acrescentam:

| Campo | Estados / tipo |
|---|---|
| `enrollment_status` | `open`, `closed`, `unknown` |
| `access_status` | `free_full`, `paid`, `preview`, `trial`, `financial_aid`, `unknown` |
| `certificate_status` | `free`, `paid`, `unknown` |
| `duration_hours` | número positivo ou `null`, somente quando a fonte informar |

O motor só aceita novos cursos com inscrição `open` e acesso `free_full`. Aceita certificado pago ou desconhecido, que ficam fora de `certificate_free=1`. Nenhuma gratuidade é deduzida de “inscreva-se grátis”, prévia, teste ou auxílio financeiro. Evidências dos itens importados: `availability_evidence`, `access_evidence` e `certificate_source`; vagas também têm `requirements_evidence`.

## Fontes e tentativas

`classification`: `verified_sync` = sincronização verificada; `official_link` = somente link oficial; `pending` = pendente. Ver [FONTES.md](FONTES.md) e `data/fontes_catalogo.json` para motivos e evidências. **Não há `verified_sync` real nesta entrega.**

`sync_status`: `never` (sem tentativa), `success` (lote validado), `error` (rede/formato/validação), `partial` (resposta incompleta), `blocked` (integração pendente). O comando pode retornar `skipped` quando o ciclo já foi tentado; esse valor não substitui o último estado persistido.

Cada fonte retorna `id`, `name`, `kind`, `official_url` (ou `null`), `classification`, `reason`, `cost`, `permission`, `available_data`, `evidence_urls`, `assessed_on`, `suggested_schedule`, `schedule_timezone`, `sync_status`, `last_attempt_at`, `last_success_at`, `error_code`, `message`, `imported_count`.

- `last_attempt_at`: instante da execução, inclusive bloqueio/falha; **não é verificação**.
- `last_success_at`: último lote completo aceito; `null` até existir sucesso real.
- `imported_count`: quantidade do último lote aceito; não é contagem de itens atualmente válidos.
- `assessed_on`: dia em que a integração foi avaliada; não é disponibilidade das ofertas.

Todos os instantes persistidos usam `America/Sao_Paulo` com deslocamento no ISO 8601. Os dias não têm hora fictícia. O prazo de revisão pode vencer mesmo que a rotina falhe.

## Exemplos para integração

Os arquivos [exemplo-vagas.json](exemplo-vagas.json) e [exemplo-cursos.json](exemplo-cursos.json) são respostas reais do backend local, geradas sem perfil pessoal, após as tentativas desta entrega. Não são mocks nem confirmação atual de fontes externas. `generated_at` não foi adicionado ao envelope: a data dos exemplos está no relatório de execução.

Exemplo reduzido **ilustrativo** de falha mantendo a distinção de datas:

```json
{
  "schema_version": 2,
  "courses": [],
  "total": 0,
  "catalog_total": 0,
  "catalog_status": "unavailable",
  "data_status": "unavailable",
  "result_status": "no_data",
  "sources": [{
    "id": "evg",
    "classification": "pending",
    "sync_status": "error",
    "last_attempt_at": "2026-11-09T22:00:00-03:00",
    "last_success_at": null,
    "error_code": "unexpected_format"
  }],
  "external_links": []
}
```

O exemplo reduzido omite outros campos por brevidade; use os arquivos completos para integração. Para a interface: diferenciar ausência de correspondência aos filtros, indisponibilidade e dados vencidos; exibir condição do certificado; apresentar links externos à parte. Nada de HTML, CSS, JavaScript, celular ou layout foi alterado/testado visualmente nesta etapa.
