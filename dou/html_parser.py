from html.parser import HTMLParser
import re


class ExtractTagsAndDataHTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        self.tags = []
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):
        self.tags.append(('start', tag, attrs))

    def handle_endtag(self, tag):
        self.tags.append(('end', tag, None))

    def handle_data(self, data):
        self.tags.append(('data', data, None))


def parse(s):
    not_closing_tags = ['img', 'input', 'br', 'hr', 'meta', 'link']
    parser = ExtractTagsAndDataHTMLParser()
    parser.feed(s)
    tags = []
    depth = [tags]
    for tag in parser.tags:
        start_end_data, tag_or_data, attrs = tag
        if start_end_data == 'data':
            if not re.match(r'^\s+$', tag_or_data, re.M | re.S):
                depth[-1].append({'data': tag_or_data})
        if start_end_data == 'end':
            if tag_or_data in not_closing_tags:
                continue
            if tag_or_data == depth[-2][-1]['tag']:
                del depth[-1]
            elif tag_or_data == depth[-3][-1]['tag']:
                del depth[-1]
                del depth[-1]
            else:
                raise Exception(tag_or_data)
        if start_end_data == 'start':
            tag_dict = {'tag': tag_or_data}
            if tag_or_data.lower() not in not_closing_tags:
                tag_dict['children'] = []
            if attrs:
                tag_dict['attrs'] = dict(attrs)
            depth[-1].append(tag_dict)
            if 'children' in tag_dict:
                depth.append(tag_dict['children'])
    return tags


def match(tag, req):
    return all(k in tag and tag[k] == v for k, v in req.items())


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

def match_attr(tag, req):
    return ('attrs' in tag and
            all(k in tag['attrs'] and tag['attrs'][k] == v
                for k, v in req.items())
            )


def walk(tags, req, parents=[], match=match):
    for n, tag in enumerate(tags):
        parents_new = parents + [(n, tag)]
        if match(tag, req):
            return parents_new
        if 'children' in tag:
            res = walk(tag['children'], req, parents_new, match)
            if res is not None:
                return res
    return None
