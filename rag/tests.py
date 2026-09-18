from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from rag.views import chat_view
from rag.quota import QuotaStatus

from rag.services import (
    RagConfigurationError,
    buscar_documentos,
    responder_pregunta,
    responder_pregunta_hibrida,
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

    @override_settings(OPENAI_API_KEY='test', OPENAI_MODEL='gpt-4.1-mini')
    @patch('rag.tools.buscar_orden')
    @patch('rag.services.get_openai_client')
    def test_respuesta_hibrida_ejecuta_herramienta_autorizada(self, get_client, buscar_orden):
        client = Mock()
        tool_call = SimpleNamespace(
            type='function_call',
            name='buscar_orden',
            arguments='{"numero_orden":"1201"}',
            call_id='call_1',
        )
        first_response = SimpleNamespace(output=[tool_call])
        final_response = SimpleNamespace(output_text='La orden 1201 está completada.')
        client.responses.create.side_effect = [first_response, final_response]
        get_client.return_value = client
        buscar_orden.return_value = {'ok': True, 'orden': '1201', 'estado': 'Completada'}

        answer = responder_pregunta_hibrida('¿Cuál es el estado de la orden 1201?', Mock())

        self.assertEqual(answer.text, 'La orden 1201 está completada.')
        self.assertEqual(answer.operation, 'buscar_orden')
        buscar_orden.assert_called_once()
        second_call = client.responses.create.call_args_list[1].kwargs
        self.assertEqual(second_call['tool_choice'], 'none')
        self.assertEqual(second_call['input'][-1]['type'], 'function_call_output')


class SessionDict(dict):
    modified = False


class RagChatViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = Mock(is_authenticated=True, is_staff=True, is_superuser=True)
        self.user.has_perm.return_value = False
        self.user.groups.values_list.return_value = []
        self.quota_patcher = patch(
            'rag.views.get_quota_status',
            return_value=SimpleNamespace(used=0, limit=10, remaining=10),
        )
        self.quota_patcher.start()
        self.addCleanup(self.quota_patcher.stop)

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
        self.assertContains(response, 'aria-label="Cerrar asistente"')
        self.assertContains(response, reverse('dashboard'))

    @patch('rag.views.complete_query')
    @patch('rag.views.reserve_query')
    @patch('rag.views.responder_pregunta_hibrida')
    def test_chat_guarda_respuesta_y_fuentes_en_sesion(self, responder, reserve, complete):
        reservation = SimpleNamespace(pk=1)
        reserve.return_value = reservation
        responder.return_value = SimpleNamespace(
            text='El backend utiliza Django [Fuente 1].',
            sources=(
                SimpleNamespace(filename='manual.docx', score=0.95),
            ),
            actions=({'url': '/reporte.pdf', 'label': 'Descargar reporte'},),
            operation='buscar_documentacion',
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
        self.assertContains(page, 'Descargar reporte')
        responder.assert_called_once_with('¿Qué usa el backend?', self.user)
        complete.assert_called_once_with(reservation, 'buscar_documentacion')

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


class RagQuotaValueTests(SimpleTestCase):
    def test_saldo_nunca_es_negativo(self):
        self.assertEqual(QuotaStatus(used=10, limit=10).remaining, 0)
        self.assertEqual(QuotaStatus(used=12, limit=10).remaining, 0)

    def test_saldo_refleja_consultas_disponibles(self):
        self.assertEqual(QuotaStatus(used=3, limit=10).remaining, 7)
