import json
import mysql.connector
import os
import re
url='https://www.work.ua/ru/jobseeker/my/apply-history/?page=1'
sql_connection=(
    mysql.connector.connect(user='root', password='12345678', database='work')
)
cursor=sql_connection.cursor()
update_sql=r'''UPDATE `work`.actions
SET done=1
where vacancy_id=%s;
'''
matcher=re.compile(
    re.sub(r'\d+',lambda m:r'(\d+)',
    re.escape(r'<a href="/ru/jobs/3954555/">')
           )
    )
fn='/home/user/work/work/www.work.ua_Archive [20-09-18 15-51-23]_apply_history.har'
path='/home/user/work/work/apply_history'
res=[]
for fn_ in os.listdir(path):
    fn=os.path.join(path,fn_)
    with open(fn,'rt') as fp:
        x=json.load(fp)
    y=[i for i in x['log']['entries'] if url[:-1] in i['request']['url']]
    for i in y:
        res.extend(matcher.findall(i['response']['content']['text']))

for i in res:
    cursor.execute(update_sql,(i,))
sql_connection.commit()
cursor.close()
sql_connection.close()
