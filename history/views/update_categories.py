from history.models import Page, Category, TimeActive
from history.serializers import PageSerializer, CategorySerializer, PageInfoSerializer
from django.http import Http404
from urllib.parse import urlparse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from history.common import shorten_url, send_bulk, is_blacklisted
import requests
import json
from collections import Counter

class CheckPageCategories(APIView):
    """
    Return categories and starred for a page
    """
    def post(self, request, format=None):
        url = request.data['url']

        url = request.data['url']
        base_url = urlparse(url).netloc

        if is_blacklisted(request.user, base_url):
            return Response({
                'status': 'Blacklist',
                'message': 'This page is blacklisted.'
            }, status=status.HTTP_204_NO_CONTENT)

        short_url = shorten_url(url)

        try:
            p = Page.objects.get(url=short_url, owned_by=request.user)
        except Page.DoesNotExist:
            raise Http404

        page = PageSerializer(p)

        return Response(page.data)

class ActivePageCategories(APIView):
    """
    Return categories and starred for a page
    """
    def get(self, request, format=None):

        try:
            ta = TimeActive.objects.get(end__isnull=True, owned_by=request.user)
        except TimeActive.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)

        p = ta.domain_set.first().pagevisit_set.last().page

        page = PageSerializer(p)

        return Response(page.data)


class AddCategoryPage(APIView):
    """
    Add Category to Page
    """
    def post(self, request, format=None):
        cat = request.data['category']
        url = request.data['url']

        if 'color' in request.data.keys():
            color = request.data['color']
        else:
            color = '#F8A055'

        short_url = shorten_url(url)

        try:
            p = Page.objects.get(url=short_url, owned_by=request.user)
        except Page.DoesNotExist:
            page_title = request.data['title']

            if page_title == '':
                page_title = 'No Title'

            base_url = urlparse(url).netloc

            p = Page(title=page_title, url=short_url, domain=base_url, owned_by=request.user)
            p.save()

        c = Category.objects.filter(title__iexact=cat, owned_by=request.user)

        if c.exists():
            p.categories.add(c.first())
        else:
            c = Category(title=cat, owned_by=request.user, color=color)
            c.save()
            p.categories.add(c)


        #updating keywords
        if p.keywords != '{}':
            cat = c.first()
            page_keywords = Counter(json.loads(p.keywords))
            cat_keywords = Counter(json.loads(cat.keywords))

            new_cat_keywords = page_keywords + cat_keywords
            cat.keywords = json.dumps(new_cat_keywords)
            cat.num_pages = cat.num_pages + 1
            cat.save()


        pv = p.pagevisit_set.last()
        if pv:
            setattr(p, 'last_visited', pv.visited)
            setattr(p, 's3', pv.s3)
            setattr(p, 'preview', pv.preview)
        else:
            setattr(p, 'last_visited', None)
            setattr(p, 's3', 'https://s3.us-east-2.amazonaws.com/hindsite-production/404_not_found.html')
            setattr(p, 'preview', 'https://s3.us-east-2.amazonaws.com/hindsite-production/default-image.jpg')

        serializer = PageInfoSerializer(p)
        return Response(serializer.data)

class DeleteCategoryPage(APIView):
    """
    Delete Category from Page
    """
    def post(self, request, format=None):
        cat = request.data['category']
        url = request.data['url']

        short_url = shorten_url(url)

        try:
            p = Page.objects.get(url=short_url, owned_by=request.user)
        except Page.DoesNotExist:
            raise Http404

        c = Category.objects.get(title=cat, owned_by=request.user)

        p.categories.remove(c)

        #update category keywords
        if p.keywords != '{}':
            page_keywords = Counter(json.loads(p.keywords))
            cat_keywords = Counter(json.loads(c.keywords))

            new_cat_keywords = cat_keywords - page_keywords
            c.keywords = json.dumps(new_cat_keywords)
            c.num_pages = c.num_pages - 1
            c.save()

        pv = p.pagevisit_set.last()
        setattr(p, 'last_visited', pv.visited)
        setattr(p, 's3', pv.s3)
        setattr(p, 'preview', pv.preview)

        serializer = PageInfoSerializer(p)
        return Response(serializer.data)

class AddCategory(APIView):
    """
    Add Category
    """
    def post(self, request, format=None):
        cat = request.data['category']

        if 'color' in request.data.keys():
            color = request.data['color']
        else:
            color = '#F8A055'

        try:
            c = Category.objects.get(title__iexact=cat, owned_by=request.user)
        except Category.DoesNotExist:
            c = Category(title=cat, owned_by=request.user, color=color)
            c.save()

        serializer = CategorySerializer(c)
        return Response(serializer.data)

class DeleteCategory(APIView):
    """
    Delete Category
    """
    def post(self, request, format=None):
        cat = request.data['category']
        try:
            c = Category.objects.get(title=cat, owned_by=request.user)
        except Category.DoesNotExist:
            raise Http404

        c.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class EditCategory(APIView):
    """
    Edit Category
    """
    def post(self, request, format=None):
        old_cat = request.data['old']
        new_cat = request.data['updated']

        try:
            c = Category.objects.get(title=old_cat, owned_by=request.user)
        except Category.DoesNotExist:
            raise Http404

        if 'color' in request.data.keys():
            c.color = request.data['color']

        c.title = new_cat
        c.save()

        serializer = CategorySerializer(c)
        return Response(serializer.data)

class SendCategories(APIView):
    """
    Send all categories for user
    """
    def get(self, request, format=None):
        c = Category.objects.filter(owned_by=request.user)
        serializer = CategorySerializer(c, many=True)
        return Response(serializer.data)

class UpdateStar(APIView):
    """
    Update Page Star
    """
    def post(self, request, format=None):
        url = request.data['url']
        star = request.data['star']

        short_url = shorten_url(url)

        try:
            p = Page.objects.get(url=short_url, owned_by=request.user)
        except Page.DoesNotExist:
            page_title = request.data['title']

            if page_title == '':
                page_title = 'No Title'

            base_url = urlparse(url).netloc

            p = Page(title=page_title, url=short_url, domain=base_url, owned_by=user)

        p.star = star
        p.save()

        serializer = PageSerializer(p)
        return Response(serializer.data)

class UpdateNote(APIView):
    """
    Update Page Note
    """
    def post(self, request, format=None):
        url = request.data['url']
        note = request.data['note']

        short_url = shorten_url(url)

        try:
            p = Page.objects.get(url=short_url, owned_by=request.user)
        except Page.DoesNotExist:
            page_title = request.data['title']

            if page_title == '':
                page_title = 'No Title'

            base_url = urlparse(url).netloc

            p = Page(title=page_title, url=short_url, domain=base_url, owned_by=request.user)
            p.save()

        p.note = note
        p.save()

        pv = p.pagevisit_set.last()
        if pv:
            setattr(p, 'last_visited', pv.visited)
            setattr(p, 's3', pv.s3)
            setattr(p, 'preview', pv.preview)
        else:
            setattr(p, 'last_visited', None)
            setattr(p, 's3', 'https://s3.us-east-2.amazonaws.com/hindsite-production/404_not_found.html')
            setattr(p, 'preview', 'https://s3.us-east-2.amazonaws.com/hindsite-production/default-image.jpg')

        serializer = PageInfoSerializer(p)
        return Response(serializer.data)
