from django.core.management.base import BaseCommand, CommandError

from rag.services import RagConfigurationError, buscar_documentos


class Command(BaseCommand):
    help = 'Busca fragmentos relevantes en el Vector Store de OpenAI.'

    def add_arguments(self, parser):
        parser.add_argument('pregunta')
        parser.add_argument('--max-resultados', type=int, default=3)

    def handle(self, *args, **options):
        try:
            results = buscar_documentos(
                options['pregunta'],
                max_resultados=options['max_resultados'],
            )
        except (RagConfigurationError, ValueError) as error:
            raise CommandError(str(error)) from error

        if not results:
            self.stdout.write(self.style.WARNING('No se encontraron fragmentos relevantes.'))
            return

        for position, result in enumerate(results, start=1):
            self.stdout.write(
                self.style.SUCCESS(
                    f'[{position}] {result.filename} | similitud: {result.score:.4f}'
                )
            )
            self.stdout.write(result.text)
            self.stdout.write('')
