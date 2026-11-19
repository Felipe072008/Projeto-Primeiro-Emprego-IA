"""Catálogo fechado e validação do editor; nunca aceita código do administrador."""
import copy
import hashlib
import json
import re
from urllib.parse import urlsplit

PAGES = {'login':'Tela inicial/login', 'dashboard':'Visão geral', 'profile':'Meu perfil',
         'jobs':'Vagas', 'courses':'Cursos', 'resume':'Meu currículo', 'account':'Minha conta'}
FONTS = ('DM Sans', 'Plus Jakarta Sans')
COLORS = {'primary':'#123dcd', 'secondary':'#162675', 'background':'#edf2ff',
          'text':'#111943', 'accent':'#d89969'}
TEXTS = {
    'login.title': ('login', 120, 'O seu futuro,\nno seu ritmo'),
    'dashboard.title': ('dashboard', 120, 'Seu próximo passo,\ncom mais clareza.'),
    'dashboard.intro': ('dashboard', 500, 'Comece pelo seu perfil. O resto vem no seu ritmo.'),
    'dashboard.resume': ('dashboard', 120, 'Seu currículo,\ndo seu jeito.'),
    'profile.title': ('profile', 120, 'Meu perfil'),
    'profile.intro': ('profile', 500, 'Organize suas informações profissionais.'),
    'jobs.title': ('jobs', 120, 'Encontre seu próximo passo.'),
    'jobs.intro': ('jobs', 500, 'Cada oportunidade exibida direciona para a página original onde foi publicada.'),
    'courses.title': ('courses', 120, 'Cursos'),
    'resume.title': ('resume', 120, 'Meu currículo'),
    'resume.intro': ('resume', 500, 'Envie um currículo pronto ou crie uma versão profissional com as suas próprias informações.'),
    'account.title': ('account', 120, 'Minha conta'),
    'account.intro': ('account', 500, 'Cuide dos seus dados de acesso e da sua privacidade.'),
}
SECTIONS = {
    'login': [('intro','Apresentação',False), ('forms','Login e cadastro',True)],
    'dashboard': [('intro','Introdução',False), ('shortcuts','Atalhos',False), ('guidance','Orientação',False)],
    'profile': [('heading','Cabeçalho',True), ('progress','Progresso',True), ('help','Explicação do progresso',False), ('data','Dados profissionais',True)],
    'jobs': [('heading','Cabeçalho',True), ('catalog','Catálogo e filtros',True)],
    'courses': [('heading','Cabeçalho',True), ('catalog','Catálogo e filtros',True)],
    'resume': [('heading','Cabeçalho',True), ('tools','Envio e criação',True), ('saved','Currículos salvos',True)],
    'account': [('heading','Cabeçalho',True), ('security','Conta, segurança e privacidade',True)],
}
INTERNAL_LINKS = ('/', '/#dashboard', '/#profile', '/#jobs', '/#courses', '/#resume', '/#account',
                  '/termos-de-uso', '/politica-de-privacidade', '/cookies')


def defaults():
    return {'theme': dict(COLORS, heading_font='Plus Jakarta Sans', body_font='DM Sans', logo=None),
            'texts': {key: item[2] for key,item in TEXTS.items()},
            'layout': {page:[{'key':page+'.'+key, 'visible':True} for key,_,_ in items]
                       for page,items in SECTIONS.items()}, 'blocks':[]}


def plain(value, limit, empty=False):
    if not isinstance(value, str) or len(value)>limit or (not empty and not value.strip()) or '\x00' in value:
        raise ValueError('Confira os textos obrigatórios e seus limites de tamanho.')
    return value


def keys(value, allowed):
    if not isinstance(value, dict) or set(value) != set(allowed):
        raise ValueError('Campo desconhecido ou ausente no catálogo do editor.')


def link(value):
    plain(value, 2048)
    if value in INTERNAL_LINKS:
        return value
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password
                or parsed.port not in {None,80,443} or any(c.isspace() or ord(c)<32 for c in value)
                or '\\' in value):
            raise ValueError()
    except ValueError:
        raise ValueError('Use um link http/https válido ou uma rota interna permitida.')
    return value


def validate(value):
    keys(value, ('theme','texts','layout','blocks'))
    theme, texts, layout, blocks = (value[k] for k in ('theme','texts','layout','blocks'))
    keys(theme, defaults()['theme'])
    for key in COLORS:
        if not isinstance(theme[key],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',theme[key]):
            raise ValueError('Cores devem usar #RRGGBB.')
    for key in ('heading_font','body_font'):
        if theme[key] not in FONTS:
            raise ValueError('Escolha uma fonte da lista local.')
    if theme['logo'] is not None:
        keys(theme['logo'], ('name','alt'))
        if not isinstance(theme['logo']['name'],str) or not re.fullmatch(r'[0-9a-f]{32}\.png',theme['logo']['name']):
            raise ValueError('Logo inválido.')
        plain(theme['logo']['alt'],160)
    keys(texts, TEXTS)
    for key,(_,limit,_) in TEXTS.items():
        plain(texts[key],limit)
    keys(layout, SECTIONS)
    for page, sections in SECTIONS.items():
        items = layout[page]
        allowed = {page+'.'+key for key,_,_ in sections}
        if not isinstance(items,list) or len(items)!=len(sections):
            raise ValueError('Estrutura inválida.')
        for item in items:
            keys(item, ('key','visible'))
            if not isinstance(item['key'],str) or item['key'] not in allowed or type(item['visible']) is not bool:
                raise ValueError('Seção inválida.')
        if len({item['key'] for item in items})!=len(sections):
            raise ValueError('Seção duplicada.')
        for index,(key,_,locked) in enumerate(sections):
            if locked and items[index] != {'key':page+'.'+key,'visible':True}:
                raise ValueError('Uma seção essencial não pode ser ocultada nem deslocada.')
    if not isinstance(blocks,list) or len(blocks)>30:
        raise ValueError('O site permite até 30 blocos.')
    ids = set()
    for block in blocks:
        keys(block, ('id','slot','type','visible','title','body','label','url','style','items'))
        identifier = block['id']
        if not isinstance(identifier,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',identifier) or identifier in ids:
            raise ValueError('Identificador de bloco inválido ou duplicado.')
        ids.add(identifier)
        if not isinstance(block['slot'],str) or block['slot'] not in PAGES or type(block['visible']) is not bool:
            raise ValueError('Slot ou visibilidade inválidos.')
        if block['type'] not in ('text','notice','button','faq') or block['style'] not in ('info','warning'):
            raise ValueError('Tipo de bloco inválido.')
        for key,limit in [('title',120),('body',3000),('label',120),('url',2048)]:
            plain(block[key],limit,empty=True)
        if block['type']=='button':
            plain(block['label'],120); link(block['url'])
        if not isinstance(block['items'],list) or len(block['items'])>12:
            raise ValueError('Use até 12 perguntas por bloco.')
        for item in block['items']:
            keys(item, ('question','answer')); plain(item['question'],200); plain(item['answer'],2000)
    return copy.deepcopy(value)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def contrast(theme):
    def luminance(color):
        rgb = [int(color[i:i+2],16)/255 for i in (1,3,5)]
        rgb = [v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(v*w for v,w in zip(rgb,(.2126,.7152,.0722)))
    a,b = sorted((luminance(theme['text']),luminance(theme['background'])))
    return round((b+.05)/(a+.05),2)


def changes(before, after):
    result = []
    for kind,label in [('theme','Tema'),('texts','Textos'),('layout','Seções'),('blocks','Blocos')]:
        if before[kind]!=after[kind]:
            result.append(label)
    return result


def catalog():
    return {'pages':PAGES, 'fonts':FONTS, 'colors':list(COLORS), 'internal_links':INTERNAL_LINKS,
            'texts':{key:{'page':page,'limit':limit,'default':default} for key,(page,limit,default) in TEXTS.items()},
            'sections':{page:[{'key':page+'.'+key,'label':label,'locked':locked} for key,label,locked in items]
                        for page,items in SECTIONS.items()}}
