import json
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
    actions: tuple[dict, ...] = ()
    operation: str = 'documentacion'


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


def responder_pregunta_hibrida(pregunta, user, max_resultados=3):
    """Permite al modelo elegir entre documentación y consultas seguras al sistema."""
    from .tools import (
        TOOL_DEFINITIONS,
        buscar_orden,
        consultar_inventario_cliente,
        consultar_procesos_orden,
        contar_ordenes_por_estado,
        generar_reporte,
    )

    pregunta = str(pregunta or '').strip()
    if not pregunta:
        raise ValueError('La pregunta no puede estar vacía.')

    client = get_openai_client()
    instructions = (
        'Eres el asistente híbrido de AgroInduGestor. Debes usar una o más de las '
        'herramientas disponibles para responder. Usa buscar_documentacion para '
        'preguntas conceptuales o técnicas y las demás funciones para datos actuales. '
        'Nunca inventes datos. Responde en español, con claridad y brevedad. '
        'Si una herramienta devuelve un error o falta un dato, explícalo. '
        'No muestres estructuras JSON ni detalles internos de las herramientas.'
    )
    input_items = [{'role': 'user', 'content': pregunta}]
    first_response = client.responses.create(
        model=settings.OPENAI_MODEL,
        instructions=instructions,
        input=input_items,
        tools=TOOL_DEFINITIONS,
        tool_choice='required',
        parallel_tool_calls=False,
        max_output_tokens=500,
        store=False,
    )

    input_items.extend(first_response.output)
    sources = []
    actions = []
    operations = []
    function_calls = [
        item for item in first_response.output
        if getattr(item, 'type', None) == 'function_call'
    ][:3]
    if not function_calls:
        raise RuntimeError('OpenAI no seleccionó una fuente de información válida.')

    for tool_call in function_calls:
        try:
            arguments = json.loads(tool_call.arguments or '{}')
        except json.JSONDecodeError as exc:
            raise RuntimeError('OpenAI devolvió argumentos de herramienta inválidos.') from exc

        name = tool_call.name
        operations.append(name)
        if name == 'buscar_documentacion':
            found = buscar_documentos(
                arguments.get('pregunta', pregunta),
                max_resultados=max_resultados,
            )
            sources.extend(found)
            result = {
                'ok': bool(found),
                'fuentes': [
                    {
                        'numero': position,
                        'archivo': item.filename,
                        'similitud': round(item.score, 4),
                        'contenido': item.text,
                    }
                    for position, item in enumerate(found, start=1)
                ],
            }
        elif name == 'buscar_orden':
            result = buscar_orden(user, arguments.get('numero_orden', ''))
        elif name == 'contar_ordenes_por_estado':
            result = contar_ordenes_por_estado(user, arguments.get('estado', ''))
        elif name == 'consultar_inventario_cliente':
            result = consultar_inventario_cliente(user, arguments.get('cliente', ''))
        elif name == 'consultar_procesos_orden':
            result = consultar_procesos_orden(user, arguments.get('numero_orden', ''))
        elif name == 'generar_reporte_facturacion':
            result = generar_reporte(user, arguments.get('numero_orden', ''), 'facturacion')
        elif name == 'generar_reporte_cliente':
            result = generar_reporte(user, arguments.get('numero_orden', ''), 'cliente')
        else:
            result = {'ok': False, 'error': 'Herramienta no autorizada.'}

        if result.get('action'):
            actions.append(result['action'])
        input_items.append({
            'type': 'function_call_output',
            'call_id': tool_call.call_id,
            'output': json.dumps(result, ensure_ascii=False, default=str),
        })

    final_response = client.responses.create(
        model=settings.OPENAI_MODEL,
        instructions=instructions,
        input=input_items,
        tools=TOOL_DEFINITIONS,
        tool_choice='none',
        max_output_tokens=500,
        store=False,
    )
    answer_text = (final_response.output_text or '').strip()
    if not answer_text:
        raise RuntimeError('OpenAI no devolvió una respuesta de texto.')

    return RagAnswer(
        text=answer_text,
        sources=tuple(sources),
        actions=tuple(actions),
        operation=', '.join(operations),
    )


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
