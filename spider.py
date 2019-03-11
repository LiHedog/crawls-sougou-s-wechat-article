from urllib.parse import urlencode
import requests
from requests.exceptions import ConnectionError
from pyquery import PyQuery as pq
import pymongo

client = pymongo.MongoClient('localhost')
db = client['weixin']

base_url = 'https://weixin.sogou.com/weixin?'

headers = {
    'Cookie': 'SUV=1545909958456327; SMYUV=1545909958457919; UM_distinctid=167ef69fb3035b-044183a787f426-b781636-1fa400-167ef69fb31346; _ga=GA1.2.1338857850.1546843672; CXID=D6C79E5AB5C9C7D9BB390F3FFF05A8A8; SUID=6F845F704C238B0A5C655E67000DF4F1; ad=Tyllllllll2tBqiXlllllVeOgf7llllltVM9bZllllylllllROxlw@@@@@@@@@@@; IPLOC=CN4403; cd=1550728372&138422711c1aa405e872165f18c55c82; rd=olllllllll2tb0hHgpcDHVem53Ctb0h1LPJBbZllll9llllxVylll5@@@@@@@@@@; ld=0yllllllll2tb0hHgpcDHVei27Ctb0h1LPJBbZllll9llllllylll5@@@@@@@@@@; LSTMV=259%2C213; LCLKINT=2175; ABTEST=8|1551766043|v1; weixinIndexVisited=1; sct=1; JSESSIONID=aaayESATQzgHc9WnlyZKw; ppinf=5|1551766259|1552975859|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZToyMDpEUiVFOCU5MyU5RCVFNyU5MyU5Q3xjcnQ6MTA6MTU1MTc2NjI1OXxyZWZuaWNrOjIwOkRSJUU4JTkzJTlEJUU3JTkzJTlDfHVzZXJpZDo0NDpvOXQybHVPQU1KUUxVYjREanQxcG43LXhraGpVQHdlaXhpbi5zb2h1LmNvbXw; pprdig=acd4Pnfzn8nxX0PafcW8OjwZh3qDbOD7yAmSRBIWxi451i_LPAeZ1WxBdnSnDJVThSeqDfhlmQ16fU8FLweWjcGPZQhltJQJkGF0rmZGZoqVoKmxyY0ptdSPkEaMZAbCc5zrpZuu0IKHD57L8u5GSiAyWJ-0KiwhflCSczoJ0r8; sgid=06-37472631-AVxibEvOmRDkcQC32cmxFVicM; ppmdig=1551766260000000e140a563eaa123145908f5b82ed4a3a9; PHPSESSID=lts8eof02o4efm62gvj4679i81; SNUID=F7C18A43989D1ACA59EF2B8A990A12B0; seccodeRight=success; successCount=1|Tue, 05 Mar 2019 06:17:21 GMT',
    'Host': 'weixin.sogou.com',
    'Referer': 'https://weixin.sogou.com/weixin?query=%E9%A3%8E%E6%99%AF&_sug_type_=&sut=5079&lkt=7%2C1551766084967%2C1551766090031&s_from=input&_sug_=y&type=2&sst0=1551766090134&page=99&ie=utf8',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36'
}

keyword = '风景'
proxy_pool_url = 'http://127.0.0.1:5000/get'
proxy = None
max_count = 10000000


def get_proxy():
    try:
        response = requests.get(proxy_pool_url)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return None

def get_html(url, count=1):
    print('Crawking', url)
    print('Trying Count', count)
    global proxy
    if count >= max_count:
        print('Tried Too Mang Counts')
        return None
    try:
        if proxy:
            proxies = {
                'http': 'http://' + proxy
            }
            response = requests.get(url, allow_redirects=False, headers=headers, proxies = proxies)
        else:
            response = requests.get(url, allow_redirects=False, headers=headers)
        if response.status_code == 200:
            return response.text
        if response.status_code == 302:
            print(302)
            proxy = get_proxy()
            if proxy:
                print('Using Proxy', proxy)
                return get_html(url)
            else:
                print('Get Proxy Failed')
                return None
    except ConnectionError as e:
        print('Error Occurred', e.args)
        proxy = get_proxy()
        count += 1
        return get_html(url, count)

def get_index(keyword, page):
    data = {
        'query': keyword,
        'type': 2,
        'page': page
    }
    queries = urlencode(data)
    url = base_url + queries
    html = get_html(url)
    return html

def parse_index(html):
    doc = pq(html)
    items = doc('.news-box .news-list li .txt-box h3 a').items()
    for item in items:
        yield item.attr('href')

def get_dedail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return None

def parse_detail(html):
    doc = pq(html)
    title = doc('.rich_media_title').text()
    content = doc('.rich_media_content ').text()
    date = doc('#publish-time').text()
    nickname = doc('#js_profile_qrcode > div > strong').text()
    wechat = doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
    return {
        'title': title,
        'content': content,
        'data': date,
        'nickname': nickname,
        'wechat': wechat
    }

def save_to_mongo(data):
    if db['articles'].update({'title': data['title']}, {'$set': data}, True):
        print('Save to Mongo', data['title'])
    else:
        print('Save to Mongo Faild', data['title'])

def main():
    for page in range(1, 100):
        html = get_index(keyword, page)
        if html:
            article_urls = parse_index(html)
            for article_url in article_urls:
                article_html = get_dedail(article_url)
            if article_html:
                article_data = parse_detail(article_html)
                print(article_data)
                save_to_mongo(article_data)



if __name__ == '__main__':
    main()


