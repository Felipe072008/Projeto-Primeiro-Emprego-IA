import copy
import io
import unittest

from pypdf import PdfReader
from documentos_curriculo import build_resume_pdf
from modelo_curriculo import presentation, objective_for, valid_link, accent_id


SAMPLE = {
    'name': 'Candidata de exemplo',
    'headline': 'Assistente administrativo',
    'contacts': ['candidata@example.test', '41996201002', 'Curitiba / PR'],
    'sections': [
        {'title': 'Objetivo profissional', 'content': 'Iniciar em uma oportunidade de apoio administrativo e desenvolver minhas habilidades.'},
        {'title': 'Habilidades', 'content': 'Organização; Trabalho em equipe; Comunicação; Informática básica'},
        {'title': 'Formação acadêmica', 'content': 'Cursando Superior\n\nAnálise e Desenvolvimento de Sistemas · Instituição de exemplo · Cursando · Previsão: 2028'},
        {'title': 'Experiência profissional', 'content': 'Aprendiz administrativo — Empresa de exemplo\nJovem Aprendiz\n10/01/2025 a 10/12/2025\nOrganização de documentos e apoio na atualização de planilhas.\n\nEstagiária de suporte — Empresa de exemplo\nEstágio\n10/01/2026 a atualmente\nApoio aos usuários e organização de equipamentos.'},
        {'title': 'Cursos e certificações', 'content': 'Pacote Office · Instituição de exemplo · 40h · Concluído · Conclusão: 2025\n\nComunicação · Instituição de exemplo · 20h · Concluído · Conclusão: 2026'},
        {'title': 'Idiomas', 'content': 'Português — Nativo; Inglês — Básico'},
        {'title': 'Informações adicionais', 'content': 'Manhã, Tarde'},
    ],
}


class ResumeLayoutTests(unittest.TestCase):
    def test_objectives_and_omissions(self):
        for mode in ('Estágio', 'Jovem Aprendiz', 'CLT'):
            for area in ('', 'Tecnologia'):
                for course in ('', 'Informática'):
                    text = objective_for(mode, area, course)
                    self.assertIn(mode, text)
                    self.assertEqual('na área de' in text, bool(area) and mode != 'Jovem Aprendiz')
                    self.assertEqual('no curso de' in text, bool(course) and mode == 'Estágio')
        self.assertEqual(objective_for('', 'TI', ''), '')
        model = presentation(dict(name='Ana', contacts=['', 'ana@example.test'], sections=[]))
        self.assertEqual(model['contact'], 'ana@example.test')
        self.assertEqual(model['sections'], [])
        self.assertEqual(accent_id('red'), 'marinho')
        for url in ('javascript:alert(1)', 'https://', 'https://a b', 'https://[', 'https://a/'+'x'*500):
            self.assertFalse(valid_link(url))
        self.assertTrue(valid_link('https://example.test/perfil'))

    def test_profile_contract_defaults_are_unambiguous(self):
        from dados_perfil import defaults, hydrate_profile
        profile = dict(desired_area='Administração')
        goals = defaults(profile)['goals']
        for modes, name in [(['aprendiz'], 'Jovem Aprendiz'), (['estagio'], 'Estágio'),
                            (['clt'], 'CLT'), (['clt','aprendiz'], ''), ([], '')]:
            fields = hydrate_profile(profile, {'goals':dict(goals,contracts=modes)})['resume_fields']
            self.assertEqual(fields['modality'], name)
            self.assertEqual(fields['objective_area'], 'Administração')

    def test_course_optional_details_and_page_breaks(self):
        from dados_perfil import curriculum_record
        item = dict(name='Excel', institution='Escola', hours='', year='')
        for hours, year, expected in [('', '', ''), ('20', '', ' (Carga horária: 20h)'),
                                      ('', '2025', ' (Ano: 2025)'), ('20', '2025', ' (Carga horária: 20h | Ano: 2025)')]:
            self.assertEqual(curriculum_record('courses', dict(item,hours=hours,year=year)), 'Excel — Escola' + expected)
        sample = dict(SAMPLE, sections=[dict(title='Formação acadêmica',content='\n\n'.join(
            'Formação %d — Escola\nStatus: Cursando' % i for i in range(55))),
            dict(title='Idiomas',content='Português')])
        pages = PdfReader(build_resume_pdf(sample)).pages
        self.assertGreater(len(pages), 1)
        for page in pages:
            text = page.extract_text().strip()
            self.assertFalse(text.endswith(('FORMAÇÃO ACADÊMICA', 'HABILIDADES E COMPETÊNCIAS')))
            for i in range(55):
                if 'Formação %d — Escola' % i in text:
                    self.assertIn('Status: Cursando', text.split('Formação %d — Escola' % i)[1])

    def test_one_page_embedded_fonts_and_unchanged_data(self):
        original = copy.deepcopy(SAMPLE)
        reader = PdfReader(build_resume_pdf(SAMPLE))
        self.assertEqual(len(reader.pages), 1)
        text = reader.pages[0].extract_text()
        for value in ('CANDIDATA DE EXEMPLO', 'Análise e Desenvolvimento de Sistemas', '(41) 99620-1002', 'Pacote Office', 'Atual'):
            self.assertIn(value, text)
        fonts = [font.get_object() for font in reader.pages[0]['/Resources']['/Font'].values()]
        self.assertTrue(any('Bold' in str(font.get('/BaseFont')) and '/FontFile2' in font['/FontDescriptor'] for font in fonts if '/FontDescriptor' in font))
        self.assertEqual(SAMPLE, original)

    def test_long_records_wrap_and_keep_last_content(self):
        sample = copy.deepcopy(SAMPLE)
        sample['name'] = 'Nome extenso de exemplo ' * 8
        sample['sections'][3]['content'] += '\n\n' + ('Texto longo com acentuação e conteúdo preservado. ' * 500) + '\nFIM DO REGISTRO'
        reader = PdfReader(build_resume_pdf(sample))
        self.assertGreater(len(reader.pages), 1)
        text = '\n'.join(page.extract_text() for page in reader.pages)
        self.assertIn('FIM DO REGISTRO', text)
        self.assertIn('Informações adicionais'.upper(), text)
