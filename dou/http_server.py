import json

import my_http_server
from http import HTTPStatus
from crawl import Crawler
from html_parser import parse, walk


class HTTPRequestHandler(my_http_server.MyHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.crawler = Crawler()
        super().__init__(*args, **kwargs)

    def register_routes(self):
        self.register_route(r'^/api/ids/?$', self.get_ids)
        self.register_route(r'^/api/vacancies/((?:\d+,)*\d+)$', self.get_vacancies)
        self.register_route(r'^/api/(score|like|done)/(\d+)/(\d+)$', self.update)
        self.register_route(r'^/api/redirect/(\d+)/?$', self.redirect)
        self.register_route(r'^/api/vacancy/(\d+)/?$', self.get_vacancy)
        self.register_route(r'^/api/log_error/?$', self.log_error_)
        self.register_route(r'^/api/stats/?$', self.get_stats)

    def get_ids(self, match, sql_connection, cursor):
        sql = (
            'select '
            '    vacancy.id '
            #'    vacancy.score, '
            #'    vacancy.`like`, '
            #'    vacancy.done, '
            #'    vacancy_crawl.title, '
            #'    vacancy_crawl.descr '
            'from vacancy '
            'inner join vacancy_crawl '
            'on vacancy_crawl.id = vacancy.id '
            'inner join crawled '
            'on crawled.id = vacancy_crawl.crawl_id '
            'and crawled.crawl_id = (select max(crawl_id) from crawled) '
            
            'order by '
            'vacancy.score is not null, '
            'coalesce(`score` = 0, 0), '
            'not (coalesce(`like`,0) and not coalesce(`done`,0)), '
            '(coalesce(`like`,0) and coalesce(`done`,0)), '
            '-vacancy.score'
        )
        cursor.execute(sql)
        ids = [i['id'] for i in cursor.fetchall()]
        return self.send_response_headers_json(ids)

    def get_vacancies(self, match, sql_connection, cursor):
        ids = [
            int(i)
            for i in match.group(1).split(',')
        ]
        sql = (
            'select '
            '    vacancy.id, '
            '    vacancy.score, '
            '    vacancy.`like`, '
            '    vacancy.done, '
            '    vacancy_crawl.title, '
            '    vacancy_crawl.descr '
            'from vacancy '
            'inner join vacancy_crawl '
            'on vacancy_crawl.id = vacancy.id '
            'inner join crawled '
            'on crawled.id = vacancy_crawl.crawl_id '
            'and crawled.crawl_id = (select max(crawl_id) from crawled) '
            'where vacancy.id in (%s)'
        )%(', '.join(['%s']*len(ids)))
        cursor.execute(sql, tuple(ids))
        data = cursor.fetchall()
        data = sorted(data, key=lambda i: ids.index(i['id']))
        return self.send_response_headers_json(data)

    def update(self, match, sql_connection, cursor):
        field = match.group(1)
        id_ = int(match.group(2))
        value = match.group(3)
        sql = (
            'update vacancy '
            'set vacancy.`%s` = %%s '
            'where vacancy.id = %%s'
        ) % (field)
        cursor.execute(sql, (value, id_))
        sql_connection.commit()
        return self.no_content(match, sql_connection, cursor)

    def redirect(self, match, sql_connection, cursor):
        id_ = int(match.group(1))
        item = self.get_vacancy_item_for_url(id_, cursor)
        url = self.vacancy_item_to_url(item)
        if url is None:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            return
        self.send_response(HTTPStatus.MOVED_PERMANENTLY)
        self.send_header("Location",url)
        self.end_headers()
        return

    def get_vacancy_item_for_url(self, id_, cursor):
        sql = (
            'select '
            '    vacancy_crawl.id, '
            '    vacancy_crawl.slug '
            'from  vacancy_crawl '
            'inner join crawled '
            'on crawled.id = vacancy_crawl.crawl_id '
            'and crawled.crawl_id = (select max(crawl_id) from crawled) '
            'where vacancy_crawl.id = %s'
        )
        cursor.execute(sql, (id_,))
        res = cursor.fetchall()
        if not res:
            item = None
        else:
            item = res[0]
        return item

    def vacancy_item_to_url(self, item):
        if item is None:
            return None
        return 'https://jobs.dou.ua/companies/%s/vacancies/%d/' % (item['slug'], item['id'])

    def get_vacancy(self, match, sql_connection, cursor):
        id_ = int(match.group(1))
        item = self.get_db_vacancy(cursor, id_)
        if item is not None:
            res = json.loads(item['data'])
            return self.send_response_headers_json(res)

        item = self.get_vacancy_item_for_url(id_, cursor)
        assert (
                item
                and isinstance(item,dict)
                and all(i in item for i in ('slug', 'id'))
        )
        url = self.vacancy_item_to_url(item)
        data = self.crawler.process('/vacancies/?remote', url=url)
        tags = parse(data)
        res = walk(tags, {'tag': 'div', 'attrs': {'class': 'b-typo vacancy-section'}})
        if res:
            parsed = res[-1][-1]
        else:
            parsed = None
        item.update({
            'url': url,
            'html': data,
            'data': parsed,
        })
        self.insert_db_vacancy(item, sql_connection, cursor)
        sql_connection.commit()
        return self.send_response_headers_json(parsed)

    def get_db_vacancy(self, cursor, id_):
        sql = (
            'select * '
            'from vacancy_crawled '
            'where id = %s '
            'and crawl_time = (select max(crawl_time) from vacancy_crawled where id = %s)'
        )
        cursor.execute(sql, (id_,)*2)
        data = cursor.fetchall()
        if not data:
            return None
        return data[0]

    def insert_db_vacancy(self, item, sql_connection, cursor):
        sql = (
            'insert into vacancy_crawled (id, slug, url, html, data) '
            'values (%s, %s, %s, %s, %s)'
        )
        cursor.execute(sql, (item['id'], item['slug'], item['url'], item['html'], json.dumps(item['data'])))

    def log_error_(self, match, sql_connection, cursor):
        s = self.rfile.read(int(self.headers['Content-Length']))
        print(s)
        return self.no_content(match, sql_connection, cursor)

    def get_stats(self, match, sql_connection, cursor):
        sql = {
            'good':(
                'select count(*) as c from vacancy '
                'where (score >= 7 or `like`) and (not `done` or `done` is null)'
            ),
            'seen':(
                'select count(*) as c from vacancy '
                'where score is not null'
            ),
            'last_crawl':(
                'select count(*) as c from vacancy_crawl '
                'join crawled '
                'on crawled.id = vacancy_crawl.crawl_id '
                'where crawled.crawl_id = (select max(crawl_id) from crawled)'
            ),
        }
        res = {}
        for key, sql_query in sql.items():
            cursor.execute(sql_query)
            data = cursor.fetchall()
            if not data:
                res[key] = None
            res[key] = data[0]['c']
        return self.send_response_headers_json(res)


if __name__ == '__main__':
    my_http_server.run(HTTPRequestHandler, {
        'user': 'root',
        'password': '12345678',
        'database': 'dou',
        'port': 3306,
    })
