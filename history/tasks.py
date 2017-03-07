from history.models import Tab, Domain, Page, PageVisit, TimeActive
from authentication.models import CustomUser
from django.utils import timezone
from history.common import shorten_url, create_data, strip_tags, get_count
from history.serializers import PageSerializer
from django.conf import settings
from urllib.parse import urlparse
import requests
from django.db.models import Q
from datetime import timedelta
import os
import json
from collections import Counter
import operator
from celery import task
from celery.decorators import periodic_task
from celery.task.schedules import crontab

@task
def create_page(user_pk, url, base_url, t_id, page_title, domain_title,
                favicon, html, prev_tab, active):

    user = CustomUser.objects.get(pk=user_pk)

    # Get the currently active TimeActive (can only be one if exists)
    ta = TimeActive.objects.filter(end__isnull=True, owned_by=user)

    # Check if a tab exists with this id that is open in this session
    t = Tab.objects.filter(tab_id=t_id, closed__isnull=True, owned_by=user)
    if t.exists():
        t=t[0]
    else:
        if ta.exists() and active:
            ta = ta.first()
            ta.end = timezone.now()
            ta.save()

        if ('https://goo.gl/' not in url and 'hindsite-local' not in url and
                'hindsite-production' not in url and 'chrome://' not in url and
                'file:///' not in url and 'chrome-extension://' not in url):
            t = Tab(tab_id=t_id, owned_by=user)
            t.save()
        else:
            return False

    domains = t.domain_set.all()

    if domains.filter(base_url=base_url, closed__isnull=True).exists():
        d = domains.get(base_url=base_url, closed__isnull=True)
        if favicon != '' and favicon != d.favicon:
            d.favicon = favicon
            d.save()
    else:
        close_domain = domains.filter(closed__isnull=True)

        if close_domain.exists():
            close_domain = close_domain[0]
            if ta.exists():
                ta = ta.first()
                ta.end = timezone.now()
                ta.save()
            close_domain.closed = timezone.now()
            close_domain.save()

        if ('https://goo.gl/' not in url and 'hindsite-local' not in url and
                'hindsite-production' not in url and 'chrome://' not in url and
                'file:///' not in url and 'chrome-extension://' not in url):
            created = False
            if t_id != prev_tab:
                prev_t = Tab.objects.filter(tab_id=prev_tab, closed__isnull=True, owned_by=user)
                if prev_t.exists():
                    prev_t = prev_t.first()
                    prev_d = prev_t.domain_set.filter(closed__isnull=True)
                    if prev_d.exists():
                        prev_d = prev_d.first()
                        d = Domain(
                            title=domain_title, tab=t, base_url=base_url,
                            favicon=favicon, opened_from_domain=prev_d,
                            opened_from_tabid=prev_tab, owned_by=user
                            )
                        d.save()
                        created = True

            if not created:
                d = Domain(title=domain_title, tab=t, base_url=base_url, favicon=favicon, owned_by=user)
                d.save()
            if active:
                new_ta = TimeActive(owned_by=user)
                new_ta.save()
                d.active_times.add(new_ta)
        else:
            return False

    short_url = shorten_url(url)

    p = Page.objects.filter(url=short_url, owned_by=user)

    if p.exists():
        p = p[0]
        if p.title != page_title:
            p.title = page_title
            p.save()
    else:
        p = Page(title=page_title, url=short_url, domain=base_url, owned_by=user)
        p.save()

    pv = PageVisit(page=p, domain=d, owned_by=user)

    session = user.session_set.filter(active=True)

    if session.exists():
        session = session.first()
        if session.end:
            if session.end < timezone.now():
                pv.session = session
            else:
                session.active = False
                session.save()
        else:
            pv.session = session

    pv.save()

    if len(html) > 0:
        aws_loc = str(user.pk) + '/' + str(pv.pk) + '.html'

        # No encryption
        # settings.S3_CLIENT.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        #                             Key=aws_loc, Body=html, ContentType='text/html')

        # Encryption
        settings.S3_CLIENT.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                                    Key=aws_loc, Body=html, SSECustomerKey=user.key,
                                    SSECustomerAlgorithm='AES256', ContentType='text/html')

        pv.s3 = settings.AWS_BUCKET_URL + aws_loc
        pv.save()

    content = strip_tags(html)

    data = create_data(pv, content)

    uri = settings.SEARCH_BASE_URI + 'pagevisits/pagevisit/' + str(pv.id)

    requests.put(uri, data=data)

    user.word_count = json.dumps(Counter(json.loads(user.word_count)) + get_count(content))
    user.save()

    return True


@periodic_task(run_every=(crontab(hour="7", minute="0", day_of_week="*")),
    ignore_result=True)
def clean_up_db():
    tw = timezone.now() - timedelta(days=14)
    first = round(PageVisit.objects.filter(Q(visited__lte=tw)).first().pk/10)
    last = round(PageVisit.objects.filter(Q(visited__lte=tw)).last().pk/10) - 1

    for i in range(first, last):
        pvs = PageVisit.objects.filter(pk__in=range(i*10, (i+1)*10))

        for pv in pvs:

            data = create_data(pv, '')

            uri = settings.SEARCH_BASE_URI + 'pagevisits/pagevisit/' + str(pv.id)

            requests.put(uri, data=data)

            # if (pv.page.pagevisit_set
            #     .exclude(s3='https://s3.us-east-2.amazonaws.com/hindsite-production/404_not_found.html')
            #     .count() > 1):
            #     aws_loc = str(user.pk) + '/' + str(pv.pk) + '.html'
            #
            #     settings.S3_CLIENT.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=aws_loc)
            #
            #     pv.s3 = 'https://s3.us-east-2.amazonaws.com/hindsite-production/404_not_found.html'

            pv.save()

    # for user in CustomUser.objects.all():
    #     for pv in user.pagevisit_set.filter(Q(visited__lte=tw)).exclude(html=''):
    #        
    #
    #         data = create_data(pv, '')
    #
    #         uri = settings.SEARCH_BASE_URI + 'pagevisits/pagevisit/' + str(pv.id)
    #
    #         requests.put(uri, data=data)


    return True


@periodic_task(run_every=(crontab(hour="9", minute="0", day_of_week="*")),
    ignore_result=True)
def analytics():
    for user in CustomUser.objects.all():
        count = Counter(json.loads(user.word_count))
        sort = sorted(count.items(), key=operator.itemgetter(1))
        sort.reverse()

        if len(sort) > 100:
            sort = sort[0:100]
        user.top_100_words = json.dumps(dict(sort))
        user.word_count = '{}'

        day = timezone.now() - timedelta(days=1)
        week = timezone.now() - timedelta(days=7)

        day_count = Counter(user.page_set.filter(Q(pagevisit__visited__gte=day)))
        week_count = Counter(user.page_set.filter(Q(pagevisit__visited__gte=week)))

        day_sort = sorted(day_count.items(), key=operator.itemgetter(1))
        day_sort.reverse()
        week_sort = sorted(week_count.items(), key=operator.itemgetter(1))
        week_sort.reverse()

        if len(day_sort) > 10:
            day_ten = day_sort[0:10]
        else:
            day_ten = day_sort

        if len(week_sort) > 10:
            week_ten = week_sort[0:10]
        else:
            week_ten = week_sort

        user.pages_day = json.dumps({c[0].pk: c[1] for c in day_ten})
        user.pages_week = json.dumps({c[0].pk: c[1] for c in week_ten})

        user.save()
