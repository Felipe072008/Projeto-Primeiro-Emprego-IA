# PrimeiroEmprego IA

Plataforma Flask para organizar perfil e currículo, consultar oportunidades em Curitiba e explorar cursos. O perfil começa vazio. Vagas e cursos têm páginas individuais de origem; os resumos são editados localmente e exibem a data da consulta.

## Executar localmente

No PowerShell, nesta pasta:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Abra <http://127.0.0.1:5000>. A aplicação usa SQLite e cria o banco localmente. Para testes separados, defina `FIRST_JOB_DATABASE` e `FIRST_JOB_UPLOAD_DIR` antes de iniciar. O site não exige chave de API paga.

## Vagas e cursos

- Seleção conferida em **08/10/2026**: 16 anúncios individuais de Curitiba/PR (3 de aprendizagem, 11 de estágio e 2 CLT de entrada) e 11 cursos online gratuitos com certificado, cobrindo as dez áreas do perfil. Consulte a [pesquisa, fontes e matriz de cobertura](docs/pesquisa-oportunidades.md).
- **Área profissional desejada** oferece 24 escolhas focadas em início de carreira. `scripts/build_career_options.py` gera `static/occupations.json`. As vagas consideram área e tipo de contrato; cursos consideram a área, independentemente do contrato. Perfis antigos em texto livre continuam reconhecidos pelos termos conhecidos, sem sobrescrever o que o usuário informou.
- As páginas exibem correspondência direta, áreas correlatas e a opção de explorar todas as áreas e contratos. A busca usa título, instituição/empresa e resumo. Selecionar uma área não garante que haja vaga ativa para cada contrato nem que o candidato preencha os requisitos.
- Cada cartão abre detalhes internos e link à fonte. Cursos mostram as condições e o custo do certificado. Candidaturas na Gupy e na Central de Estágios exigem cadastro na fonte; os resumos não exigem login nessas plataformas. As instituições de ensino também pedem cadastro para matrícula.
- Vagas ficam ocultas após `expires_on` ou `review_by`, o que ocorrer primeiro. A revisão geral desta seleção vence em **22/10/2026**, mas há anúncios com prazo anterior (por exemplo, CELEPAR em **09/10/2026**). Cursos têm revisão até **06/01/2027**. Antes de renovar datas, abra a fonte e confira disponibilidade, requisitos e condições. O catálogo é manual: pesquisar portais atualizados diariamente não equivale a sincronização automática diária.
- Para ver anúncios vencidos ou próximos de revisão: `.\.venv\Scripts\python.exe scripts\review_catalog.py`. Registros de vagas exigem `entry_level: true` e `contract_type` (`aprendiz`, `estagio` ou `clt`), além de URL HTTPS individual, Curitiba/PR, fonte, resumo, requisitos, áreas e datas. Cursos exigem informação de `certificate`, com `certificate_source` e `certificate_cost` documentando a certificação. Não publique bancos de talentos como vagas abertas.

## Currículo e análise gratuita

O envio aceita apenas PDF real, até 8 MB e 20 páginas. PDFs digitalizados podem ser guardados, mas precisam de OCR para análise. O gerador PDF inclui as informações que a pessoa revisou no formulário, com localização e contato editáveis. A revisão automática da estrutura funciona sem serviço externo.

A análise contextual com IA usa [Ollama para Windows](https://docs.ollama.com/windows), instalado **no computador que executa o Flask**. Você escolheu instalá-lo depois. Quando quiser ativar:

1. Instale Ollama pela [página oficial](https://ollama.com/download/windows). A instalação do Windows ocupa pelo menos 4 GB, além do espaço do modelo. Em computador com aproximadamente 8 GB de RAM, o projeto está configurado para o modelo leve `qwen3:1.7b`.
2. No PowerShell, execute `ollama pull qwen3:1.7b`.
3. Confirme com `ollama list` e mantenha o serviço Ollama iniciado. Reinicie o site, se necessário.
4. Acesse **Meu currículo → Analisar currículo**. O relatório indica quando a análise contextual foi feita por IA local. Se o modelo estiver indisponível ou falhar, ele informa isso e mostra apenas a revisão automática.

O texto extraído do PDF é enviado apenas ao serviço Ollama local em `127.0.0.1:11434` para a análise contextual. Não há envio do currículo a uma API paga por este código. O modelo pode errar; sugestões de redação devem ser conferidas antes de uso.

## Verificações

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static\app.js
```

## Antes de publicar

HTTPS, navegação do histórico, conta, política de privacidade e demais itens que você adiou continuam pendentes. Configure `SECRET_KEY`, servidor de produção e proteção adequada dos dados antes de expor o site publicamente.
