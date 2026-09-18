import sys

from django.core.management.base import BaseCommand, CommandError
from openai import OpenAIError

from rag.services import RagConfigurationError, responder_pregunta


class Command(BaseCommand):
    help = 'Responde una pregunta usando los documentos indexados y OpenAI.'

    def add_arguments(self, parser):
        parser.add_argument('pregunta')
        parser.add_argument('--max-resultados', type=int, default=3)

    def handle(self, *args, **options):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        try:
            answer = responder_pregunta(
                options['pregunta'],
                max_resultados=options['max_resultados'],
            )
        except (RagConfigurationError, ValueError, RuntimeError, OpenAIError) as error:
            raise CommandError(str(error)) from error

        self.stdout.write(self.style.SUCCESS('\nRespuesta:'))
        self.stdout.write(answer.text)

        if answer.sources:
            self.stdout.write(self.style.SUCCESS('\nFuentes recuperadas:'))
            for position, source in enumerate(answer.sources, start=1):
                self.stdout.write(
                    f'[{position}] {source.filename} | similitud: {source.score:.4f}'
                )
