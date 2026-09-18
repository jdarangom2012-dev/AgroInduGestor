from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from openai import OpenAI


class RagConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RagSearchResult:
    file_id: str
    filename: str
    score: float
    text: str


@dataclass(frozen=True)
class RagAnswer:
    text: str
    sources: tuple[RagSearchResult, ...]


def get_openai_client():
    if not settings.OPENAI_API_KEY:
        raise RagConfigurationError('Falta OPENAI_API_KEY en el archivo .env.')
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def get_vector_store_id():
    if not settings.OPENAI_VECTOR_STORE_ID:
        raise RagConfigurationError('Falta OPENAI_VECTOR_STORE_ID en el archivo .env.')
    return settings.OPENAI_VECTOR_STORE_ID


def buscar_documentos(pregunta, max_resultados=3):
    pregunta = str(pregunta or '').strip()
    if not pregunta:
        raise ValueError('La pregunta no puede estar vacía.')
    if not 1 <= max_resultados <= 50:
        raise ValueError('max_resultados debe estar entre 1 y 50.')

    response = get_openai_client().vector_stores.search(
        vector_store_id=get_vector_store_id(),
        query=pregunta,
        max_num_results=max_resultados,
    )
    return [
        RagSearchResult(
            file_id=item.file_id,
            filename=item.filename,
            score=float(item.score),
            text='\n'.join(
                block.text for block in item.content if getattr(block, 'text', None)
            ).strip(),
        )
        for item in response.data
    ]


def responder_pregunta(pregunta, max_resultados=3):
    """Recupera contexto relevante y genera una respuesta sustentada en él."""
    pregunta = str(pregunta or '').strip()
    if not pregunta:
        raise ValueError('La pregunta no puede estar vacía.')

    resultados = buscar_documentos(pregunta, max_resultados=max_resultados)
    if not resultados:
        return RagAnswer(
            text='No encontré información suficiente en los documentos indexados.',
            sources=(),
        )

    contexto = '\n\n'.join(
        f'[Fuente {position}: {resultado.filename}]\n{resultado.text}'
        for position, resultado in enumerate(resultados, start=1)
    )
    response = get_openai_client().responses.create(
        model=settings.OPENAI_MODEL,
        instructions=(
            'Eres el asistente de conocimiento de AgroInduGestor. '
            'Responde en español, de forma clara y breve, usando únicamente el '
            'contexto recuperado. No inventes información. Si el contexto no '
            'permite responder, indícalo explícitamente. Al sustentar un dato, '
            'menciona la fuente con el formato [Fuente N].'
        ),
        input=f'Pregunta:\n{pregunta}\n\nContexto recuperado:\n{contexto}',
        max_output_tokens=500,
        store=False,
    )
    respuesta = (response.output_text or '').strip()
    if not respuesta:
        raise RuntimeError('OpenAI no devolvió una respuesta de texto.')

    return RagAnswer(text=respuesta, sources=tuple(resultados))


def subir_documento(ruta, categoria='documentacion'):
    path = Path(ruta).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f'No existe el documento: {path}')

    client = get_openai_client()
    vector_store_id = get_vector_store_id()

    for vector_file in client.vector_stores.files.list(vector_store_id=vector_store_id).data:
        remote_file = client.files.retrieve(vector_file.id)
        if remote_file.filename == path.name and vector_file.status != 'failed':
            return vector_file, False

    result = client.vector_stores.files.upload_and_poll(
        vector_store_id=vector_store_id,
        file=path,
        attributes={
            'categoria': categoria,
            'sistema': 'AgroInduGestor',
        },
        max_wait_seconds=300,
    )
    if result.status != 'completed':
        raise RuntimeError(f'OpenAI no pudo indexar el documento: {result.last_error}')
    return result, True
