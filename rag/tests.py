from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from rag.views import chat_view

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


class SessionDict(dict):
    modified = False


class RagChatViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = Mock(is_authenticated=True, is_staff=True, is_superuser=True)
        self.user.has_perm.return_value = False
        self.user.groups.values_list.return_value = []

    def build_request(self, method='get', data=None, session=None, anonymous=False):
        request_method = getattr(self.factory, method)
        request = request_method(reverse('rag_chat'), data=data or {})
        request.user = AnonymousUser() if anonymous else self.user
        request.session = session if session is not None else SessionDict()
        return request

    def test_chat_exige_autenticacion(self):
        response = chat_view(self.build_request(anonymous=True))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_chat_muestra_formulario(self):
        response = chat_view(self.build_request())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Asistente de conocimiento')
        self.assertContains(response, 'name="question"')

    @patch('rag.views.responder_pregunta')
    def test_chat_guarda_respuesta_y_fuentes_en_sesion(self, responder):
        responder.return_value = SimpleNamespace(
            text='El backend utiliza Django [Fuente 1].',
            sources=(
                SimpleNamespace(filename='manual.docx', score=0.95),
            ),
        )
        session = SessionDict()

        response = chat_view(
            self.build_request(
                method='post',
                data={'question': '¿Qué usa el backend?'},
                session=session,
            )
        )

        self.assertEqual(response.status_code, 302)
        page = chat_view(self.build_request(session=session))
        self.assertContains(page, 'El backend utiliza Django')
        self.assertContains(page, 'manual.docx')
        responder.assert_called_once_with('¿Qué usa el backend?')

    def test_chat_permite_limpiar_historial(self):
        session = SessionDict(
            rag_chat_history=[{'question': 'Q', 'answer': 'A', 'sources': []}]
        )

        response = chat_view(
            self.build_request(method='post', data={'action': 'clear'}, session=session)
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('rag_chat'))
        self.assertNotIn('rag_chat_history', session)
