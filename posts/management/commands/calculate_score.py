from django.core.management.base import BaseCommand, CommandError
import os
from django.utils.timezone import now
from django.utils.dateparse import parse_datetime

from django.db.models import Count, F
from django.db import transaction, IntegrityError
from django.core.exceptions import ObjectDoesNotExist

from posts.models import Content
from reacts.models import Reaction

from bubblyb.utils import count_db_hits, perf_timer

location = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__))
)
save_file = os.path.join(location, "last_ran.txt")
now = now()

def read_last_ran():
    try:
        f = open(save_file, "r")
        return parse_datetime( f.read() )
        f.close()
    except (FileNotFoundError, ):
        return parse_datetime("2018-12-22 17:01:41.253700+00:00")
    
def save_time_ran():
    f = open(save_file, "w")
    f.write( str(now) )
    f.close()
    
# @perf_timer
# @count_db_hits
def calculate_post_score():
    last_ran = read_last_ran()
    recent = Reaction.objects.filter(timestamp__gt = last_ran)
    aggregated = recent.values('to').annotate(count=Count('to'))
    with transaction.atomic():
        for item in aggregated:
            # ideally to avoid catching in atomic. but i think my code is fine
            try:
                content = Content.objects.get(id=item['to'])
            except ObjectDoesNotExist:
                continue
            cmty = content.allocated_to
            try:
                membership = cmty.membership_set.get(user=content.author)
            except ObjectDoesNotExist:
                continue
            membership.reputation_point = F('reputation_point') + item['count']
            membership.save()
    save_time_ran()


class Command(BaseCommand):
    help = "Calculate reputation point"

    def handle(self, *args, **options):
        calculate_post_score()
