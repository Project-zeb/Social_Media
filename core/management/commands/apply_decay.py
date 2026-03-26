from django.core.management.base import BaseCommand
from core.utils.decay_logic import apply_global_decay

class Command(BaseCommand):
    help = 'Reduces truth scores of all events based on time'

    def handle(self, *args, **options):
        apply_global_decay()
        self.stdout.write(self.style.SUCCESS('Successfully decayed global truth scores.'))