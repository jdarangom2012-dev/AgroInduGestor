from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from openai import OpenAIError

from .services import RagConfigurationError, responder_pregunta


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
            try:
                answer = responder_pregunta(question)
            except (RagConfigurationError, ValueError, RuntimeError, OpenAIError) as exc:
                error = f'No fue posible consultar el asistente: {exc}'
            else:
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
                })
                history = history[-MAX_HISTORY_ITEMS:]
                request.session[SESSION_KEY] = history
                request.session.modified = True
                return redirect('rag_chat')

    return render(
        request,
        'rag/chat.html',
        {
            'history': history,
            'error': error,
            'question': question,
            'max_question_length': MAX_QUESTION_LENGTH,
        },
    )
