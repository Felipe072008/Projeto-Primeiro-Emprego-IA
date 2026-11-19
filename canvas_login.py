"""Catálogo fechado e CSS dos layouts do editor visual."""
import re

from conteudo_editavel import PAGES, SECTIONS, link, plain

DEVICES = ('desktop', 'mobile')
# Nome, seletor do site e comportamento. Formulários de acesso, navegação e rodapé
# nunca entram na superfície editável.
CATALOG = {
    'login': {
        'title': ('Título principal', '.intro-copy', 'text'),
        'art': ('Ilustração', '.login-art', 'image'),
        'glass': ('Card de vidro', '[data-canvas="glass"]', 'card'),
    },
    'dashboard': {
        'eyebrow': ('Seu espaço', '.overview-intro .eyebrow', 'text'),
        'title': ('Título principal', '.overview-intro h1', 'text'),
        'intro': ('Introdução', '.overview-intro .lead', 'text'),
        'profile': ('Completar meu perfil', '.overview-intro [data-go]', 'action'),
        **{route: (name, '.overview-shortcut:has([data-go="'+route+'"])', 'functional')
           for route, name in [('resume','Meu currículo'),('jobs','Vagas'),('courses','Cursos')]},
        'guidance': ('Orientação personalizada', '.more-guidance', 'dynamic'),
    },
}
for page in ('profile', 'jobs', 'courses', 'resume', 'account'):
    layers = {'title': ('Título', '[data-edit-key="'+page+'.title"]', 'text')}
    if page != 'courses':
        layers['intro'] = ('Introdução', '[data-edit-key="'+page+'.intro"]', 'text')
    for key, name, _ in SECTIONS[page]:
        if key not in ('heading', 'security', 'tools'):
            layers[key] = (name, '[data-section-key="'+page+'.'+key+'"]',
                           'system' if key in ('progress','help') else 'dynamic')
    CATALOG[page] = layers
CATALOG['jobs']['location'] = ('Localização', '.verified-pill', 'text')
CATALOG['account']['logout'] = ('Sair', '#logout-button', 'action')
CATALOG['resume'].update({
    'status': ('Disponibilidade da revisão', '#ai-availability', 'system'),
    'upload': ('Envio de currículo', '.upload-option', 'dynamic'),
    'create_title': ('Título da criação', '.create-option h2', 'text'),
    'create_intro': ('Introdução da criação', '.create-option p', 'text'),
    'builder': ('Criar meu currículo', '#open-builder', 'action'),
})

EXTRAS = ('text', 'notice', 'button', 'faq', 'card', 'shape', 'image')
GEOMETRY = ('x','y','w','h','z','visible','locked','style')
LAYOUT_KEYS = {p+'_'+d for p in PAGES for d in DEVICES}
COLOR = re.compile(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?')


def layer_catalog(page, blocks):
    layers = dict(CATALOG[page])
    for block in blocks:
        if block['slot'] == page and block['visible']:
            ident = block['id']
            name = block['title'] or block['label'] or 'Bloco de ' + block['type']
            layers['block_'+ident] = (name, '[data-block-id="'+ident+'"]', 'block')
    return layers


def base_width(page, device):
    if device == 'mobile':
        return 390
    return 560 if page == 'login' else 1280


def number(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'Use um número inteiro entre {low} e {high}.')


def migrate_saved_layout(value):
    """O piloto do login armazenava transparência em porcentagem inteira."""
    theme = value.get('theme') if isinstance(value,dict) else None
    layout = theme.get('login_desktop') if isinstance(theme,dict) else None
    if not isinstance(layout,dict) or set(layout) != {'title','art','glass'}:
        return value
    styles = [item.get('style') if isinstance(item,dict) else None for item in layout.values()]
    if all(isinstance(s,dict) and set(s)=={'color','opacity','blur','radius'} and
           type(s['opacity']) is int and 0 <= s['opacity'] <= 100 for s in styles) and any(s['opacity']>1 for s in styles):
        for style in styles:
            style['opacity'] /= 100
    return value


def validate_canvas(layout, page='login', device='desktop', blocks=()):
    if layout is None:
        return
    known = layer_catalog(page,blocks)
    width = base_width(page, device)
    if not isinstance(layout, dict) or not set(CATALOG[page]) <= layout.keys() or len(layout) > len(known)+30:
        raise ValueError('Camadas ausentes ou em excesso.')
    for key, item in layout.items():
        extra = key not in known
        if extra and not re.fullmatch(r'item_[a-z0-9]{1,32}', key):
            raise ValueError('Elemento fora do catálogo.')
        required = set(GEOMETRY) | ({'kind','text','url','body'} if extra else set())
        if not isinstance(item, dict) or not required <= item.keys() or set(item)-required-{'label','removed','heading','items'}:
            raise ValueError('Propriedade de camada inválida.')
        kind = item['kind'] if extra else known[key][2]
        if extra:
            if kind not in EXTRAS:
                raise ValueError('Tipo de elemento inválido.')
            plain(item['text'], 3000 if kind in ('text','notice') else 500, empty=kind=='shape')
            plain(item['body'], 2000, empty=True)
            if kind == 'button':
                link(item['url'])
            elif item['url'] != '':
                raise ValueError('Somente botões aceitam links.')
        if 'heading' in item:
            if not extra: raise ValueError('Título adicional inválido.')
            plain(item['heading'],120,empty=True)
        if 'items' in item:
            pairs = item['items']
            if not extra or kind!='faq' or not isinstance(pairs,list) or len(pairs)>12:
                raise ValueError('Perguntas inválidas.')
            for pair in pairs:
                if not isinstance(pair,dict) or set(pair)!={'question','answer'}:
                    raise ValueError('Cada pergunta precisa de uma resposta.')
                plain(pair['question'],200); plain(pair['answer'],2000)
        if 'label' in item:
            if key=='status' or extra or kind not in ('text','action','image','functional') or (kind=='text' and key=='heading'):
                raise ValueError('Este elemento mantém o conteúdo do site.')
            plain(item['label'], 500)
        for attr, low, high in [('w',16,width),('h',80 if kind=='dynamic' else 16,12000),
                                ('x',0,width-16),('y',0,20000),('z',0,99)]:
            number(item[attr], low, high)
        if item['x']+item['w'] > width or any(type(item[k]) is not bool for k in ('visible','locked')):
            raise ValueError('Elemento fora da área editável.')
        if 'removed' in item and (type(item['removed']) is not bool or
                (item['removed'] and (item['visible'] or kind in ('action','functional','dynamic','system')))):
            raise ValueError('Este elemento não pode ser excluído.')
        if kind in ('action','functional','dynamic','system') and not item['visible']:
            raise ValueError('Uma função do site precisa continuar disponível.')
        style = item['style']
        limits = {'blur':(0,40),'radius':(0,48),'border':(0,12),'font':(12,96),'shadow':(0,3)}
        if not isinstance(style,dict) or set(style)-set(limits)-{'color','ink','line','align','opacity','borderOpacity'}:
            raise ValueError('Estilo fora do catálogo.')
        for prop in style:
            if prop in ('opacity','borderOpacity'):
                if type(style[prop]) not in (int,float) or not 0 <= style[prop] <= 1:
                    raise ValueError('Opacidade fora da faixa de 0 a 1.')
            elif prop in limits:
                number(style[prop], *limits[prop])
            elif prop=='align':
                if style[prop] not in ('left','center','right'):
                    raise ValueError('Alinhamento inválido.')
            elif not isinstance(style[prop],str) or not COLOR.fullmatch(style[prop]):
                raise ValueError('Cor inválida.')


def rgba(color, opacity):
    opacity *= int(color[7:] or 'ff',16)
    return color[:7]+format(round(opacity),'02x')


def canvas_css(layout, page='login', device='desktop', blocks=()):
    if layout is None:
        return ''
    validate_canvas(layout, page, device, blocks)
    width = base_width(page,device)
    board = f'[data-layout-board="{page}"]'
    rules = []
    for key, item in layout.items():
        scope = board+f'>[data-layer="{key}"]'
        known = layer_catalog(page,blocks).get(key)
        kind = known[2] if known else item['kind']
        def unit(prop):
            return f'{100*item[prop]/width:.5f}cqw'
        styles = [f'margin:{unit("y")} 0 0 {unit("x")}', f'width:{unit("w")}',
                  f'min-height:{unit("h")}', f'z-index:{item["z"]}']
        if kind in ('dynamic','shape','image') or key=='glass':
            styles.append(f'height:{unit("h")}')
        if kind=='dynamic':
            styles.extend(['min-height:80px','overflow:auto'])
        if not item['visible']:
            styles.append('display:none!important')
        s = item['style']
        if 'color' in s and (kind in ('shape','card') or 'border' in s):
            styles += ['background:'+rgba(s['color'],s.get('opacity',1)),
                       f'backdrop-filter:blur({s.get("blur",0)}px)',
                       f'border-radius:{s.get("radius",0)}px',
                       f'border:{s.get("border",1)}px solid '+rgba(s.get('line','#ffffff'),s.get('borderOpacity',0.45))]
        if 'shadow' in s:
            styles.append('box-shadow:'+('none','0 2px 6px #10184222','0 6px 18px #10184233','0 12px 32px #10184244')[s['shadow']])
        rules.append(scope+'{'+ ';'.join(styles)+'}')
        text = []
        if 'ink' in s: text.append('color:'+s['ink'])
        if 'font' in s: text.append(f'font-size:{s["font"]}px')
        if 'align' in s: text.append('text-align:'+s['align'])
        if text:
            rules.append(scope+','+scope+' :is(h1,h2,p,a,summary,button){'+';'.join(text)+'}')
    query = '(min-width:900px)' if device=='desktop' else '(width < 900px)'
    return '@media '+query+'{'+''.join(rules)+'}'


def blend(foreground, background, opacity=1):
    alpha = int(foreground[7:] or 'ff',16) / 255 * opacity
    return '#' + ''.join(f'{round(int(foreground[i:i+2],16)*alpha + int(background[i:i+2],16)*(1-alpha)):02x}'
                         for i in (1,3,5))


def problems(theme, blocks=()):
    from conteudo_editavel import contrast
    found = []
    for key in sorted(LAYOUT_KEYS & theme.keys()):
        page, device = key.rsplit('_',1)
        for layer, item in (theme[key] or {}).items():
            if not item['visible']:
                continue
            style = item['style']
            title = layer_catalog(page,blocks).get(layer, (item.get('text','Elemento'),))[0]
            prefix = f'{PAGES[page]} · {"Celular" if device=="mobile" else "Computador"} · {title}'
            if style.get('font',14) < (14 if device=='mobile' else 12):
                found.append({'critical':True,'message':prefix+' — texto abaixo do mínimo.', 'layout':key,'layer':layer,'fix':'font'})
            if 'ink' in style or ('color' in style and (item.get('kind') not in ('shape','image') and layer not in ('glass','art'))):
                base = theme.get('board_backgrounds',{}).get(key) or ('#2a43ac' if page=='login' else theme['background'])
                background = blend(style.get('color', base), base, style.get('opacity',1))
                ink = blend(style.get('ink', '#ffffff' if page=='login' else theme['text']), background)
                if contrast({'text':ink,'background':background}) < 4.5:
                    found.append({'critical':False,'message':prefix+' — contraste abaixo de 4,5:1.', 'layout':key,'layer':layer,'fix':'ink','suggestion':'#000000' if contrast({'text':'#000000','background':background}) >= 4.5 else '#ffffff'})
    return found
