from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings

from rag.services import RagConfigurationError, buscar_documentos, subir_documento


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
