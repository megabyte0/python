#from my_http_server import MyHTTPRequestHandler, run
import my_http_server
import re
import json
from decimal import Decimal
import datetime

from http import HTTPStatus
import sys #getfilesystemencoding()

class HTTPRequestHandler(my_http_server.MyHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.fields = r'''id
label
task_id
start_at
end_at
finished
exported'''.split('\n')
        super().__init__(*args, **kwargs)
        
    def register_routes(self):
        self.register_route(r'^/api/data/(\d+)?$',self.get_data)
        self.register_route(r'^/api/start/$',
                            self.update(self.start_time_log)
                            )
        self.register_route(r'^/api/stop/(\d+)$',
                            self.update(self.stop_time_log)
                            )
        self.register_route(r'^/api/update/(\d+)?$',
                            self.update(self.update_time_log)
                            )
        self.register_route(r'^/api/test503/$',self.return_503)

    def return_503(self,match):
        self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
        self.send_header('Access-Control-Allow-Origin', '*')
        enc = sys.getfilesystemencoding()
        content_type = None
        self.send_header("Content-type",
                         ("%s; charset=%s" %
                          (content_type or "text/html", enc)))
        self.send_header("Content-Length", '0')
        self.end_headers()
        return

    def get_data(self,match):
        if not match.group(1):
            my_http_server.sql_connection = (
                my_http_server.obtain_sql_connection()
                )
        cursor = my_http_server.sql_connection.cursor(buffered=True)
        if match.group(1):
            _id = int(match.group(1))
        else:
            _id = None
        res = self.get_by_id(cursor,_id)
        cursor.close()
        return self.send_response_headers_json(res,gzip=True)

    def get_input_json(self):
        if "Content-Length" not in self.headers:
            return None
        _len = int(self.headers["Content-Length"])
        data = self.rfile.read(_len)
        data = json.loads(data)
        return data

    def get_by_id(self,cursor,_id=None):
        sql = 'select %s from time_tracking'%(
            ', '.join(self.fields)
            )
        if _id:
            sql+=' where id=%s'
            cursor.execute(sql,(_id,))
        else:
            cursor.execute(sql)
        res = []
        for data in cursor:
            res_item = {
                k:(v if not isinstance(v,datetime.datetime) else repr(v))
                for k,v in zip(self.fields,data)
                }
            res.append(res_item)
        return res

    def update(self,function):
        def res_function(match,function=function):
            new_entry = self.get_input_json()
            if not new_entry:
                new_entry = {}
##                self.send_response_headers_json({'id':None})
##                return
            if match.groups() and match.group(1):
                new_entry['id'] = int(match.group(1))
            fields_present = {
                k:v
                for k,v in new_entry.items()
                if k in self.fields
                and k not in ['id','end_at','start_at','exported']
                }
            _id = new_entry['id'] if 'id' in new_entry else None
            cursor = my_http_server.sql_connection.cursor(buffered=True)
            res = function(cursor,fields_present,_id)
            cursor.close()
            return self.send_response_headers_json(res)
        return res_function

    def start_time_log(self,cursor,record,_id):
        sql = 'insert into time_tracking (%s) values (%s)'%(
            ', '.join(k for k in record),
            ', '.join('%s' for k in record)
            )
        cursor.execute(sql,tuple(record.values()))
        _id = cursor.lastrowid
        my_http_server.sql_connection.commit()
        return self.get_by_id(cursor,_id)

    def stop_time_log(self,cursor,record,_id):
        sql = 'update time_tracking set %s end_at = default where id=%%s'%(
            ''.join('%s = %%s, '%(field) for field in record)
            )
        cursor.execute(sql,tuple(record.values())+(_id,))
        my_http_server.sql_connection.commit()
        return self.get_by_id(cursor,_id)

    def update_time_log(self,cursor,record,_id):
        sql = 'update time_tracking set %s where id=%%s'%(
            ', '.join('%s = %%s'%(field) for field in record)
            )
        cursor.execute(sql,tuple(record.values())+(_id,))
        my_http_server.sql_connection.commit()
        return self.get_by_id(cursor,_id)

    def login(self,match):
        if "Content-Length" in self.headers:
            _len = int(self.headers["Content-Length"])
            data = self.rfile.read(_len)
            data = json.loads(data)
            assert all(i in data for i in ['user','password'])
            sql_select = ('select `id`,`password_md5` from `users` '
                          'where `login` = %s')
            cursor = my_http_server.sql_connection.cursor(buffered=True)
            cursor.execute(sql_select,data['user'])
            passwords = {password:_id for _id,password in cursor}
            if passwords:
                if data['password'] not in passwords:
                    #error
                    pass
                else:
                    user_id = passwords[data['password']]
            else:
                #register
                cursor.execute(
                    ('insert into `users` (`login`, `password_md5`) '
                     'values (%s, %s)'),
                    tuple(data[i] for i in ['user','password']))
                user_id = cursor.lastrowid
            #register session
            with open('/dev/urandom','rb') as fp:
                unique = base64.b64encode(fp.read(24))
            cursor.close()

my_http_server.run(HTTPRequestHandler,{
    'user':'root',
    'password':'12345678',
    'database':'time_tracking',
    #'port':33061,
    })
