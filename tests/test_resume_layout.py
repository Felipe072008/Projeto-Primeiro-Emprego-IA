import copy
import io
import unittest

from pypdf import PdfReader
from resume_documents import build_resume_pdf, resume_section_paragraphs


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
    def test_highlights_lists_and_literal_markup(self):
        section = {'title': 'Cursos e certificações', 'content': '<Curso> & prática · Escola\nDescrição\n\nOutro curso · Outra escola'}
        paragraphs = list(resume_section_paragraphs(section))
        self.assertEqual(paragraphs[0], ('<b>&lt;Curso&gt; &amp; prática</b> · Escola', False, True, False))
        self.assertTrue(paragraphs[1][3])
        self.assertIn('<b>Outro curso</b>', paragraphs[2][0])
        bullets = list(resume_section_paragraphs({'title':'Habilidades','content':'Organização; Comunicação\n● Excel'}))
        self.assertEqual([item[0] for item in bullets], ['Organização','Comunicação','Excel'])
        self.assertTrue(all(item[1] for item in bullets))

    def test_one_page_embedded_fonts_and_unchanged_data(self):
        original = copy.deepcopy(SAMPLE)
        reader = PdfReader(build_resume_pdf(SAMPLE))
        self.assertEqual(len(reader.pages), 1)
        text = reader.pages[0].extract_text()
        for value in ('CANDIDATA DE EXEMPLO', 'Análise e Desenvolvimento de Sistemas', '(41) 99620-1002', 'Pacote Office', 'atualmente'):
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
