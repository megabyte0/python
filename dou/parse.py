from crawl import Db as CrawlDb
import re
from collections import Counter, defaultdict


class Db(CrawlDb):
    def get_last_crawl(self):
        id = self.get_max_crawl_id()
        return self.execute_select(
            'select * from crawled where crawl_id = %s',
            id
        )

    def insert(self, table, fields, data):
        if not data:
            return
        sql = (
            'insert into %s (%s) values %s'
        )%(
            table,
            ', '.join(
                '`%s`'%field
                for field in fields
            ),
            ','.join([
                         '(%s)'%(
                             ','.join(['%s']*len(fields))
                         )
                     ]*len(data)
                     )
        )
        cursor = self.get_cursor()
        cursor.execute(sql, tuple(
            i[field]
            for i in data
            for field in fields
        ))
        self.connection.commit()

    def insert_companies(self, data):
        fields = ['slug', 'company', 'img']
        companies_having = self.execute_select(
            'select * from company',
        )
        slugs_to_insert = set(
            i['slug']
            for i in data
        ) - set(
            i['slug']
            for i in companies_having
        )
        data_to_insert = [
            i
            for i in data
            if i['slug'] in slugs_to_insert
        ]
        self.insert('company', fields, data_to_insert)

    def insert_vacancy_crawl(self, data):
        fields = [
            'id',
            'crawl_id',
            'date',
            'slug',
            'title',
            'descr',
        ]
        assert all(
            field in i
            for i in data
            for field in fields
        )
        data = [
            {
                k:(convert_date(v) if k == 'date' else v)
                for k,v in i.items()
            }
            for i in data
        ]
        self.insert('vacancy_crawl', fields, data)

    def insert_vacancies(self, ids):
        having = self.execute_select(
            'select `id` from vacancy',
        )
        having_ids = set(
            i['id']
            for i in having
        )
        ids = set(ids) - having_ids
        self.insert('vacancy', ['id'], [
            {'id': id}
            for id in ids
        ])

matcher = re.compile(
    r'(?sm)'
    r'<li class="l-vacancy(?: __hot)?">'
    r'\s*'
    r'<div class="date">(?P<date>\d+ (?:марта|февраля|января))</div>'
    r'\s*'
    r'<div class="title">'
    r'\s*'
        r'<a class="vt" href="https://jobs.dou.ua/companies/(?P<slug>[-a-z0-9_Z]+)/vacancies/(?P<id>\d+)/(?:\?from=list_hot)?"'
            r'\s*'
        r'>'
        r'(?P<title>.*?)'
        r'</a>'
        r'&nbsp;'
        r'<strong>'
            r'в&nbsp;<a\s*class="company" href="https://jobs.dou.ua/companies/(?P=slug)/vacancies/"\s*>'
            r'(?:'
                r'<img alt="" class="f-i" src="https://s.dou.ua/img/static/favicons/'
                    r'(?P<img>'
                        # r'(?:|u|me|n|Фавикон|ak_|b|int|q|sh|a|v|t|g|32x|f|favicon-|h|l|k|pr-|P_|s|d|3|4b|8|ab|favicon-32x|an|ap|att|br|bro|c|cd|co|cp|cr|cropped-Logo-32x|cropped-icon-32x|cs|dc|deep-favicon-32x|dev|developex|do|dph_|ds|dw|e|eleks)32(?:_[A-Za-z0-9]+)?\.(?:png|jpg|jpeg)'
                        # r'|dou-fav_QGBWYJH_sLNlZ9M_MvR0Ctt_VZczkhq_r69vfaa_eZ9fUfX\.jpg' #dou
                        # r'|nc_2x\.png' #ncube
                        # r'|IMG_20240712_114249_733\.png' #genesis
                        # r'|Mythical_Logo_\.png'
                        # r'|mast\.png' #master of code global
                        # r'|HYS32\.png'
                        # r'|A\.png' #adaptiq
                        # r'|1123\.png' #SeoProfy
                        # r'|123\.png' #Nasctech
                        # r'|1652648577272-Svit_One_icon_logo_256\.png' #Svit.One
                        r'[-0-9A-Za-z_Фавиконх]+\.(?:png|jpg|jpeg|svg)'
                    r')'
                r'">'
                r'&nbsp;'
            r')?'
                '(?P<company>.*?)</a>'
        r'</strong>'
            r'(?:'
                r'\s*'
                r'<span class="salary">.*?</span>'
            r')?'
            r'\s*'
        r'<span class="cities">(?:.*?)</span>'
    r'\s*'
    r'</div>'
    r'\s*'
    r'<div class="sh-info">'
    r'\s*'
    r'(?P<descr>.*?)'
    r'\s*'
    r'</div>'
    r'\s*'
    r'</li>'
)

fields = [
    'date',
    'slug',
    'id',
    'title',
    'img',
    'company',
    'descr',
]

def convert_date(s):
    day, month = s.split(' ')
    months = {
        'января': (1, 31),
        'февраля': (2, 28),
        'марта': (3, 31),
    }
    day = int(day)
    assert month in months
    month, max_day_month = months[month]
    assert 1 <= day <= max_day_month
    year = 2025
    return '%04d-%02d-%02d' % (year, month, day)

if __name__ == '__main__':
    db = Db()
    last_crawl = db.get_last_crawl()
    d = {
        i['counter_start']: i['data']
        for i in last_crawl
    }
    for k, res_data in d.items():
        # print(repr(data))
        x = matcher.split(res_data)
        b1 = len(x) % 8 == 1
        b2 = all(i.strip() == '' for i in (
            x[0::8] if k != 0 else x[8:-1:8]
        ))

        if not (b1 and b2):
            print('\n'.join(
                repr(i)
                for i in x
            ))
            assert False

    items = []
    for crawled in last_crawl:
        x = matcher.split(crawled['data'])
        for index in range(1, len(x) - 1, 8):
            item = dict(zip(fields, x[index:index + 7]))
            item['crawl_id'] = crawled['id']
            items.append(item)

    if any(
            item['company'].startswith('<img')
            for item in items
    ):
        print('\n'.join(sorted(set(
            item['company']
            for item in items
            if item['company'].startswith('<img')
        ))))
        assert False

    assert max(Counter(item['id'] for item in items).values()) == 1
    excluded_companies = [
        {
            'slug': 'jatapp',
            'company': 'JATAPP',
            'img': 'j32_4D7hJ0a.png',
        },
    ]
    companies = defaultdict(set)
    for item in items:
        if {
            k:v
            for k, v in item.items()
            if k in ('slug', 'company', 'img')
        } in excluded_companies:
            continue
        companies[item['slug']].add((
            item['slug'],
            item['company'],
            item['img'],
        ))
    if not all(
            len(v) == 1
            for v in companies.values()
    ):
        print({
            k:v
            for k, v in companies.items()
            if len(v) != 1
        })
        assert False
    field_max_len = {field: max(item[field] and len(item[field]) or 0 for item in items) for field in fields}
    print(field_max_len)
    field_max_len_db = {'slug': 50, 'title': 203, 'img': 59, 'company': 54, 'descr': 294}
    assert all(
        field_max_len[k] <= v
        for k, v in field_max_len_db.items()
    )

    companies_set_frozenset = set(
        frozenset(j.items())
        for j in (
                {
                    k: i[k]
                    for k in ['slug', 'company', 'img']
                }
                for i in items
        )
        if j not in excluded_companies
    )
    db.insert_companies([dict(i) for i in companies_set_frozenset])
    db.insert_vacancy_crawl(items)
    db.insert_vacancies([int(i['id']) for i in items])
    db.close()
