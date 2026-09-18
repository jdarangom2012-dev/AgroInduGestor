from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from openai import OpenAIError

from .quota import (
    RagQuotaExceeded,
    complete_query,
    fail_query,
    get_quota_status,
    reserve_query,
)
from .services import RagConfigurationError, responder_pregunta_hibrida


SESSION_KEY = 'rag_chat_history'
MAX_HISTORY_ITEMS = 10
MAX_QUESTION_LENGTH = 1000


@login_required
@require_http_methods(['GET', 'POST'])
def chat_view(request):
    history = request.session.get(SESSION_KEY, [])
    error = ''
    question = ''

    if request.method == 'POST':
        if request.POST.get('action') == 'clear':
            request.session.pop(SESSION_KEY, None)
            request.session.modified = True
            return redirect('rag_chat')

        question = request.POST.get('question', '').strip()
        if not question:
            error = 'Escribe una pregunta antes de consultar.'
        elif len(question) > MAX_QUESTION_LENGTH:
            error = f'La pregunta no puede superar {MAX_QUESTION_LENGTH} caracteres.'
        else:
            reservation = None
            try:
                reservation = reserve_query(request.user, question)
                answer = responder_pregunta_hibrida(question, request.user)
            except RagQuotaExceeded as exc:
                error = str(exc)
            except (RagConfigurationError, ValueError, RuntimeError, OpenAIError) as exc:
                if reservation is not None:
                    fail_query(reservation, exc)
                error = f'No fue posible consultar el asistente: {exc}'
            else:
                complete_query(reservation, answer.operation)
                uses_docs = 'buscar_documentacion' in answer.operation
                uses_system = any(
                    operation in answer.operation
                    for operation in (
                        'buscar_orden', 'contar_ordenes_por_estado',
                        'consultar_inventario_cliente', 'consultar_procesos_orden',
                        'generar_reporte_facturacion', 'generar_reporte_cliente',
                    )
                )
                if uses_docs and uses_system:
                    source_type = 'Documentos + datos del sistema'
                elif uses_system:
                    source_type = 'Datos actuales del sistema'
                else:
                    source_type = 'Documentación indexada'
                history.append({
                    'question': question,
                    'answer': answer.text,
                    'sources': [
                        {
                            'filename': source.filename,
                            'score': round(source.score, 4),
                        }
                        for source in answer.sources
                    ],
                    'actions': list(answer.actions),
                    'source_type': source_type,
                })
                history = history[-MAX_HISTORY_ITEMS:]
                request.session[SESSION_KEY] = history
                request.session.modified = True
                return redirect('rag_chat')

    quota = get_quota_status()
    return render(
        request,
        'rag/chat.html',
        {
            'history': history,
            'error': error,
            'question': question,
            'max_question_length': MAX_QUESTION_LENGTH,
            'quota': quota,
        },
    )
