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

- As vagas de `data/jobs.json` são oportunidades individuais consultadas em Curitiba, PR. Os cursos de `data/courses.json` incluem capacitações online gratuitas e cursos técnicos do SENAI Paraná. A página de cursos técnicos pode ser apenas um catálogo: turma, unidade, inscrição e valor precisam de confirmação na instituição.
- O campo **Área profissional desejada** em Meu perfil orienta as recomendações. As páginas exibem correspondência direta, áreas correlatas e a opção de explorar todas as áreas. A busca usa título, instituição/empresa e resumo.
- Cada cartão abre detalhes dentro do site e leva à página original. Ler as oportunidades consultadas não exigiu login; candidatar-se na Abler ou BNE pode exigir cadastro. Estudar pela Escola Virtual exige cadastro gratuito.
- Anúncios com prazo de revisão vencido ficam ocultos. O prazo inicial das vagas é **09/10/2026**. Depois disso, revise cada URL na fonte, corrija dados alterados, remova vagas encerradas, atualize `checked_on` e `review_by` e publique o catálogo revisto. Para ver o que precisa de revisão: `.\.venv\Scripts\python.exe scripts\review_catalog.py`. Cursos têm revisão inicial até **24/12/2026**. O catálogo é manual; o site não afirma consultar todas as fontes em tempo real.
- Ao adicionar uma oportunidade, use URL HTTPS individual, cidade Curitiba, estado PR, fonte, requisitos, resumo, áreas e datas de consulta/revisão. Confira a oferta na fonte antes de marcar `status` como `published`. Não extrapole requisitos nem condições.

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
