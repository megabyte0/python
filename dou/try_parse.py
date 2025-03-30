from crawl import Crawler
from html_parser import parse, walk

if __name__ == '__main__':
    crawler = Crawler()
    data = crawler.process('/vacancies/?remote', url='https://jobs.dou.ua/companies/sharpminds/vacancies/299188/')
    assert 'b-typo vacancy-section' in data
    tags = parse(data)
    res = walk(tags, {'tag':'div', 'attrs': {'class':'b-typo vacancy-section'}})
    print(res[-1])
