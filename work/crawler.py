import json
import urllib.request
import zlib
import pickle
import re
from html.parser import HTMLParser
import mysql.connector
import os
import os.path

archives_searches={'common':{
'archives':{'page':'www.work.ua_Archive [20-05-27 08-58-41].har',
          'vacancy':'www.work.ua_Archive [20-05-27 08-59-42].har'},
'searches':{'page':'page=2','vacancy':'/ru/jobs/3886786/'},
},'prog':{
'archives':{'page':'www.work.ua_Archive [20-05-19 16-36-51].har',
          'vacancy':'www.work.ua_Archive [20-05-19 17-46-31].har'},
'searches':{'page':'page=2','vacancy':'/ru/jobs/3805896/'},
}}
keyword='prog'
archives=archives_searches[keyword]['archives']
searches=archives_searches[keyword]['searches']

data=dict()
x=dict()
for key,archive in archives.items():
    with open(archive,'rt') as f:
        data[key]=json.load(f)
    x[key]=[i for i in data[key]['log']['entries']
            if searches[key] in i['request']['url']][0]
g=lambda x:([(k,type(v),len(v) if not isinstance(v,(int,type(None))) else None)
             for k,v in (x.items() if isinstance(x,dict) else
                         x[0].items() if isinstance(x,list) else
                         enumerate(x))]
            if isinstance(x,(dict,list,tuple)) else x)
page_request=x['page']['request']
def get_page(n):
    global page_request
    data=dict((
        (i['name'],i['value'])
        if i['name']!='page' else
        (i['name'],str(n))
        ) for i in page_request['queryString'])#['postData']['params'])
    if n==1:
        del data['page']
    request_params = {
        'url':page_request['url'].replace('&page=2','&page=%d'%n if (n!=1) else ''),
        'data':'&'.join('%s=%s'%(k,v) for k,v in data.items()).encode('ascii'),
        'method':page_request['method']}
    return get_url(page_request,request_params)

def get_url(page_request,request_params):
    req = urllib.request.Request(**request_params)
    #print(request_params)
    for i in page_request['headers']:
        if i['name'] not in ['Host','Content-Length','Connection']:
            req.add_header(i['name'],i['value'])
    with urllib.request.urlopen(req) as f:
        r=f.read()
    if ('Content-Encoding' in f.headers and
        f.headers['Content-Encoding']=='gzip'):
        r=zlib.decompress(r,zlib.MAX_WBITS+16)
    return (r,f)

def get_vacancy(vacancy_id):
    global x
    request = x['vacancy']['request']
    request_params = {
        'url':(request['url']\
               .replace(searches['vacancy'].split('/')[-2],vacancy_id)),
        #'data':'&'.join('%s=%s'%(k,v) for k,v in data.items()).encode('ascii'),
        'method':request['method']}
    return get_url(request,request_params)

def decode(r,f):
    if 'Content-Type' in f.headers:
        m=re.match(r'.*charset=(.+)',f.headers['Content-Type'])
        if m:
            encoding=m.group(1).lower()
        else:
            encoding='utf-8'
    return r.decode(encoding)

class MyHTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        self.tags = []
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):
        self.tags.append(('start',tag,attrs))

    def handle_endtag(self, tag):
        self.tags.append(('end',tag))

    def handle_data(self, data):
        self.tags.append(('data',data))

def parse(s):
    not_closing_tags=['img','input','br','hr','meta','link']
    parser = MyHTMLParser()
    parser.feed(s)
    tags=[]
    depth=[tags]
    for tag in parser.tags:
        if tag[0]=='data':
            if not re.match('^\s+$',tag[1],re.M|re.S):
                depth[-1].append({'data':tag[1]})
        if tag[0]=='end':
            if tag[1] in not_closing_tags:
                continue
            if tag[1]==depth[-2][-1]['tag']:
                del depth[-1]
            elif tag[1]==depth[-3][-1]['tag']:
                del depth[-1]
                del depth[-1]
            else:
                raise Exception(tag[1])
        if tag[0]=='start':
            tag_dict={'tag':tag[1]}
            if tag[1].lower() not in not_closing_tags:
                tag_dict['children']=[]
            if tag[2]:
                tag_dict['attrs']=dict(tag[2])
            depth[-1].append(tag_dict)
            if 'children' in tag_dict:
                depth.append(tag_dict['children'])
    return tags

def match(tag,req):
    return all(k in tag and tag[k]==v for k,v in req.items())
#    for k,v in req.items():
#        if k not in tag:
#            return False
##        if isinstance(v,(dict,list)):
##            if not isinstance(tag[k],type(v)):
##                return False
##            _iter={
##                dict:lambda x:x.items(),
##                list:lambda x:enumerate(x),
##                }[type(v)]()
#        if tag[k]!=v:
#            return False
#    return True

def match_attr(tag,req):
    return ('attrs' in tag and
            all(k in tag['attrs'] and tag['attrs'][k]==v
                for k,v in req.items())
            )

def walk(tags,req,parents=[],match=match):
    for n,tag in enumerate(tags):
        parents_new = parents+[(n,tag)]
        if match(tag,req):
            return parents_new
        if 'children' in tag:
            res=walk(tag['children'],req,parents_new,match)
            if res!=None:
                return res
    return None

def get_num_pages(tags):
    parents = walk(tags,{'tag':'li','attrs':{'class':'no-style'},'children':[{
        'tag':'span','attrs':{'class':'ellipsis-style'},'children':[{
            'data':'...'
            }]
        }]
                         })
    return parents[-2][1]['children'][parents[-1][0]+1]['children'][0]['children'][0]['data']

def filter_page(tags):
    parents=walk(tags,
                 {'class':  "overflow text-muted add-top-sm add-bottom"},
                 [],match_attr)
    that_div=parents[-3][1]
    children=list(filter((lambda elem:
                     'tag' in elem and elem['tag']=='div'
                     and 'attrs' in elem
                     and 'class' in elem['attrs']
                     and any(i=='job-link'
                             for i in elem['attrs']['class'].split(' '))
                     ),that_div['children']))
    filtered_2=[]
    for elem in children:
        res={'tag':elem['tag']}
        if 'attr' in elem:
            res['attr']=elem['attr']
        if 'children' in elem:
            met=set()
            vacancy_id=None
            title=None
            res['children']=[]
            for elem2 in elem['children']:
                if 'tag' in elem2 and elem2['tag'] in ['h2','p']:
                    met.add(elem2['tag'])
                    res['children'].append(elem2)
                    if elem2['tag']=='h2':
                        if ('children' in elem2 and elem2['children'] and
                        'tag' in elem2['children'][0] and
                        elem2['children'][0]['tag']=='a' and
                        'children' in elem2['children'][0] and
                        elem2['children'][0]['children'] and
                        'data' in elem2['children'][0]['children'][0] and
                        elem2['children'][0]['children'][0]['data']):
                            vacancy_id=(elem2['children'][0]
                                ['attrs']['href'].split('/')[-2])
                            title=(elem2['children'][0]
                                   ['children'][0]['data'])

                        continue
                    else:
                        break
                if ('h2' in met) and ('p' not in met):
                    res['children'].append(elem2)
        filtered_2.append({'id':vacancy_id,'title':title,'data':res})
    return filtered_2

if __name__ == '__main__':
    sql_connection=(
        mysql.connector.connect(user='root', password='12345678', database='work')
    )
    cursor=sql_connection.cursor()
    cursor.execute(('select max(crawl_id) from pages '
                    'where keyword=%s'),(keyword,))
    crawl_id=(list(cursor)[0][0] or 0)+1
    sql_insert_preview = (
    'INSERT INTO vacancy (id,preview,header) VALUES (%s,%s,%s) '
    'ON DUPLICATE KEY UPDATE preview=%s, header=%s'
    )
    cursor.execute('select id from vacancy where preview is not null')
    with_prewiev=list(cursor)
    num_pages=1
    n=1
    sql_insert = lambda what:(
    'INSERT INTO pages (keyword,crawl_id,page,%s) VALUES (%%s,%%s,%%s,%%s) '
    'ON DUPLICATE KEY UPDATE %s=%%s'
    )%((what,)*2)
    while n<=num_pages:
        r,f=get_page(n)
        #with open('pages/%d.pickle'%n,'wb') as fp:
        #    pickle.dump((r,f),fp)
        #with open('pages/2.pickle','rb') as fp:
        #    (r,f)=pickle.load(fp)
        s=decode(r,f)
        cursor.execute(sql_insert('raw'),(keyword,crawl_id,n,)+((s,)*2))
        sql_connection.commit()
        tags=parse(s)
        #with open('pages/%d_parsed.pickle'%n,'wb') as fp:
        #    pickle.dump(tags,fp)
        cursor.execute(sql_insert('parsed'),
                       (keyword,crawl_id,n,)+((json.dumps(tags),)*2))
        sql_connection.commit()
        if n==1:
            num_pages=int(get_num_pages(tags))
            print('%d pages: '%num_pages)
        print('Page %d'%n,end='')
        filtered=filter_page(tags)
        print('(%d):'%len(filtered),end='')
        for vacancy in filtered:
            if not vacancy['id']:
                print('-',sep='',end='')
                continue
            if (vacancy['id'] in with_prewiev or
                (vacancy['id'],) in with_prewiev or
                int(vacancy['id']) in with_prewiev or
                (int(vacancy['id']),) in with_prewiev):
                print('>',sep='',end='')
                continue
            cursor.execute(sql_insert_preview,(vacancy['id'],)+
                           ((json.dumps(vacancy['data']),vacancy['title'])*2))
            sql_connection.commit()
            print('.',sep='',end='')
        print()
        n+=1
    #print()
    cursor.close()
    sql_connection.close()

if __name__ == '__main__' and False:
    sql_connection=(
        mysql.connector.connect(user='root', password='12345678', database='work')
    )
    cursor=sql_connection.cursor()
    #cursor.execute(('select max(crawl_id) from pages '
    #                'where keyword=%s'),(keyword,))
    #crawl_id=(list(cursor)[0][0] or 0)
    #{'class':  "overflow text-muted add-top-sm add-bottom"}
    for n_page in range(1,300):
        file_name = 'pages/%d_parsed.pickle'%n_page
        if not os.path.exists(file_name):
            break
        with open(file_name,'rb') as fp:
            tags=pickle.load(fp)
    cursor.close()
    sql_connection.close()
