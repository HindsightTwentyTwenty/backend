from search.common import datetime_formatter
from bs4 import BeautifulSoup
import re
from collections import Counter
from authentication.models import CustomUser
import operator
from hindsite.constants import ignore_words

def shorten_url(url):
    import requests
    import json

    google_url = 'https://www.googleapis.com/urlshortener/v1/url?key=AIzaSyAyNJpylrKrx1dy2iss__bSshi2W-nl77c'
    data = {'longUrl': url}
    headers = {'Content-Type': 'application/json'}

    resp = requests.post(google_url, data=json.dumps(data), headers=headers)
    if resp.ok:
        return resp.json()['id']
    else:
        return url

def strip_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    content = ''

    for a in soup.find_all(['div','a', 'p', 'title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'li', 'ol', 'span', 'strong', 'td', 'th']):
            for s in a.strings:
                if (s.find('function(')==-1 and s.find('image/jpeg')==-1 and
                        s.find('image/png')==-1 and s.find('image/jpg')==-1 and
                        s.find('image/gif')==-1 and s.find('{')==-1 and
                        s.find('document.get')==-1 and s.find('<')==-1 and
                        s.find('>')==-1):
                    content += s + ' '

    content = content.replace('\\n', ' ').replace("\n", ' ').replace("\\'", "'").replace("\'", "'").replace("\\t", " ").replace("\\r", ' ').replace('*', ' ')
    content = content.replace('. ', ' ').replace(',', '').replace('"', '').replace('!', '').replace('?', '').replace('(', '').replace(')', '').replace(':', '')
    content = content.replace(';', '').replace('[', '').replace(']', '').replace('.', '')
    content = re.sub(r'[^\x00-\x7F]+',' ', content)

    return content

def get_count(content):
    content = content.lower().split()
    slim_sum = [word for word in content if word not in ignore_words]
    counts = Counter(slim_sum)

    return counts

def create_data(pv, content):
    import json

    return json.dumps({
        "user_id": pv.owned_by.id,
        "title": pv.page.title,
        "html": content,
        "date": datetime_formatter(pv.visited)
    })

def create_action(pv):
    import json

    return json.dumps({
        "index": {
            "_index" : pv._meta.verbose_name_plural, "_type": pv._meta.verbose_name, "_id": str(pv.id)
        }
    })

def create_bulk(pvs):
    data = ''

    for pv in pvs:
        data += create_action(pv) + '\n' + create_data(pv) + '\n'

    return data

def send_bulk(pvs):
    from django.conf import settings
    import requests
    import json

    uri = settings.SEARCH_BASE_URI + '_bulk/'

    data = create_bulk(pvs)

    response = requests.post(uri, data=data)
    results = json.loads(response.text)
    return results


def is_blacklisted(user, domain):

    blacklist = []

    for b in user.blacklist_set.all():
        blacklist.append(b.base_url)
        if b.base_url.startswith('www.'):
            blacklist.append(b.base_url[4:])

    return domain in blacklist

def blacklist(user):
    blacklist = []

    for b in user.blacklist_set.all():
        blacklist.append(b.base_url)
        if b.base_url.startswith('www.'):
            blacklist.append(b.base_url[4:])

    return blacklist

def update_stats(user, pv):
    import json

    admin = CustomUser.objects.get(email='admin@hindsitehistory.com')

    day = user.day_set.last()
    pages = json.loads(day.pages)
    domains = json.loads(day.domains)

    admin_day = admin.day_set.get(date=day.date)
    admin_domains = json.loads(admin_day.domains)

    if str(pv.page_id) in pages.keys():
        pages[str(pv.page_id)] += 1
    else:
        pages[str(pv.page_id)] = 1

    if pv.domain.base_url in domains.keys():
        domains[pv.domain.base_url] += 1
    else:
        domains[pv.domain.base_url] = 1

    if pv.domain.base_url in admin_domains.keys():
        admin_domains[pv.domain.base_url] += 1
    else:
        admin_domains[pv.domain.base_url] = 1

    day.pages = json.dumps(pages)
    day.domains = json.dumps(domains)
    day.save()

    admin_day.domains = json.dumps(admin_domains)
    admin_day.save()

def update_timeactive_stats(d):
    import ast

    user = d.owned_by

    procr_sites = ast.literal_eval(user.procrastination_sites)

    day = user.day_set.last()

    if d.base_url in procr_sites:
        day.procrastination_mins = day.procrastination_mins + d.timeactive()[0]
        day.save()
        return True
    else:
        for p in procr_sites:
            if d.base_url in p:
                day.procrastination_mins = day.procrastination_mins + d.timeactive()[0]
                day.save()
                return True

    day.productivity_mins = day.productivity_mins + d.timeactive()[0]
    day.save()

    return False

def calc_cat_score(cats, page, checked):
    import json
    page_keywords = json.loads(page.keywords)
    scored_cats = []
    ranked_cats = {}
    empty_cats = []

    #TODO- check if empty
    for cat in cats:
        score = 0
        cat_keywords = json.loads(cat.keywords)
        if not cat_keywords:
            empty_cats.append(cat)
        else:
            if cat not in checked:
                for word in page_keywords.keys():
                    if word in cat_keywords.keys():
                        avg = cat_keywords[word] / cat.num_pages
                        score += abs(avg - page_keywords[word])
            ranked_cats[cat] = score

    sorted_cats = sorted(ranked_cats.items(), key=operator.itemgetter(1))

    for c in checked:
        scored_cats.append(c)
    for c in sorted_cats:
        scored_cats.append(c[0])
    for c in empty_cats:
        scored_cats.append(c)

    return scored_cats
