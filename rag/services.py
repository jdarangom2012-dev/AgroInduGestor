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
