import http.server
import socketserver #ThreadingTCPServer
from http import HTTPStatus
import sys #getfilesystemencoding()
import io #BytesIO()
import re
import json
import mysql.connector
import os
import os.path
import gzip

import urllib.parse, email.utils, datetime

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.routes = []
        self.register_routes()
        self.do_POST = self.do_GET
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Serve a GET request."""
        f=self.route()
        if f==False:
            f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def send_response_headers(self,data,
                              content_type=None,
                              status=None,
                              #headers={},
                              gzip_output=False):
        if not isinstance(data,list):
            r=[data]
        else:
            r=data
        enc = sys.getfilesystemencoding()
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        if gzip_output:
            encoded=gzip.compress(encoded)
            headers={'Content-Encoding':'gzip'}
        else:
            headers={}
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        headers['Access-Control-Allow-Origin']='*'#
        self.send_response(status or HTTPStatus.OK)
        for k,v in headers.items():
            self.send_header(k,v)
        self.send_header("Content-type",
                         ("%s; charset=%s" %
                          (content_type or "text/html", enc)))
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

    def register_route(self,route,handler):
        self.routes.append((re.compile(route),handler))

    def route(self):
        global sql_connection
        for matcher,handler in self.routes:
            match=matcher.match(self.path)
            if match:
                try:
                    return handler(match)
                except mysql.connector.errors.OperationalError:
                    sql_connection=obtain_sql_connection()
                    return handler(match)
        return False

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        # check for trailing "/" which should return 404. See Issue17324
        # The test for this was added in test_httpserver.py
        # However, some OS platforms accept a trailingSlash as a filename
        # See discussion on python-dev and Issue34711 regarding
        # parseing and rejection of filenames with a trailing slash
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            # Use browser cache if possible
            if ("If-Modified-Since" in self.headers
                    and "If-None-Match" not in self.headers):
                # compare If-Modified-Since and time of last file modification
                try:
                    ims = email.utils.parsedate_to_datetime(
                        self.headers["If-Modified-Since"])
                except (TypeError, IndexError, OverflowError, ValueError):
                    # ignore ill-formed values
                    pass
                else:
                    if ims.tzinfo is None:
                        # obsolete format with no timezone, cf.
                        # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        # compare to UTC datetime of last modification
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc)
                        # remove microseconds, like in If-Modified-Since
                        last_modif = last_modif.replace(microsecond=0)

                        if last_modif == ims: #the only thing changed
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            f.close()
                            return None

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified",
                self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def register_routes(self):
        pass
##        self.register_route(r'^/api/page/(\d+)$',self.get_page)
##        self.register_route(r'^/api/(like|done)/(\d+)/(\d+)$',self.store_like)
##        self.register_route(r'^/api/times/0\.(\d+)$',self.store_times)
##        self.register_route(r'^/api/redirect/(\d+)$',self.redirect)
##        self.register_route(r'^/api/rate/(\d+)/(\d+)$',self.store_rate)
##        self.register_route(r'^/api/hidden$',self.get_hidden)
##        self.register_route(r'^/api/vacancy/(\d+)$',self.get_vacancy)
##        self.register_route(r'^/api/parsed/(\d+)$',self.get_page_parsed)
##        self.register_route(r'^/api/rates$',self.get_likeness)
##        self.register_route(r'^/api/experience$',self.get_experience)
##        self.register_route(r'^/api/experience/store$',self.store_experience)
##        self.register_route(r'^/api/stats$',self.get_stats)
##        self.register_route(r'^/api/pages$',self.get_pages)

    def send_response_headers_json(self,data,status=None,gzip=False):
        data_json=json.dumps(data)
        #application/json; charset=UTF-8
        return self.send_response_headers(
            data_json,'application/json',status,gzip_output=gzip
            )

    def no_content(self,match):
        #print(self.rfile.read())
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()
        return

    def redirect(self,match):
##        global sql_connection,store_action_sql
##        vacancy_id = match.group(1)
##        cursor = sql_connection.cursor(buffered=True)
##        cursor.execute(store_action_sql('hit'),(vacancy_id,'1','1'))
##        sql_connection.commit()
##        cursor.close()
        self.send_response(HTTPStatus.MOVED_PERMANENTLY)
        url = "https://example.com"
        self.send_header("Location",url)
        self.end_headers()
        return

def run(HTTPRequestHandler,connection_init_dict):
    global sql_connection, obtain_sql_connection

    PORT = 8000

##    Handler = http.server.SimpleHTTPRequestHandler
    
    Handler = HTTPRequestHandler

    sql_connection=(obtain_sql_connection:=lambda:(
        mysql.connector.connect(
            #user='root', password='12345678', database='work'
            **connection_init_dict
            )
    ))()

    #mysql.connector.errors.OperationalError

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
