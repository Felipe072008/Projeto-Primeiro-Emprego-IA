"""Section validation and truthful text views for existing profile consumers."""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

EDUCATION_OPTIONS = (
    'Fundamental Incompleto', 'Fundamental Completo', 'Médio Incompleto',
    'Médio Completo', 'Cursando Ensino Médio', 'Superior Incompleto',
    'Cursando Superior', 'Superior Completo',
)
SECTIONS = ('contact', 'goals', 'experiences', 'education', 'courses', 'skills', 'languages', 'projects', 'availability')
LIST_FIELDS = {'experiences': 'professional_experience', 'courses': 'courses', 'skills': 'skills', 'languages': 'languages', 'projects': 'academic_experience'}
REQUIRED = {'phone': 'Telefone', 'age': 'Idade', 'city': 'Cidade', 'state': 'Estado', 'desired_area': 'Área profissional', 'education': 'Escolaridade', 'skills': 'Habilidades', 'languages': 'Idiomas'}
CAREERS = Path(__file__).resolve().parent / 'static' / 'occupations.json'


class ProfileError(ValueError):
    def __init__(self, errors):
        super().__init__('Confira os campos indicados.')
        self.errors = errors


def key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold().strip()) if not unicodedata.combining(c))


def defaults(profile):
    result = {
        'contact': {field: profile.get(field, '') for field in ('phone', 'age', 'city', 'state')},
        'goals': {'desired_area': profile.get('desired_area', ''), 'objective': profile.get('objective', ''), 'secondary_areas': [], 'contracts': [], 'work_modes': [], 'salary': ''},
        'education': {'level': profile.get('education', ''), 'legacy': profile.get('course', ''), 'items': []},
        'availability': {'periods': [], 'days': [], 'other_city': '', 'travel': ''},
    }
    for section, field in LIST_FIELDS.items():
        result[section] = {'items': [], 'legacy': profile.get(field, '')}
    result['experiences']['no_experience'] = False
    return result


def validate_section(section, data, previous):
    errors = {}
    if section not in SECTIONS or not isinstance(data, dict):
        raise ProfileError({'_form': 'Seção ou dados inválidos.'})
    allowed = set(previous)
    if set(data) - allowed:
        raise ProfileError({'_form': 'O formulário contém campos desconhecidos.'})
    # A section save is complete, while every other section remains untouched.
    result = {}

    def text(source, field, path=None, required=False, limit=2000):
        value = source.get(field, '')
        path = path or field
        if not isinstance(value, str) or len(value) > limit:
            errors[path] = f'Use um texto de até {limit} caracteres.'
            return ''
        value = value.strip()
        if required and not value:
            errors[path] = 'Preencha este campo.'
        return value

    def choices(field, options, maximum=10):
        values = data.get(field, [])
        if not isinstance(values, list) or len(values) > maximum or any(not isinstance(v, str) or v not in options for v in values):
            errors[field] = 'Selecione opções válidas.'
            return []
        return list(dict.fromkeys(values))

    if section == 'contact':
        result = {field: text(data, field, required=True, limit=120) for field in allowed}
        for field, maximum in (('phone', 11), ('age', 3)):
            value = result[field]
            if not re.fullmatch(r'[0-9]{1,' + str(maximum) + '}', value):
                errors[field] = f'Use apenas números, com até {maximum} dígitos.'
        if result['age'].isdigit() and not 1 <= int(result['age']) <= 120:
            errors['age'] = 'Informe uma idade de 1 a 120 anos.'
    elif section == 'goals':
        career_titles = {item['title'] for item in json.loads(CAREERS.read_text(encoding='utf-8'))['occupations']}
        result = {field: text(data, field, required=field == 'desired_area', limit=160 if field != 'objective' else 2000) for field in ('desired_area', 'objective', 'salary')}
        if result['desired_area'] not in career_titles and result['desired_area'] != previous['desired_area']:
            errors['desired_area'] = 'Selecione uma área sugerida.'
        result['secondary_areas'] = choices('secondary_areas', career_titles, 3)
        result['secondary_areas'] = [v for v in result['secondary_areas'] if v != result['desired_area']]
        result['contracts'] = choices('contracts', {'aprendiz', 'estagio', 'clt'}, 3)
        result['work_modes'] = choices('work_modes', {'Presencial', 'Híbrido', 'Remoto'}, 3)
    elif section == 'availability':
        result['periods'] = choices('periods', {'Manhã', 'Tarde', 'Noite'}, 3)
        result['days'] = choices('days', {'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'}, 7)
        for field in ('other_city', 'travel'):
            result[field] = text(data, field, limit=3)
            if result[field] not in {'', 'Sim', 'Não'}:
                errors[field] = 'Selecione Sim ou Não.'
    else:
        result['legacy'] = text(data, 'legacy', limit=12000)
        if section == 'education':
            result['level'] = text(data, 'level', required=True, limit=80)
            if result['level'] not in EDUCATION_OPTIONS:
                errors['level'] = 'Selecione sua escolaridade.'
        if section == 'experiences':
            result['no_experience'] = data.get('no_experience', False)
            if not isinstance(result['no_experience'], bool):
                errors['no_experience'] = 'Escolha uma opção válida.'
        items = data.get('items', [])
        if not isinstance(items, list) or len(items) > 30:
            raise ProfileError({'items': 'Cadastre até 30 registros por seção.'})
        result['items'] = []
        schemas = {
            'experiences': ('role company contract start end current description', {'role', 'company', 'start'}),
            'education': ('level course institution status year city state', {'level', 'institution', 'status'}),
            'courses': ('name institution hours status year certificate_url', {'name', 'institution', 'status'}),
            'skills': ('name', {'name'}),
            'languages': ('language level', {'language', 'level'}),
            'projects': ('title context start end description', {'title', 'description'}),
        }
        fields, required = schemas[section]
        seen = set()
        for index, item in enumerate(items):
            prefix = f'items.{index}.'
            if not isinstance(item, dict) or set(item) - set(fields.split()):
                errors[f'items.{index}'] = 'Registro inválido.'
                continue
            clean = {}
            for field in fields.split():
                if field == 'current':
                    clean[field] = item.get(field, False)
                    if not isinstance(clean[field], bool):
                        errors[prefix + field] = 'Escolha uma opção válida.'
                else:
                    clean[field] = text(item, field, prefix + field, field in required, 2000 if field == 'description' else 300)
            for field in ('start', 'end'):
                if field not in clean or not clean[field]:
                    continue
                try:
                    parsed = date.fromisoformat(clean[field])
                    if section == 'experiences' and parsed > date.today():
                        errors[prefix + field] = 'A data de experiência não pode estar no futuro.'
                except ValueError:
                    errors[prefix + field] = 'Informe uma data válida.'
            if clean.get('current'):
                clean['end'] = ''
            if clean.get('start') and clean.get('end') and clean['end'] < clean['start']:
                errors[prefix + 'end'] = 'A data final deve ser igual ou posterior à inicial.'
            if 'year' in clean and clean['year'] and (not re.fullmatch(r'[0-9]{4}', clean['year']) or not 1900 <= int(clean['year']) <= date.today().year + 20):
                errors[prefix + 'year'] = 'Informe um ano válido com quatro dígitos.'
            if 'hours' in clean and clean['hours'] and not re.fullmatch(r'[0-9]{1,5}', clean['hours']):
                errors[prefix + 'hours'] = 'Informe a quantidade de horas em números.'
            if 'status' in clean and clean['status'] not in {'Cursando', 'Concluído', 'Interrompido'}:
                errors[prefix + 'status'] = 'Selecione uma situação válida.'
            if clean.get('status') == 'Concluído' and clean.get('year', '').isdigit() and int(clean['year']) > date.today().year:
                errors[prefix + 'year'] = 'Para um ano futuro, selecione Cursando e informe a previsão.'
            if section == 'education' and clean['level'] not in EDUCATION_OPTIONS:
                errors[prefix + 'level'] = 'Selecione um nível válido.'
            if section == 'experiences' and clean['contract'] not in {'', 'Jovem Aprendiz', 'Estágio', 'CLT', 'Outra experiência'}:
                errors[prefix + 'contract'] = 'Selecione um vínculo válido.'
            if section == 'languages' and clean['level'] not in {'Básico', 'Intermediário', 'Avançado', 'Fluente', 'Nativo'}:
                errors[prefix + 'level'] = 'Selecione um nível válido.'
            if section in {'skills', 'languages'}:
                identity = key(clean['name' if section == 'skills' else 'language'])
                if identity in seen:
                    errors[prefix + ('name' if section == 'skills' else 'language')] = 'Este item já foi adicionado.'
                seen.add(identity)
            if clean.get('certificate_url'):
                url = urlparse(clean['certificate_url'])
                if url.scheme not in {'https', 'http'} or not url.hostname or url.username or url.password:
                    errors[prefix + 'certificate_url'] = 'Use um link HTTP ou HTTPS válido.'
            result['items'].append(clean)
        if section in {'skills', 'languages'} and not result['items'] and not result['legacy'] and not previous['items'] and not previous['legacy']:
            errors['items'] = 'Adicione pelo menos um item.'
        if section == 'experiences' and result['no_experience'] and (result['items'] or result['legacy']):
            errors['no_experience'] = 'Há experiências cadastradas. Remova-as explicitamente antes de marcar esta opção.'
    if errors:
        raise ProfileError(errors)
    return result


def display_date(value):
    return '/'.join(reversed(value.split('-'))) if value else ''


def record_text(section, item):
    if section == 'experiences':
        period = f"{display_date(item['start'])} a {'atualmente' if item['current'] else display_date(item['end']) or 'término não informado'}"
        return '\n'.join(filter(None, [f"{item['role']} — {item['company']}", item['contract'], period, item['description']]))
    if section == 'education':
        year = (('Previsão: ' if item['status'] == 'Cursando' else 'Conclusão: ' if item['status'] == 'Concluído' else 'Ano informado: ') + item['year']) if item['year'] else ''
        return ' · '.join(filter(None, [item['course'], item['level'], item['institution'], item['status'], year, ' / '.join(filter(None,[item['city'],item['state']]))]))
    if section == 'courses':
        year = (('Previsão: ' if item['status'] == 'Cursando' else 'Conclusão: ' if item['status'] == 'Concluído' else 'Ano informado: ') + item['year']) if item['year'] else ''
        return ' · '.join(filter(None, [item['name'], item['institution'], item['hours']+'h' if item['hours'] else '', item['status'], year, item['certificate_url']]))
    if section == 'skills':
        return item['name']
    if section == 'languages':
        return f"{item['language']} — {item['level']}"
    return '\n'.join(filter(None,[item['title'],item['context'],' a '.join(filter(None,[display_date(item['start']),display_date(item['end'])])),item['description']]))


def hydrate_profile(raw, stored):
    profile = dict(raw)
    sections = defaults(raw)
    sections.update(stored)
    profile['sections'] = sections
    profile.update(sections['contact'])
    profile.update({field: sections['goals'][field] for field in ('desired_area', 'objective')})
    profile['education'] = sections['education']['level']
    for section, field in LIST_FIELDS.items():
        data = sections[section]
        items = data['items']
        if section == 'experiences':
            items = sorted(items, key=lambda item: (item['current'], item['start']), reverse=True)
        parts = [data['legacy']] + [record_text(section, item) for item in items]
        profile[field] = ('; ' if section in {'skills','languages'} else '\n\n').join(filter(None,parts))
    resume_fields = {field: profile.get(field,'') for field in ('education','course','professional_experience','academic_experience','courses','skills','languages','objective')}
    resume_fields['education'] = '\n\n'.join(filter(None,[profile['education']] + [record_text('education',item) for item in sections['education']['items']]))
    resume_fields['course'] = sections['education']['legacy']
    availability = sections['availability']
    resume_fields['additional_information'] = ' · '.join(filter(None,[', '.join(availability['periods']), ', '.join(availability['days']), 'Trabalho em outra cidade: '+availability['other_city'] if availability['other_city'] else '', 'Viagens: '+availability['travel'] if availability['travel'] else '']))
    profile['resume_fields'] = resume_fields
    profile['missing_fields'] = [label for field,label in REQUIRED.items() if not profile.get(field,'').strip()]
    return profile
