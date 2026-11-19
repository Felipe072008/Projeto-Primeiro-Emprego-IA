# Catálogo do editor do site

Projeto: `C:\Users\felip\Documents\primeiro-emprego-ia`. O catálogo executável fica em `conteudo_editavel.py` e rejeita chaves desconhecidas.

| Página | Textos editáveis | Estrutura |
|---|---|---|
| Tela inicial/login | Chamada principal | Apresentação pode ser ocultada; login/cadastro são travados |
| Visão geral | Título, introdução e chamada do currículo | Introdução, atalhos e orientação podem ser ocultados/reordenados |
| Meu perfil | Título e introdução | Cabeçalho e campos profissionais travados; explicação do progresso pode ser ocultada |
| Vagas | Título e introdução | Cabeçalho e catálogo/filtros travados |
| Cursos | Título | Cabeçalho e catálogo/filtros travados |
| Meu currículo | Título e introdução | Cabeçalho, envio/criação e arquivos salvos travados |
| Minha conta | Título e introdução | Cabeçalho, segurança, formulários e privacidade travados |

Cada página tem um slot ao final para blocos de Texto, Aviso, Botão com link e Perguntas frequentes. São no máximo 30 blocos no site inteiro, com ordem e visibilidade próprias. Slots não se movem. Uma seção travada conserva sua posição original, inclusive nas requisições forjadas. Seções não travadas só podem trocar de posição dentro do mesmo grupo e sem deslocar as travadas.

Textos são simples (sem HTML e sem formatação Markdown nesta versão), até 120 caracteres nos títulos e 500 nas introduções. Quebras de linha são preservadas. Restaurar um texto recupera o padrão listado no catálogo.

Tema: primária (`--blue`), secundária (`--blue-deep`), fundo (`--cream`), texto (`--ink`) e destaque (`--orange`). Cores devem usar `#RRGGBB`. O tema só substitui as cores publicadas que diferem dos padrões; o visual original permanece como fallback. Contraste texto/fundo abaixo de 4,5:1 exige confirmação adicional na publicação.

Fontes: DM Sans e Plus Jakarta Sans, já distribuídas localmente com licença SIL OFL em `static/fonts/`. Títulos e corpo têm escolhas independentes. Logo PNG/JPEG/WEBP até 1 MB, validado e recodificado como PNG sem metadados, até 4 milhões de pixels; texto alternativo obrigatório até 160 caracteres.

Não são editáveis: Termos, Privacidade, Cookies, aceites, navegação, formulários, mensagens de validação, dados dinâmicos e o próprio painel. As prévias não consultam usuários, currículos ou ofertas reais; exibem apenas exemplos fixos identificados.

Direção da interface: estender o painel existente, com barra de ações, tema/estrutura à esquerda e prévia à direita; no celular os controles precedem a prévia. Reutilizar botões, fontes e cores locais. A ação principal é salvar rascunho; publicar é uma decisão explícita com resumo. Não há alteração visual fora desse escopo.
