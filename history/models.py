from django.db import models
from django.db.models import Q
from django.utils import timezone
import math


class Category(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=50)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('created',)

class TimeActive(models.Model):
    start = models.DateTimeField(auto_now_add=True)
    end = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('start',)

class Tab(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    tab_id = models.IntegerField()
    closed = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.tab_id)

    class Meta:
        ordering = ('created',)

class Domain(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=1000)
    base_url = models.CharField(max_length=1000)
    favicon = models.CharField(max_length=1000, blank=True, default='')
    tab = models.ForeignKey('Tab')
    closed = models.DateTimeField(blank=True, null=True)
    active_times = models.ManyToManyField(TimeActive, blank=True)
    opened_from_domain = models.ForeignKey('self', blank=True, null=True)
    opened_from_tabid = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.title

    @property
    def pagecount(self):
        return self.pagevisit_set.count()

    def timeactive(self, start=None, end=None):
        minutes_active = 0

        if start is None or end is None:
            ta = self.active_times.all()

            for a in ta:
                if a.end is not None:
                    time = a.end - a.start
                else:
                    time = timezone.now() - a.start
                minutes_active += math.ceil(time.seconds / 60)
        else:
            ta = self.active_times.filter(Q(start__range=[start, end]) |
                                          Q(end__range=[start, end]))

            for a in ta:
                if a.start < start:
                    time = a.end - start
                elif a.end is None or a.end > end:
                    time = end - a.start
                else:
                    time = a.end - a.start
                minutes_active += math.ceil(time.seconds / 60)

        return (minutes_active, ta)

    class Meta:
        ordering = ('created',)

class Page(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100)
    url = models.CharField(max_length=1000)
    star = models.BooleanField(blank=True, default=False)
    categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('created',)

class PageVisit(models.Model):
    visited = models.DateTimeField(auto_now_add=True)
    page = models.ForeignKey('Page')
    domain = models.ForeignKey('Domain')

    class Meta:
        ordering = ('visited',)