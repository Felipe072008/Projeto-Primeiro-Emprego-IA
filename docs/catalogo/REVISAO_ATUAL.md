# Revisão do catálogo — 2026-11-09

Repositório confirmado visualmente no VS Code: `C:\Users\felip\Documents\primeiro-emprego-ia`. Abas visíveis: README.md, analise_curriculo.py, test_aplicacao.py e test_layout_curriculo.py. Nenhuma alteração de frontend foi feita por esta revisão; outro chat trabalhou simultaneamente na interface e acrescentou fontes anteriores ao registro, que foram preservadas.

## Vagas recuperadas

Os 17 anúncios anteriores foram consultados diretamente, com resposta HTTP 200 em todos. HTTP 200 sozinho não foi usado como prova de abertura: conferidos texto de encerramento, prazo, candidatura, cidade, contrato e requisitos. Dados estruturados oficiais de JobPosting foram usados quando presentes. O resultado direto prevaleceu sobre páginas antigas do índice de busca.

**8 antigas abertas + 5 novas abertas = 13 publicadas**: 3 de aprendizagem, 7 de estágio e 3 CLT. As outras 9 antigas continuam no acervo, ocultas: 8 encerradas e 1 indisponível. O arquivo anterior completo (17 vagas e cursos) foi preservado em `data/historico/catalogo-antes-revisao-2026-11-09.json`.

Os campos `checked_on` e `last_verified_at` só foram renovados para as ofertas abertas conferidas. As encerradas/indisponíveis mantiveram o dia de verificação e o prazo de revisão anteriores. `last_review_attempt_at` registra a nova consulta e `closed_at` o momento em que o encerramento foi observado, sem inventar quando a empresa encerrou de fato.

`review_by` segue a política de revisão diária (dia seguinte à conferência) e não é prazo de inscrição. `expires_on` vem da fonte quando informado; não foram presumidos prazos para Destro, Bellinati ou a nova oferta de Comunicação Interna do Pilar. A revisão manual não elimina a necessidade de novas conferências ao vencer esse prazo.

| Registro oficial | Resultado | Prazo informado na fonte | Evidência resumida |
|---|---|---|---|
| [magnum-aprendiz](https://magnumtires.gupy.io/job/eyJqb2JJZCI6MTI2MTE1NjksInNvdXJjZSI6Imd1cHlfcG9ydGFsIn0=?jobBoardSource=gupy_portal) | Aberta, mantida | 2026-11-13 | Anúncio individual de Curitiba com candidatura disponível, sem aviso de encerramento. Prazo informado nos dados estruturados da fonte: 2026-11-13. |
| [pashal-aprendiz](https://pashal.gupy.io/jobs/12165252?jobBoardSource=gupy_public_page) | Aberta, mantida | 2027-02-01 | Anúncio individual de Curitiba com candidatura disponível, sem aviso de encerramento. Prazo informado nos dados estruturados da fonte: 2027-02-01. |
| [autoglass-aprendiz](https://autoglassjovemaprendiz.gupy.io/jobs/12693816?jobBoardSource=gupy_public_page) | Aberta, mantida | 2026-11-30 | Anúncio individual de Curitiba com candidatura disponível, sem aviso de encerramento. Prazo informado nos dados estruturados da fonte: 2026-11-30. |
| [cee-178406](https://www.ceestagios.pr.gov.br/cee/jsp/frm_cons_detalhe_vaga.jsp?codoferta=178406) | Indisponível, oculta | 2026-10-28 | A consulta direta retornou “Vaga não encontrada”; ocultada sem presumir prorrogação nem data de encerramento. |
| [cee-178626](https://www.ceestagios.pr.gov.br/cee/jsp/frm_cons_detalhe_vaga.jsp?codoferta=178626) | Aberta, mantida | 2026-11-29 | Período da oferta: 30/10/2026 a 29/11/2026; Curitiba/PR; formulário de candidatura disponível. |
| [cee-177903](https://www.ceestagios.pr.gov.br/cee/jsp/frm_cons_detalhe_vaga.jsp?codoferta=177903) | Encerrada, oculta | 2026-10-23 | Oferta encerrada: prazo oficial 2026-10-23. |
| [cee-178755](https://www.ceestagios.pr.gov.br/cee/jsp/frm_cons_detalhe_vaga.jsp?codoferta=178755) | Encerrada, oculta | 2026-10-30 | Oferta encerrada: prazo oficial 2026-10-30. |
| [cee-178426](https://www.ceestagios.pr.gov.br/cee/jsp/frm_cons_detalhe_vaga.jsp?codoferta=178426) | Encerrada, oculta | 2026-10-09 | Oferta encerrada: prazo oficial 2026-10-09. |
| [cee-177882](https://www.ceestagios.pr.gov.br/cee/jsp/frm_cons_detalhe_vaga.jsp?codoferta=177882) | Encerrada, oculta | 2026-10-30 | Oferta encerrada: prazo oficial 2026-10-30. |
| [sicredi-servicos](https://sicredi.gupy.io/jobs/12382343?jobBoardSource=gupy_public_page) | Aberta, mantida | 2026-11-19 | Anúncio individual de Curitiba com candidatura disponível, sem aviso de encerramento. Prazo informado nos dados estruturados da fonte: 2026-11-19. |
| [fertipar-administrativo](https://grupofertipar.gupy.io/jobs/12588807?jobBoardSource=gupy_public_page) | Encerrada, oculta | 2026-10-26 | Oferta encerrada: aviso de candidaturas encerradas e prazo oficial 2026-10-26. |
| [mrv-engenharia](https://programadeestagiomrveco.gupy.io/job/eyJqb2JJZCI6MTE5ODM4MTYsInNvdXJjZSI6Imd1cHlfcG9ydGFsIn0=?jobBoardSource=gupy_portal) | Encerrada, oculta | 2026-09-30 | Oferta encerrada: aviso de candidaturas encerradas e prazo oficial 2026-09-30. |
| [pilar-farmacia](https://pilarhospital.gupy.io/jobs/9172371?jobBoardSource=gupy_portal) | Encerrada, oculta | 2026-10-30 | Oferta encerrada: aviso de candidaturas encerradas e prazo oficial 2026-10-30. |
| [positivo-pedagogia](https://positivo.gupy.io/jobs/11576904?jobBoardSource=gupy_public_page) | Encerrada, oculta | 2026-09-10 | Oferta encerrada: aviso de candidaturas encerradas e prazo oficial 2026-09-10. |
| [destro-logistica](https://vagas.destromacro.com.br/vagas/auxiliar-de-logistica) | Aberta, mantida | Não informado | Página individual em Curitiba/PR, contrato CLT e recebimento de currículos disponível; sem experiência exigida. |
| [apg-administrativo](https://apg-gov.gupy.io/jobs/10670487?jobBoardSource=gupy_public_page) | Aberta, mantida | 2026-11-30 | Anúncio individual de Curitiba com candidatura disponível, sem aviso de encerramento. Prazo informado nos dados estruturados da fonte: 2026-11-30. |
| [bp-infra-estagio](https://bellinatiperez.gupy.io/jobs/12467350) | Aberta, mantida | Não informado | Anúncio individual de Curitiba com candidatura disponível, sem aviso de encerramento. |
| [destro-ajudante-motorista](https://vagas.destromacro.com.br/vagas/ajudante-de-motorista) | Nova, aberta | Não informado | Página individual de Curitiba, contrato e requisitos de entrada conferidos; recebimento de currículos disponível. |
| [sicredi-infra-12824570](https://sicredi.gupy.io/jobs/12824570) | Nova, aberta | 2026-12-11 | Página individual de estágio em Curitiba com candidatura disponível e requisitos de estudante conferidos. |
| [unicred-comercial-12842069](https://unicredbr.gupy.io/jobs/12842069) | Nova, aberta | 2027-01-04 | Página individual de estágio em Curitiba com candidatura disponível e requisitos de estudante conferidos. |
| [pilar-comunicacao-12788794](https://pilarhospital.gupy.io/jobs/12788794) | Nova, aberta | Não informado | Página individual de estágio em Curitiba com candidatura disponível e requisitos de estudante conferidos. |
| [plaenge-produto-12770857](https://grupoplaenge.gupy.io/jobs/12770857) | Nova, aberta | 2026-12-07 | Página individual de estágio em Curitiba com candidatura disponível e requisitos de estudante conferidos. |

## Fontes e cursos

`meu_emprego` foi removido de `data/fontes_catalogo.json`. As fontes anteriores e as novas integrações pendentes/links foram preservadas. Acrescentado o [Programa Aprendiz da Prefeitura](https://aprendiz.curitiba.pr.gov.br/) como link oficial separado das ofertas; o portal exige acesso pelo e-Cidadão e não representa vaga individual verificada.

O perfil sintético de Administração foi criado, salvo pela API de perfil e consultado por `GET /api/courses` sem `all=1`: HTTP 200, `recognized_areas=["Administração"]`, `personalized=true` e **3 cursos compatíveis** (Atendimento ao Público, Estratégias de Logística na Administração Pública e Excel Básico). Após salvar Tecnologia, a mesma sessão retornou **2 cursos de Tecnologia**, sem manter Administração. Evidência em `teste-administracao.json`. Não foi encontrada falha de reconhecimento no backend. Esta verificação confirma a associação de áreas; não revalida matrícula/conteúdo dos cursos externos.

Os testes antigos de outubro passaram a usar o acervo arquivado. Os novos testes exercitam o catálogo atual, a exclusão das vagas fechadas, os contratos, as evidências, a preservação das fontes e a troca de área pelas rotas reais em banco temporário.

## PythonAnywhere e automação

Conta informada pelo usuário: `felipecorreia`. O usuário confirmou que a aba Tasks está vazia. Não houve acesso autenticado ao painel por ferramentas: o host de navegador estava indisponível e nenhuma credencial de API estava configurada no ambiente.

**Agendamento não configurado; automação não comprovada.** Não há log de execução agendada nem lote real importado de fonte autorizada. Os anúncios acima resultam de revisão editorial manual. Nenhuma API de agregação foi habilitada apenas porque uma página pública respondeu.

Os critérios para considerar automação ativa continuam sendo: fonte e uso autorizados, adaptador validado com lote real, tarefa instalada na conta correta, log de execução realmente disparada pelo agendador e sucesso persistido no mesmo armazenamento lido pelo site. Um teste manual com `--due` não prova execução agendada.

A [documentação atual do PythonAnywhere](https://help.pythonanywhere.com/pages/ScheduledTasks/) informa que tarefas agendadas dependem do plano e da data de criação da conta. Contas gratuitas elegíveis permitem uma tarefa diária; para este caso, uma única execução diária de `scripts/atualizar_catalogo.py --due` pode selecionar o ciclo diário de vagas e o semanal de cursos. Horário do painel e caminhos/ambiente remoto ainda precisam ser confirmados. Não foi contratado plano, feito upload, alterado o site hospedado nem criado agendamento nesta revisão.

## Verificação e arquivos

Testes de backend executados em bancos/arquivos temporários; nenhum perfil real alterado. O relatório final do chat informa a contagem final e o resultado de `git diff --check`.

Arquivos desta revisão: `data/jobs.json`, `data/fontes_catalogo.json`, `data/historico/catalogo-antes-revisao-2026-11-09.json`, `tests/test_aplicacao.py`, `tests/test_catalogo_revisado.py`, relatório JSON e documentos/exemplos em `docs/catalogo/`, além dos apontamentos de documentação. Alterações simultâneas de CSS/JavaScript/testes de frontend pertencem ao outro chat e não foram sobrescritas.

### Resultado final dos comandos

- 52 testes Python: aprovados. As rotas de página/recursos também responderam HTTP 200 no cliente Flask.
- `GET /api/jobs?all=1`: HTTP 200, `total=13`, `result_status=results`.
- Perfil Administração: HTTP 200 e 3 cursos; após salvar Tecnologia, HTTP 200 e 2 cursos dessa área.
- Nova tentativa real do CSV EV.G em 09/11/2026 às 23h52 de Brasília: HTML no lugar de CSV, `unexpected_format`, zero cursos importados, `last_success_at=null`. Falha preservou os dados e não foi tratada como confirmação.
- `git diff --check`: sem erros. Sem commit e sem deploy desta revisão.

Evidência estruturada em `verificacao-revisao.json`. O estado do PythonAnywhere deriva da confirmação do usuário sobre a lista vazia, não de leitura autenticada do painel por ferramentas.
