import itertools
import re
import sys

import brotli
import os, os.path
import time
import json
import urllib.request
import mysql.connector
import http.client


class HarStorage:
    def __init__(self):
        self.directory = './har/'
        self.entries = None
        self.latest_har_fn = None

    def get_latest_har_fn(self):
        if self.latest_har_fn is None:
            hars = [
                os.path.join(self.directory, fn)
                for fn in os.listdir(self.directory)
                if fn.endswith('.har')
            ]
            # print([
            #     [
            #         time.ctime(t)
            #         for t in os.stat(full_fn)[-3:]
            #     ]
            #     for full_fn in hars
            # ])
            self.latest_har_fn = max(hars, key=lambda fn: os.stat(fn)[-2])
        return self.latest_har_fn

    def read_har_json(self, fn):
        if self.entries is None:
            with open(fn, 'rt') as fp:
                data = json.load(fp)
            assert 'log' in data
            assert 'entries' in data['log']
            self.entries = data['log']['entries']
        return self.entries

    def filter_entries_by_url(self, entries, url_fn):
        return [
            i
            for i in entries
            if (
                    'request' in i
                    and 'url' in i['request']
                    and isinstance(i['request']['url'], str)
                    and url_fn(i['request']['url'])
            )
        ]

    def process(self, url_fn):
        entries = self.read_har_json(
            self.get_latest_har_fn()
        )
        base_entries = self.filter_entries_by_url(
            entries,
            url_fn
        )
        assert len(base_entries)
        base_entry = base_entries[0]
        return base_entry


class Requester:
    def re_request_har_entry(self, entry, url=None, data=None, cookies=None):
        if cookies is None:
            cookies = {}
        entry_request = entry['request']
        headers = {
            i['name']: i['value']
            for i in entry_request['headers']
            if i['name'] not in ('Host', 'Connection', 'Content-Length')
        }
        har_cookies = dict(
            tuple(i.split('=', 1))
            for i in headers['Cookie'].split('; ')
        )
        har_cookies.update(cookies)
        headers['Cookie'] = '; '.join(
            '%s=%s' % (k, v)
            for k, v in har_cookies.items()
        )
        if isinstance(data, bytes):
            headers['Content-Length'] = len(data)
        req = urllib.request.Request(
            url=url or entry_request['url'],
            data=data,
            method=entry_request['method'],
            headers=headers,
        )
        with urllib.request.urlopen(req) as fp:
            data = fp.read()
        return fp, data

    def decompress(self, fp, data):
        if fp.headers.get('Content-Encoding') == 'br':
            data = brotli.decompress(data)
        return data

    def get_cookies(self, fp):
        headers: http.client.HTTPMessage = fp.headers
        return {
            k: v for (k, v) in [
                i.split('; ', 1)[0].split('=', 1)
                for i in (headers.get_all('Set-Cookie') or [])
            ]
        }


class Db:
    def __init__(self):
        self.connection_dict = {
            'user': 'root',
            'password': '12345678',
            'database': 'dou',
        }
        self.connection = None
        self.cursor = None

    def connect(self):
        if self.connection is None:
            self.connection = mysql.connector.connect(**self.connection_dict)
        return self.connection

    def close(self):
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def get_cursor(self):
        if self.cursor is None:
            self.cursor = self.connect().cursor(buffered=True, dictionary=True)
        return self.cursor

    def execute_select(self, sql, *args):
        cursor = self.get_cursor()
        cursor.execute(sql, args)
        return cursor.fetchall()

    def get_cookies(self):
        return {
            i['key']: i['value']
            for i in self.execute_select(
                'select * from cookie'
            )
        }

    def set_cookies(self, cookies):
        if not cookies:
            return
        cursor = self.get_cursor()
        sql = (
                  'insert into cookie (`key`, `value`) values %s as `new` on duplicate key update `value` = `new`.`value`'
              ) % (', '.join('(%s, %s)' for _ in cookies))
        # print(sql)
        cursor.execute(sql, tuple(
            i
            for k, v in cookies.items()
            for i in (k, v)
        ))
        self.connection.commit()

    def store(self, data, crawl_id, counter_start, counter_end):
        cursor = self.get_cursor()
        sql = (
            'insert into crawled (data, crawl_id, counter_start, counter_end) values (%s, %s, %s, %s)'
        )
        cursor.execute(
            sql,
            (data, crawl_id, counter_start, counter_end)
        )
        self.connection.commit()


    def get_max_crawl_id(self):
        data = self.execute_select(
            'select max(crawl_id) as `max_crawl_id` from crawled'
        )
        assert len(data) == 1
        max_crawl_id = data[0]['max_crawl_id']
        if max_crawl_id is None:
            return 0
        return max_crawl_id

matchers = {
    'token': r'(?m)^\s*window\.CSRF_TOKEN\s*=\s*"([A-Za-z0-9]+)";\s*$',
}
matchers = {
    k: re.compile(v)
    for k, v in matchers.items()
}

class Crawler:
    def __init__(self):
        self.requester = Requester()
        self.db = Db()
        self.har_storage = HarStorage()
        self.cookies = self.db.get_cookies()

    def process(self, url_end, url = None, data = None):
        # global base_entry, fp, res_data, cookies
        base_entry = self.har_storage.process(
            lambda s: s.endswith(url_end)
        )
        # cookies = db.get_cookies()
        # print(cookies)
        # assert False
        fp, res_data = self.requester.re_request_har_entry(base_entry, url=url, data=data, cookies=self.cookies)
        assert fp.status == 200
        self.cookies = self.requester.get_cookies(fp)
        self.db.set_cookies(self.cookies)
        # headers: http.client.HTTPMessage = fp.headers
        # print(fp.status, type(headers), headers.get_all('Set-Cookie'))
        res_data = self.requester.decompress(fp, res_data)
        # with open('./out.html', 'wb') as fp:
        #     fp.write(data)
        res_data = res_data.decode()
        return res_data

if __name__ == '__main__':
    crawler = Crawler()
    # data = crawler.process('/vacancies/?remote', url='https://jobs.dou.ua/companies/sharpminds/vacancies/299188/')
    # assert 'b-typo vacancy-section' in data
    # assert False
    data = crawler.process('/vacancies/?remote')
    tokens = matchers['token'].findall(data)
    assert len(tokens) == 1
    token = tokens[0]
    crawl_id = crawler.db.get_max_crawl_id() + 1
    print(crawl_id, token)
    crawler.db.store(data, crawl_id, 0, 20)

    for start in itertools.count(20, 40):
        req_data = {
            'csrfmiddlewaretoken': token,
            'count': str(start),
        }
        data = crawler.process(
            '/vacancies/xhr-load/?remote=',
            data='&'.join(
                '%s=%s' % (k, v)
                for k, v in req_data.items()
            ).encode(),
        )

        data = json.loads(data)
        assert set(data.keys()) == set(['html', 'last', 'num'])
        crawler.db.store(data['html'], crawl_id, start, start + data['num'])
        print(len(data['html']), data['last'], data['num'], start)
        if data['last']:
            break

    crawler.db.close()
