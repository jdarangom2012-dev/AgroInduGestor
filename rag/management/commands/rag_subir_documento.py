from django.core.management.base import BaseCommand, CommandError

from rag.services import RagConfigurationError, subir_documento


class Command(BaseCommand):
    help = 'Carga e indexa un documento en el Vector Store de OpenAI.'

    def add_arguments(self, parser):
        parser.add_argument('ruta')
        parser.add_argument('--categoria', default='documentacion')

    def handle(self, *args, **options):
        try:
            result, created = subir_documento(
                options['ruta'],
                categoria=options['categoria'],
            )
        except (RagConfigurationError, FileNotFoundError, RuntimeError) as error:
            raise CommandError(str(error)) from error

        if created:
            self.stdout.write(self.style.SUCCESS(f'Documento indexado: {result.id}'))
        else:
            self.stdout.write(
                self.style.WARNING(f'El documento ya estaba indexado: {result.id}')
            )
