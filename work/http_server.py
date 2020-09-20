import http.server
import socketserver
from http import HTTPStatus
import sys
import io
import re
import json
import pickle
import mysql.connector
import os
import os.path

import crawler

PORT = 8000

Handler = http.server.SimpleHTTPRequestHandler

keyword='prog'

class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        #global sql_connection
        self.routes = []
        self.register_routes()
        self.do_POST = self.do_GET
        #self.cnx = sql_connection
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Serve a GET request."""
        #if self.path.startswith('/api/'):
        #    f = self.send_response_headers('api call')
        #else:
        f=self.route()
        if f==False:
            f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def send_response_headers(self,data,content_type=None,status=None):
        if not isinstance(data,list):
            r=[data]
        else:
            r=data
        enc = sys.getfilesystemencoding()
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(status or HTTPStatus.OK)
        self.send_header("Content-type",
                         ("%s; charset=%s" %
                          (content_type or "text/html", enc)))
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

    def register_route(self,route,handler):
        self.routes.append((re.compile(route),handler))

    def route(self):
        for matcher,handler in self.routes:
            match=matcher.match(self.path)
            if match:
                return handler(match)
        return False

    def register_routes(self):
        self.register_route(r'^/api/page/(\d+)$',self.get_page);
        self.register_route(r'^/api/like/(\d+)/(\d+)$',self.store_like);
        self.register_route(r'^/api/times/0\.(\d+)$',self.store_times);
        self.register_route(r'^/api/redirect/(\d+)$',self.redirect);
        self.register_route(r'^/api/rate/(\d+)/(\d+)$',self.store_rate);
        self.register_route(r'^/api/hidden$',self.get_hidden);
        self.register_route(r'^/api/vacancy/(\d+)$',self.get_vacancy);
        self.register_route(r'^/api/parsed/(\d+)$',self.get_page_parsed);
        self.register_route(r'^/api/rates$',self.get_likeness);

    def send_response_headers_json(self,data,status=None):
        data_json=json.dumps(data)
        #application/json; charset=UTF-8
        return self.send_response_headers(data_json,'application/json',status)

    def get_page(self,match):
        global sql_connection,keyword
        cursor = sql_connection.cursor(buffered=True)
        #keyword='common'
        page=match.group(1)
        cursor.execute(
            ('select parsed from pages '
             'where crawl_id = '
             '(select max(crawl_id) from pages '
             'where keyword = %s) '
             'and keyword = %s '
             'and page = %s'),(keyword,keyword,page))
        page=list(cursor)[0][0]
        cursor.close()
        #file_name = 'pages/%s_parsed.pickle'%(match.group(1))
        #if not os.path.exists(file_name):
        if not page:
            return self.no_content(match)
        #with open(file_name,'rb') as fp:
        #    tags=pickle.load(fp)
        tags=json.loads(page)
        return self.send_response_headers_json(tags)

    def store_like(self,match):
        global sql_connection,store_action_sql
        cursor = sql_connection.cursor(buffered=True)
        cursor.execute(store_action_sql('liking'),match.groups()+(match.group(2),))
        sql_connection.commit()
        cursor.close()
        #print(match.groups())
        return self.no_content(match)

    def store_times(self,match):
        global sql_connection
        #print(set(self.headers))
        s=self.rfile.read(int(self.headers['Content-Length']))
        times=json.loads(s)
        session_id=match.group(1)
        sql=('insert into times '
             '(session_id,vacancy_id,ratio,event_time) '
             'values '
            )+(', '.join(['(%s)'%(','.join(['%s']*4))]*len(times)))
        cursor = sql_connection.cursor(buffered=True)
        cursor.execute(sql,tuple(
        i for t in times for i in [session_id]+[t[j] for j in ['id','ratio','time']]
        ))
        sql_connection.commit()
        cursor.close()
        #print(len(times),s[:20],match.group(1))
        return self.no_content(match)

    def no_content(self,match):
        #print(self.rfile.read())
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()
        return

    def redirect(self,match):
        global sql_connection,store_action_sql
        vacancy_id = match.group(1)
        cursor = sql_connection.cursor(buffered=True)
        cursor.execute(store_action_sql('hit'),(vacancy_id,'1','1'))
        sql_connection.commit()
        cursor.close()
        self.send_response(HTTPStatus.MOVED_PERMANENTLY)
        self.send_header("Location","https://www.work.ua/ru/jobs/%s/"%(vacancy_id))
        self.end_headers()
        return

    def store_rate(self,match):
        global sql_connection,store_action_sql,sql_insert_vacancy
        vacancy_id,rate = match.group(1),int(match.group(2))
        cursor = sql_connection.cursor(buffered=True)
        if rate==0:
            cursor.execute(store_action_sql('hide'),(vacancy_id,'1','1'))
            sql_connection.commit()
        cursor.execute(sql_insert_vacancy('likeness'),
                       (vacancy_id,rate/10,rate/10))
        cursor.close()
        sql_connection.commit()
        return self.no_content(match)

    def get_hidden(self,match):
        global sql_connection
        cursor = sql_connection.cursor(buffered=True)
        sql = ('select vacancy_id from actions '
               'where hide')
        cursor.execute(sql)
        hidden = list(cursor)
        cursor.close()
        #sql_connection.commit()
        return self.send_response_headers_json(hidden)

    def get_likeness(self,match):
        global sql_connection
        cursor = sql_connection.cursor(buffered=True)
        sql = ('select id,likeness*10 from vacancy')
        cursor.execute(sql)
        rates = dict(list(cursor))
        cursor.close()
        #sql_connection.commit()
        return self.send_response_headers_json(rates)

    def get_vacancy(self,match):
        global sql_connection,sql_insert_vacancy
        vacancy_id=match.group(1)
        cursor = sql_connection.cursor(buffered=True)
        sql_select = ('select html,parsed from vacancy '
                      'where id = %s')
        cursor.execute(sql_select,(int(vacancy_id),))
        vacancy_list=list(cursor)
        if (vacancy_list):
            s,parsed = vacancy_list[0]
        else:
            s,parsed = None,None
        if parsed:
            parsed=json.loads(parsed)
            cursor.close()
            return self.send_response_headers_json(parsed)
        if not s:
            s=crawler.decode(*(crawler.get_vacancy(vacancy_id)))
            cursor.execute(sql_insert_vacancy('html'),(vacancy_id,s,s))
            sql_connection.commit()
        if not parsed:
            parsed = crawler.parse(s)
            cursor.execute(sql_insert_vacancy('parsed'),
                           (vacancy_id,)+((json.dumps(parsed),)*2))
            sql_connection.commit()
        cursor.close()
        return self.send_response_headers_json(parsed)

    def get_page_parsed(self,match):
##        global sql_connection
##        cursor = sql_connection.cursor(buffered=True)
##        keyword='prog'
        page=match.group(1)
##        cursor.execute(
##            ('select parsed from pages '
##             'where crawl_id = '
##             '(select max(crawl_id) from pages '
##             'where keyword = %s) '
##             'and keyword = %s '
##             'and page = %s'),(keyword,keyword,page))
##        page=list(cursor)[0][0]
##        cursor.close()
        file_name = 'pages/%s_parsed.pickle'%(match.group(1))
        if not os.path.exists(file_name):
        #if not page:
            return self.no_content(match)
        with open(file_name,'rb') as fp:
            tags=pickle.load(fp)
##        tags=json.loads(page)
        filtered_2=crawler.filter_page(tags)
        #walk_text=lambda tag:
        #    ('data' in tag and [tag['data']] or [])+
        #    ('children' in tag and
        #     sum((walk_text(i) for i in tag['children']),[]) or [])
        #salary_matcher=re.compile(r'(?:\d+\s*)+грн')
        return self.send_response_headers_json(filtered_2)


Handler = HTTPRequestHandler

sql_connection=(
    mysql.connector.connect(user='root', password='12345678', database='work')
)

#mysql.connector.errors.OperationalError

sql_insert_vacancy = lambda action:(
'INSERT INTO vacancy (id,%s) VALUES (%%s,%%s) '
'ON DUPLICATE KEY UPDATE %s=%%s'
)%((action,)*2)

store_action_sql = lambda action:(
    'INSERT INTO actions (vacancy_id,%s) VALUES (%%s,%%s) '
    'ON DUPLICATE KEY UPDATE %s=%%s'
    )%((action,)*2)

while PORT<8010:
    try:
        with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
            print("serving at port", PORT)
            httpd.serve_forever()
    except OSError:
        PORT+=1
    except KeyboardInterrupt:
        if sql_connection:
            sql_connection.close()
        raise
