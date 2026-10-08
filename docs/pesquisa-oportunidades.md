# Áreas e oportunidades para o primeiro emprego em Curitiba

Consulta: **08/10/2026**. Esta é uma seleção editorial para iniciantes, não um ranking estatístico das profissões mais contratadas.

## 1. Áreas selecionadas antes da pesquisa de anúncios

1. Administração.
2. Finanças e Contabilidade.
3. Comércio e Atendimento.
4. Tecnologia da Informação.
5. Marketing e Comunicação.
6. Logística.
7. Recursos Humanos.
8. Indústria e Engenharia.
9. Saúde.
10. Educação e Pedagogia.

O perfil oferece 24 escolhas: Jovem Aprendiz geral e nas áreas administrativa, comercial e logística; dez opções de estágio; dez opções CLT com cargos auxiliares, de atendimento ou júnior. Saúde na entrada CLT significa recepção de clínica, sem atribuições clínicas. A opção industrial inclui estágio em engenharia e entrada CLT em produção. Educação inclui estágio em pedagogia e apoio escolar. Matrícula, formação, idade e experiência devem ser verificadas em cada anúncio: escolher uma área não garante elegibilidade.

### Evidências para a seleção

- [Prefeitura: mercado formal no primeiro semestre de 2026](https://www.curitiba.pr.gov.br/noticias/com-setor-de-servicos-em-alta-curitiba-gerou-16-mil-empregos-com-carteira-assinada-no-primeiro-semestre-segundo-caged/84311), publicada em 30/07/2026: serviços concentram o saldo de emprego; comércio, indústria e construção também aparecem. Fundamenta priorizar funções de apoio e atendimento.
- [Portal de Estágio do Imap](https://imap.curitiba.pr.gov.br/portal-de-estagio.html): relaciona administração, comunicação, finanças, educação, saúde e outras áreas de atuação na cidade.
- [Prefeitura: estágio para ensino médio e graduação](https://www.curitiba.pr.gov.br/noticias/quer-turbinar-seu-curriculo-prefeitura-de-curitiba-tem-100-vagas-de-estagio-para-estudantes-em-maio/82896), publicada em 06/05/2026: evidencia a diversidade de cursos elegíveis, como Administração, Contábeis, Comunicação, Psicologia, Engenharias, Enfermagem e tecnologia. A notícia é evidência das áreas, não foi republicada como vaga atual.
- [Programa Aprendiz de Curitiba](https://aprendiz.curitiba.pr.gov.br/): canal municipal dedicado ao ingresso por aprendizagem.
- [Emprega Curitiba](https://www.curitiba.pr.gov.br/noticias/encontre-no-emprega-curitiba-a-vaga-que-voce-esta-procurando/83693), publicada em 22/06/2026: apresenta o portal gratuito de oportunidades da cidade.

### Regras da seleção

- Priorizar aprendiz e estágio, e aceitar CLT somente em funções de entrada, com requisitos registrados fielmente.
- Usar anúncios individuais com Curitiba/PR explicitamente indicada, sem substituir Curitiba por cidades da região metropolitana.
- Não transformar banco de talentos, notícia antiga, concurso ou página de busca em vaga confirmada.
- Manter fonte, URL individual, data de consulta, prazo de revisão e eventuais restrições.
- Para cursos, exigir uma página identificável e informação da instituição sobre certificado, custo e condições de conclusão.

As escolhas estão em `static/occupations.json`; `scripts/build_career_options.py` reproduz a lista. Os anúncios e cursos estão em `data/jobs.json` e `data/courses.json`, com suas próprias fontes.

## 2. Pesquisa e seleção de vagas

Foram integrados **16 anúncios: 3 de aprendizagem, 11 de estágio e 2 CLT de entrada**. Os 16 endereços responderam HTTP 200 na conferência direta de 08/10/2026. Isso confirma acesso à página, não garante que o recrutador ainda tenha vagas no momento da candidatura. Descrições e requisitos também foram lidos; vagas com encerramento explícito foram descartadas.

### Portais pesquisados e resultado da análise

| Canal | Evidência e decisão |
| --- | --- |
| [Gupy — Curitiba](https://portal.gupy.io/job-search/term%3Dcuritiba) | Listagem com publicações de 07 e 08/10; integrados anúncios individuais de Magnum, Pashal, Autoglass, Sicredi, Fertipar, MRV, Pilar Hospital, Positivo e APG GOV. |
| [Central de Estágios do Paraná](https://www.ceestagios.pr.gov.br/cee/jsp/frm_busca_vagas.jsp) | Ofertas individuais com código, curso, cidade, bolsa e prazo; integradas seis ofertas. A leitura direta mostrou prorrogações que ainda não apareciam na cópia da busca. |
| [Destro](https://vagas.destromacro.com.br/vagas/auxiliar-de-logistica) | Anúncio próprio em Curitiba, contrato CLT e ausência explícita de exigência de experiência. |
| [GERAR](https://gerar.org.br/vagas-e-oportunidades/) | Vagas publicadas em 05 e 06/10 em diversas áreas; nesta consulta a página reunia anúncios e formulários, sem URL individual confirmada para cada vaga selecionada. Não importados. |
| [Cidade Júnior / Abler](https://vagascidadejunior.abler.com.br/) | Publicações em 05 e 06/10 e foco em aprendizagem. Alguns detalhes exigiram renderização que a consulta não recuperou de forma consistente; não renovados automaticamente. |
| [CIEE-PR](https://www.cieepr.org.br/canais-de-atendimento/faq/) | Há orientações e busca pública; oportunidades personalizadas e candidatura dependem de cadastro/login do estudante. Não houve acesso a conta pessoal. |
| [Aprendiz Curitiba](https://aprendiz.curitiba.pr.gov.br/) | Acesso do candidato via e-Cidadão; canal relevante para próximas revisões. |
| [Emprega Curitiba](https://www.curitiba.pr.gov.br/noticias/encontre-no-emprega-curitiba-a-vaga-que-voce-esta-procurando/83693) | Canal municipal pesquisado; a notícia não foi tratada como anúncio individual. |
| [Super Estágios — Marketing](https://www.superestagios.com.br/vagas/curitiba/marketing) | A página declara atualização diária. O botão consultado não forneceu endereço individual com todos os detalhes; não importado. |
| Indeed e BNE | O anúncio de marketing consultado no Indeed estava expirado; o anúncio BNE selecionado retornou 404 na conferência direta. Ambos foram descartados. |

Não foi confirmado que todos esses portais publicam **todos os dias**. As datas recentes e a declaração do Super Estágios mostram atividade frequente; o catálogo do PrimeiroEmprego IA continua com revisão manual, sem promessa de sincronização em tempo real.

### Cuidados específicos de interpretação

- Autoglass: o título e o programa descrito são de aprendizagem, mas o rótulo da plataforma aparece como efetivo. A divergência consta dos requisitos mostrados ao usuário.
- Experiência tratada como diferencial nas vagas de estágio não foi convertida em exigência obrigatória.
- Recepção e administração escolar não foram apresentadas como funções clínicas ou docência.
- Bolsa por hora foi mantida por hora; remuneração variável da Destro não foi transformada em salário fixo.
- Há vagas com prazo curto: CELEPAR até **09/10/2026** e COHAPAR até **12/10/2026**. O sistema as oculta depois da data, mesmo que a revisão geral ainda esteja válida.
- Os demais anúncios têm revisão, no máximo, em **22/10/2026**. Só renove a data após abrir a fonte novamente.

## 3. Cursos com certificado e cobertura

Foram selecionados **11 cursos online gratuitos**, com certificado sem cobrança segundo as respectivas instituições. Cada uma das 24 escolhas do perfil tem pelo menos um curso com correspondência direta à sua área, conferido por teste automatizado na data desta seleção. Cursos livres não equivalem a diploma técnico ou superior. Ofertas técnicas anteriores sem confirmação de turma/certificação nesta revisão foram substituídas por capacitações com condições verificáveis.

| Área | Exemplo de vaga integrada | Curso relacionado e certificado |
| --- | --- | --- |
| Administração | Aprendiz Magnum; estágio Fertipar; auxiliar APG | [Excel Básico — Fundação Bradesco, 15h](https://www.ev.org.br/cursos/microsoft-excel-2016-basico) |
| Finanças e Contabilidade | Estágios TECPAR e Sicredi | [Contabilidade Empresarial — Fundação Bradesco, 10h](https://www.ev.org.br/cursos/Contabilidade-Empresarial); Excel Básico como introdução |
| Comércio e Atendimento | Aprendiz Autoglass; atendimento APG | [Atendimento ao Público — Fundação Bradesco, 10h](https://www.ev.org.br/cursos/atendimento-ao-publico) |
| Tecnologia da Informação | Estágio COHAPAR | [Python Básico — Fundação Bradesco, 18h](https://www.ev.org.br/cursos/linguagem-de-programacao-python-basico) |
| Marketing e Comunicação | Estágio CELEPAR | [Marketing digital: primeiros passos — Sebrae, 9h](https://loja.sebrae.com.br/marketing-digital-para-sua-empresa-primeiros-passos-1-372000031607) |
| Logística | Aprendiz Pashal; estágio FUNSAÚDE; auxiliar Destro | [Estratégias de Logística — EV.G/Enap, 20h](https://www.escolavirtual.gov.br/curso/435/governoes) |
| Recursos Humanos | Aprendiz Pashal; estágio SEJU | [Gestão de Pessoas — EV.G/Enap, 20h](https://www.escolavirtual.gov.br/curso/1338/) |
| Indústria e Engenharia | Estágio MRV | [Geração, Transmissão e Distribuição de Energia — SENAI Online, 20h](https://www.sp.senai.br/curso/desvendando-a-geracao-transmissao-e-distribuicao-de-energia/109935) |
| Saúde | Estágio de farmácia hospitalar no Pilar | [Segurança do Paciente — EV.G/Enap/Anvisa, 100h](https://www.escolavirtual.gov.br/curso/236/governoes); Atendimento ao Público para recepção |
| Educação e Pedagogia | Estágios SEDEF e Positivo; apoio escolar APG | [Educação Inclusiva — Fundação Bradesco, 20h](https://www.ev.org.br/cursos/educacao-inclusiva); [IA para Educadores, 4h](https://www.ev.org.br/cursos/iaeduc) |

### Condições da certificação

- **Fundação Bradesco**: [orientação institucional](https://www.ev.org.br/) informa certificado após aprovação com 70% na avaliação final. Idade e prazo variam por curso e constam dos detalhes; Educação Inclusiva exige 18 anos, por exemplo.
- **EV.G/Enap**: as páginas individuais informam curso aberto, gratuito, com certificado e matrícula contínua. A emissão depende dos critérios de aprovação apresentados no ambiente do curso; não foi inventada uma nota mínima comum a todos.
- **Sebrae**: a [página original da oferta](https://sebrae.com.br/sites/PortalSebrae/cursosonline/marketing-digital-para-sua-empresa-primeiros-passos%2C5497125576a4e710VgnVCM100000d701210aRCRD) informa certificação digital gratuita e redireciona à nova oferta. Foi usada a carga atual de **9h**, em vez das 6h da versão antiga.
- **SENAI Online**: o [FAQ oficial](https://www.sp.senai.br/unidade/online/perguntas-frequentes) informa certificado gratuito, conclusão das atividades, aproveitamento mínimo de 50% e prazo de 21 dias. O usuário deve escolher a oferta **SENAI ONLINE**, não uma unidade presencial em São Paulo.

A seleção gratuita já cobre todas as áreas; não foi necessário incluir curso pago apenas para completar o catálogo. Revisão dos cursos até **06/01/2027**, ou antes se a instituição alterar as condições.

## Correspondência e limites

As opções novas possuem área e modalidade explícitas. Por exemplo, “CLT — Recepcionista de clínica” corresponde a Saúde, enquanto “Jovem Aprendiz — todas as áreas de entrada” aceita todas as áreas, mas só anúncios de aprendizagem. Cursos ignoram a modalidade contratual. A busca por todas as áreas permite explorar também outros contratos. Dados antigos do perfil não são alterados.

Cobertura de cursos é garantida na seleção de 08/10, não indefinidamente: registros vencidos são ocultados para evitar informação antiga. As dez áreas têm vaga nesta seleção, mas não há garantia de anúncio ativo para cada combinação área/contrato. Quando não houver, o site informa ausência de resultados e permite explorar as demais oportunidades.
