#from my_http_server import MyHTTPRequestHandler, run
import my_http_server
import re
import json
from decimal import Decimal
import datetime
import time

from http import HTTPStatus
import sys #getfilesystemencoding()

from read_time_database_render import (
    slack_history_linear,
    get_slack_history,
    slack_letters_config,
    letter_priority
    )
from read_jetbrains_history import (
    read_jetbrains_history,
    path_to_letter
    )

class HTTPRequestHandler(my_http_server.MyHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.fields = r'''id
label
jira_project
task_id
start_at
end_at
finished
exported'''.split('\n')
        super().__init__(*args, **kwargs)
        
    def register_routes(self):
        self.register_route(r'^/api/data/(\d+)?$',self.get_data)
        self.register_route(
            r'^/api/insert/$',
            self.update(
                self.start_time_log,
                set(['end_at','start_at'])
                )
            )
##        self.register_route(r'^/api/start/$',
##                            self.update(self.start_time_log)
##                            )
##        self.register_route(r'^/api/stop/(\d+)$',
##                            self.update(self.stop_time_log)
##                            )
##        self.register_route(r'^/api/update/(\d+)?$',
##                            self.update(self.update_time_log)
##                            )
##        self.register_route(r'^/api/test503/$',self.return_503)

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
        config = {
            'time_log': (self.get_time_log, [match]),
            'idle_editor_log': (self.get_ide_editor_log,()),
            'slack_messages': (self.get_slack_history_linear,[match]),
            }
        res = {
            k:self.time_it(*v)
            for k,v in config.items()
            }
        return self.send_response_headers_json(res,gzip=True)

    def get_time_log(self,match):
        if True:#not match.group(1):
            my_http_server.sql_connection = (
                my_http_server.obtain_sql_connection()
                )
        cursor = my_http_server.sql_connection.cursor(buffered=True)
        if match.group(1):
            _time = int(match.group(1))
        else:
            _time = None
        res = self.get_log_since(cursor,_time)
        cursor.close()
        return res

    def time_it(self,method,params):
        time_start = time.process_time()
        res = method(*params)
        time_end = time.process_time()
        return {
            'data': res,
            'time': time_end - time_start
            }

    def get_ide_editor_log(self):
        history = read_jetbrains_history()
        return {
            'history': {
                time_ms:{
                    'files':[
                        fn_with_path.decode()
                        for fn_with_path in files_and_letter['files']
                        ],
                    'letter':files_and_letter['letter'],
                    }
                for time_ms,files_and_letter in history.items()
                },
            'path_to_letter': path_to_letter,
            'letter_priority': letter_priority,
            }

    def get_slack_history_linear(self,match):
        if match:
            time_start = int(match.group(1))
        else:
            time_start = None
        history = slack_history_linear(get_slack_history(),time_start)
        return {
            'history': history,
            'user_to_letter': slack_letters_config,
            }

    def get_database_changes(self):
        pass

    def get_input_json(self):
        if "Content-Length" not in self.headers:
            return None
        _len = int(self.headers["Content-Length"])
        data = self.rfile.read(_len)
        data = json.loads(data)
        return data

    def get_by_id(self,cursor,_id=None):
        if _id:
            where = ' where id=%s'
            execute_args = (_id,)
        else:
            where = ''
            execute_args = ()
        return self.get_time_tracking_log(
            cursor, where, execute_args
            )

    def get_log_since(self,cursor,_time=None):
        if _time:
            # https://stackoverflow.com/a/23995048
            where = ' where start_at > from_unixtime(%s)'
            execute_args = (_time,)
        else:
            where = ''
            execute_args = ()
        return self.get_time_tracking_log(
            cursor, where, execute_args
            )

    def get_time_tracking_log(self,cursor,where,execute_args):
        sql = 'select %s from time_tracking'%(
            ', '.join(self.fields)
            )
        cursor.execute(sql + where, execute_args)
        res = []
        for data in cursor:
            res_item = {
                k:(v if not isinstance(v,datetime.datetime) else repr(v))
                for k,v in zip(self.fields,data)
                }
            res.append(res_item)
        return res

    def update(self,function,not_excluded_fields=set()):
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
                and k not in (
                    set(['id','end_at','start_at','exported']) -
                    not_excluded_fields
                    )
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
