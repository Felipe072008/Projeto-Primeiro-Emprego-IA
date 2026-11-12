# Fontes do catálogo

## Atualização em 12/11/2026

**Jooble Brasil habilitada para vagas.** A [página oficial da API](https://br.jooble.org/api/about) descreve o uso das respostas em portais próprios. A chave fornecida pelo responsável foi testada na API brasileira. O adaptador consulta três termos para Curitiba e publica somente registros com ID/link individual, requisitos e área reconhecida. A consulta cobre a primeira página por termo: não representa todas as vagas da fonte e não encerra itens por ausência. A disponibilidade é a observada na API, sem garantia de candidatura ainda aberta na empresa.

O recebimento real no PythonAnywhere foi confirmado. Os cursos não usam a Jooble e continuam sem adaptador automático. A EV.G foi excluída das fontes ativas e seus três cursos foram removidos, por solicitação do responsável; a avaliação abaixo permanece apenas como histórico.

## Avaliação histórica de 09/11/2026 (Brasília)

Esta é a avaliação técnica desta integração, não uma autorização jurídica geral. Acesso público, `robots.txt` e preço zero de um curso não equivalem a licença para republicar um catálogo. Nenhum contrato, conta ou serviço pago foi criado. Não houve coleta em massa de páginas de anúncios, contorno de login/CAPTCHA/bloqueio nem cópia de descrições completas.

O registro usado pelas rotas está em `data/fontes_catalogo.json`, com domínio/link, custo conhecido, documentação, permissão, dados disponíveis e motivo por fonte.

| Fonte | Classificação | Evidência e limite encontrado |
|---|---|---|
| EV.G / Enap | **Pendente** | [Catálogo oficial](https://www.escolavirtual.gov.br/catalogo) oferece [CSV](https://www.escolavirtual.gov.br/catalogo/exportar/csv). Primeiro download retornou HTML de manutenção. [Enap](https://enap.gov.br/acesso-a-informacao/dados-abertos/) declara reúso de bases publicadas no Portal Brasileiro de Dados Abertos; falta confirmar o vínculo da licença com este CSV, seu esquema, completude e estados por oferta. Não usar base de alunos como catálogo. |
| Emprega Curitiba | **Somente link oficial** | [Prefeitura identifica o portal gratuito](https://www.curitiba.pr.gov.br/noticias/confira-as-vagas-de-trabalho-disponiveis-no-site-emprega-curitiba/85486). Consulta automatizada do portal recebeu 403. Não foi confirmado API/feed autorizado de redistribuição; não insistir em contornar o bloqueio. |
| CIEE, prioridade PR | **Somente link oficial** | [CIEE/PR](https://www.cieepr.org.br/) aponta para [busca oficial](https://autoweb.cieepr.org.br/Estudante/vagas-externo). Não foi confirmada API/feed e autorização de republicação. Acesso público e candidatura cadastrada são coisas distintas. CIEE nacional não foi usado como substituto de vagas do Paraná. |
| InfoJobs Brasil | **Somente link oficial** | [Aviso legal](https://www.infojobs.com.br/legal/aviso-legal-para-candidatos__15727.aspx), seção de propriedade intelectual, restringe republicação em outros sites sem autorização. Não houve obtenção de licença/API para essa finalidade. |
| Catho | **Somente link oficial** | [Termos de API](https://assets.catho.com.br/consents-prod/terms/termos-de-uso-api-publica-v1.pdf) descrevem integração de recrutadores/anúncio de vagas; não comprovam leitura livre de todo o catálogo ou licença de agregação. Não confundir anúncio gratuito com API gratuita de redistribuição. |
| Indeed | **Somente link oficial** | [Termos](https://br.indeed.com/legal) impõem condições a APIs, armazenamento e redistribuição. Não foi confirmado acesso permitido para este uso. |
| Meu Emprego | **Removido da configuração em 09/11/2026** | Domínio não confirmado; registro histórico da avaliação anterior. Não é retornado pelas rotas nem pelo comando. |
| Prefeitura / IMAP — estágios | **Pendente, piloto separado** | [Conjunto oficial](https://dadosabertos.curitiba.pr.gov.br/conjuntodado/detalhe?chave=26200d9a-eff9-434c-8858-36b8eb6ebea6) e [regras de reúso](https://dadosabertos.curitiba.pr.gov.br/informacoes/regrasutilizacao/5). [Espelho oficial vinculado](https://dadosabertos.c3sl.ufpr.br/curitiba/IMAPEstagios/) entregou documentação e metadados, não vagas. O PDF, apesar de publicado sob data de 2024, descreve serviço de 2015, com órgão/área/turno/escolaridade/endereço, sem ID ou link individual. Teste HTTPS falhou por certificado incompatível. Não foram enviadas credenciais nem desativada validação TLS. |
| Aprenda Mais / MEC | **Somente link oficial** | [Portal](https://aprendamais.mec.gov.br/) e [ajuda](https://aprendamais.mec.gov.br/mod/page/view.php?id=134111). Cursos e turmas públicos não comprovam API/feed autorizado; matrícula, prazo e certificação precisam de conferência por oferta. Sem API paga. |
| Sebrae | **Somente link oficial** | [Catálogo oficial](https://loja.sebrae.com.br/cursos/cursos-online) contém ofertas e preços; [exemplo de página](https://loja.sebrae.com.br/gest-o-financeira-1-372000026927). Não foi confirmada permissão/API de redistribuição. Não extrapolar gratuidade ou certificado de um curso para todos. |
| Prime Cursos | **Somente link oficial** | [Portal](https://www.primecursos.com.br/) distingue conteúdo gratuito de certificado pago; [contrato](https://www.primecursos.com.br/contrato-de-prestacao-de-servicos/) não comprova feed autorizado de agregação. A futura integração pode listar conteúdo integral gratuito com certificado pago, devidamente marcado. |
| Coursera | **Somente link oficial** | [Termos](https://www.coursera.org/about/terms) limitam a licença de uso; não foi confirmada autorização de redistribuição. Cadastro, prévia, teste temporário e auxílio financeiro não serão interpretados como conteúdo integral gratuito. |

## Antes de ativar uma fonte

Confirmar acesso e licença para a finalidade, obter uma resposta real oficial, documentar esquema/paginação e evidência de completude, ID/link individual, abertura e requisitos/condições. Só então adicionar o adaptador e mudar `classification` para `verified_sync`. Alterar apenas o JSON não habilita uma importação: o registro `ADAPTERS` também exige um adaptador implementado e revisado.

Para a Prefeitura, o reúso exige citar órgão/fonte, Portal de Dados Abertos, instante de acesso e o aviso de que o portal/órgão não garantem autenticidade, qualidade, integridade e atualidade após disponibilização para uso secundário. Isso deve integrar o contrato de atribuição do adaptador antes de ativação. A licença de dados abertos não se estende automaticamente ao portal Emprega Curitiba.

## O que efetivamente retornou dados

- EV.G: HTML de manutenção; **zero cursos importados**.
- Espelho de estágios: PDF de documentação e XML de metadados; **zero vagas importadas**.
- Serviço de estágios: falha de certificado HTTPS; sem consulta autenticada.
- Demais fontes: consulta documental/páginas oficiais somente; **zero registros importados**.
- Motor de importação: sucessos comprovados exclusivamente em fixtures sintéticas de teste, não em fontes reais.
