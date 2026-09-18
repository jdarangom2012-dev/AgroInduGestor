from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings

from rag.services import (
    RagConfigurationError,
    buscar_documentos,
    responder_pregunta,
    subir_documento,
)


class RagServicesTests(SimpleTestCase):
    @override_settings(OPENAI_API_KEY='', OPENAI_VECTOR_STORE_ID='')
    def test_busqueda_exige_configuracion(self):
        with self.assertRaises(RagConfigurationError):
            buscar_documentos('arquitectura del sistema')

    @override_settings(OPENAI_API_KEY='test', OPENAI_VECTOR_STORE_ID='vs_test')
    @patch('rag.services.get_openai_client')
    def test_busqueda_normaliza_resultados(self, get_client):
        client = Mock()
        client.vector_stores.search.return_value = SimpleNamespace(data=[
            SimpleNamespace(
                file_id='file_1',
                filename='manual.docx',
                score=0.95,
                content=[SimpleNamespace(text='Fragmento recuperado')],
            )
        ])
        get_client.return_value = client

        results = buscar_documentos('arquitectura del sistema')

        self.assertEqual(results[0].filename, 'manual.docx')
        self.assertEqual(results[0].text, 'Fragmento recuperado')
        self.assertEqual(results[0].score, 0.95)

    @override_settings(OPENAI_API_KEY='test', OPENAI_VECTOR_STORE_ID='vs_test')
    @patch('rag.services.get_openai_client')
    def test_carga_evitar_duplicados_por_nombre(self, get_client):
        client = Mock()
        existing = SimpleNamespace(id='file_1', status='completed')
        client.vector_stores.files.list.return_value = SimpleNamespace(data=[existing])
        client.files.retrieve.return_value = SimpleNamespace(filename='manual.docx')
        get_client.return_value = client

        with TemporaryDirectory() as directory:
            path = Path(directory) / 'manual.docx'
            path.touch()
            result, created = subir_documento(path)

        self.assertEqual(result.id, 'file_1')
        self.assertFalse(created)
        client.vector_stores.files.upload_and_poll.assert_not_called()

    @override_settings(
        OPENAI_API_KEY='test',
        OPENAI_VECTOR_STORE_ID='vs_test',
        OPENAI_MODEL='gpt-4.1-mini',
    )
    @patch('rag.services.get_openai_client')
    def test_respuesta_usa_contexto_recuperado(self, get_client):
        client = Mock()
        client.vector_stores.search.return_value = SimpleNamespace(data=[
            SimpleNamespace(
                file_id='file_1',
                filename='manual.docx',
                score=0.95,
                content=[SimpleNamespace(text='El backend utiliza Django.')],
            )
        ])
        client.responses.create.return_value = SimpleNamespace(
            output_text='El backend utiliza Django [Fuente 1].'
        )
        get_client.return_value = client

        answer = responder_pregunta('¿Qué usa el backend?')

        self.assertEqual(answer.text, 'El backend utiliza Django [Fuente 1].')
        self.assertEqual(answer.sources[0].filename, 'manual.docx')
        call = client.responses.create.call_args.kwargs
        self.assertEqual(call['model'], 'gpt-4.1-mini')
        self.assertIn('El backend utiliza Django.', call['input'])
        self.assertFalse(call['store'])
