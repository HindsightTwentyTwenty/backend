from history.models import Tab, Domain, Page, PageVisit, TimeActive, Category
from authentication.models import CustomUser
from django.http import Http404, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import pytz
from django.core import serializers
from history.serializers import (
        SendTabSerializer, SendCategorySerializer,
        SendDomainSerializer, PopupInfoSerializer,
        NewSendCategorySerializer
        )
from authentication.serializers import UserInfoSerializer
from django.db.models.functions import Lower
from history.common import blacklist
from urllib.parse import urlparse
from history.common import shorten_url, send_bulk, is_blacklisted, calc_cat_score
import json


class SendPopupInfo(APIView):
    """
    Return all data for popup
    """
    def post(self, request, format=None):
        cu = request.user

        url = request.data['url']

        base_url = urlparse(url).netloc

        if is_blacklisted(cu, base_url):
            return Response({
                'status': 'Blacklist',
                'message': 'This page is blacklisted.'
            }, status=status.HTTP_201_CREATED)

        short_url = shorten_url(url)

        c = cu.category_set.all()

        holder = {'categories': c, 'tracking': request.user.tracking_on}

        try:
            p = Page.objects.get(url=short_url, owned_by=cu)
        except Page.DoesNotExist:
            holder['page'] = None
            send = PopupInfoSerializer(holder)
            return Response(send.data, status=status.HTTP_404_NOT_FOUND)

        checked = p.categories.all()
        ordered_score = calc_cat_score(c, p, checked)

        holder['categories'] = ordered_score
        holder['page'] = p

        send = PopupInfoSerializer(holder)

        return Response(send.data)

class SendTabs(APIView):
    """
    Send info for lookback page
    """
    def post(self, request, format=None):
        start = request.data['start']
        end = request.data['end']

        start = pytz.utc.localize(datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ'))
        end = pytz.utc.localize(datetime.strptime(end, '%Y-%m-%dT%H:%M:%S.%fZ'))

        #domains open during timeframe
        domains = Domain.objects.filter(owned_by=request.user).filter(
                              Q(created__range=[start, end]) |
                              Q(closed__range=[start, end]) |
                              (Q(closed__gte=end) & Q(created__lte=start)) |
                              (Q(created__lte=start) & Q(closed__isnull=True))
                              )

        # pvs = PageVisit.objects.filter(visited__range=[start, end])

        tabs = set()

        for d in domains:
            tabs.add(d.tab.pk)

        tabs = Tab.objects.filter(pk__in=tabs)

        domains = list(domains)
        holder = {'tabs': []}

        for t in tabs:
            setattr(t, 'domains', [])

            for d in domains:
                if d.tab == t and d not in t.domains:

                    ta = d.timeactive(start, end)

                    setattr(d, 'pages', d.pagecount)
                    setattr(d, 'minutes_active', ta[0])
                    setattr(d, 'active_times', ta[1])

                    pv = (d.pagevisit_set
                        .exclude(preview='https://s3.us-east-2.amazonaws.com/hindsite-production/default-image.jpg'))

                    if pv.exists():
                        setattr(d, 'preview', pv.first().preview)
                    else:
                        setattr(d, 'preview', None)
                    t.domains.append(d)
            holder['tabs'].append(t)

        send = SendTabSerializer(holder)


        return Response(send.data)

class SendCategories(APIView):
    """
    Send categories with their associated pages
    """
    def get(self, request, format=None):
        holder = {'categories': []}

        bl = blacklist(request.user)

        starred = Page.objects.filter(star=True, owned_by=request.user).exclude(domain__in=bl)

        for p in starred:
            pv = p.pagevisit_set.last()
            if pv:
                setattr(p, 'last_visited', pv.visited)
                setattr(p, 's3', pv.s3)
                setattr(p, 'preview', pv.preview)
            else:
                setattr(p, 'last_visited', 'N/A')
                setattr(p, 's3', 'https://s3.us-east-2.amazonaws.com/hindsite-production/404_not_found.html')
                setattr(p, 'preview', 'https://s3.us-east-2.amazonaws.com/hindsite-production/default-image.jpg')

        holder['starred'] = starred

        cats = Category.objects.filter(owned_by=request.user).order_by(Lower('title'))

        for c in cats:
            pages = c.page_set.exclude(domain__in=bl)

            for p in pages:
                pv = p.pagevisit_set.last()
                if pv:
                    setattr(p, 'last_visited', pv.visited)
                    setattr(p, 's3', pv.s3)
                    setattr(p, 'preview', pv.preview)
                else:
                    setattr(p, 'last_visited', 'N/A')
                    setattr(p, 's3', 'https://s3.us-east-2.amazonaws.com/hindsite-production/404_not_found.html')
                    setattr(p, 'preview', 'https://s3.us-east-2.amazonaws.com/hindsite-production/default-image.jpg')

            setattr(c, 'pages', pages)

            holder['categories'].append(c)

        send = SendCategorySerializer(holder)

        return Response(send.data)

class NewSendCategories(APIView):

    def get(self, request, format=None):
        holder = {'categories': []}

        bl = blacklist(request.user)

        page_list = []

        starred = Page.objects.filter(star=True, owned_by=request.user).exclude(domain__in=bl)
        starred_pks = []

        for p in starred:
            cat_pks = []

            for category in p.categories.all():
                cat_pks.append(category.pk)

            pv = p.pagevisit_set.last()
            if pv:
                setattr(p, 'last_visited', pv.visited)
                setattr(p, 's3', pv.s3)
                setattr(p, 'preview', pv.preview)
            else:
                setattr(p, 'last_visited', 'N/A')
                setattr(p, 's3', 'https://s3.us-east-2.amazonaws.com/hindsite-production/404_not_found.html')
                setattr(p, 'preview', 'https://s3.us-east-2.amazonaws.com/hindsite-production/default-image.jpg')
            setattr(p, 'cat_pks', cat_pks)

            page_list.append(p)
            starred_pks.append(p.pk)

        holder['starred'] = starred_pks

        cats = Category.objects.filter(owned_by=request.user).order_by(Lower('title'))

        for c in cats:
            pages = c.page_set.exclude(domain__in=bl)
            page_pks = []
            for p in pages:
                cat_pks = []
                for category in p.categories.all():
                    cat_pks.append(category.pk)

                pv = p.pagevisit_set.last()
                if pv:
                    setattr(p, 'last_visited', pv.visited)
                    setattr(p, 's3', pv.s3)
                    setattr(p, 'preview', pv.preview)
                else:
                    setattr(p, 'last_visited', 'N/A')
                    setattr(p, 's3', 'https://s3.us-east-2.amazonaws.com/hindsite-production/404_not_found.html')
                    setattr(p, 'preview', 'https://s3.us-east-2.amazonaws.com/hindsite-production/default-image.jpg')
                setattr(p, 'cat_pks', cat_pks)

                page_pks.append(p.pk)
                page_list.append(p)

            setattr(c, 'pages', page_pks)

            holder['categories'].append(c)

        holder['pages'] = list(set(page_list))

        send = NewSendCategorySerializer(holder)

        return Response(send.data)

class SendDomain(APIView):
    """
    Send domain and all the pages
    """
    def post(self, request, format=None):
        pk = request.data['pk']

        d = Domain.objects.get(pk=pk, owned_by=request.user)

        pvs = d.pagevisit_set.all().order_by('visited')

        ta = d.timeactive()

        setattr(d, 'pages', d.pagecount)
        setattr(d, 'minutes_active', ta[0])
        setattr(d, 'active_times', ta[1])
        setattr(d, 'pagevisits', pvs)

        send = SendDomainSerializer(d)

        return Response(send.data)

class SendUserData(APIView):
    """
    Send user info
    """
    def get(self, request, format=None):

        cu = request.user

        user = UserInfoSerializer(cu)

        return Response(user.data)
