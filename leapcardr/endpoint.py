import requests
import cookielib
import re
from bs4 import BeautifulSoup
import datetime
import time

cj = cookielib.CookieJar()

def save_cookies(cookiejar):
    expiry_mins = 15

    for cookie in cookiejar:
        if cookie.discard:
            future = datetime.datetime.now() + datetime.timedelta(minutes=expiry_mins)
            unix_time = int(time.mktime(future.timetuple()))
            cookie.expires = unix_time
            cookie.discard = False

def extract_aspdata(html, fields):
    aspdata = {}
    for field in fields:
        pattern = field + r'.*value="(.*)"'
        match = re.search(pattern, html)
        if match:
            aspdata[field] = match.group(1)
    return aspdata

def login(username, password):
    url = 'https://www.leapcard.ie'
    fields = ("__VIEWSTATE", "__EVENTVALIDATION")

    aspdata = extract_aspdata(requests.get(url).text, fields)
    payload = {
        fields[0]: aspdata[fields[0]],
        fields[1]: aspdata[fields[1]],
        'ctl00$ContentPlaceHolder1$login_View$UserName': username,
        'ctl00$ContentPlaceHolder1$login_View$Password': password,
        'ctl00$ContentPlaceHolder1$login_View$btnlogin': 'Login',
    }

    #r = requests.post(url, data=payload, cookies=cj, allow_redirects=False)
    #return r.status_code == requests.codes.found
    r = requests.post(url, data=payload, cookies=cj)
    #expiry_secs = int(r.headers['refresh'].split(';')[0]) - 30
    return "Welcome" in r.text

def list_cards():
    url = 'https://www.leapcard.ie/SelfServices/CardServices/ViewJourneyHistory.aspx'

    html = requests.get(url, cookies=cj).text
    soup = BeautifulSoup(html)
    card_tags = soup.find(id="ContentPlaceHolder1_ddlUserRegisteredCards").find_all('option')[1:]
    return dict([(tag.text, tag['value']) for tag in card_tags])
    
def list_card_history(card_id):
    url = 'https://www.leapcard.ie/SelfServices/CardServices/ViewJourneyHistory.aspx'
    fields = ("__VIEWSTATE", "__PREVIOUSPAGE")
    proxies = None #{"https": "127.0.0.1:8080"}

    html = requests.get(url, cookies=cj, proxies=proxies).text
    aspdata = extract_aspdata(html, fields)
    soup = BeautifulSoup(html)
    payload = {
        fields[0]: soup.find(id=fields[0])['value'], #aspdata[fields[0]],
        fields[1]: soup.find(id=fields[1])['value'], #aspdata[fields[1]],
        'ctl00$ContentPlaceHolder1$ddlUserRegisteredCards': card_id,
    }
    return payload
    
    headers = {
        'Referer': 'https://www.leapcard.ie/SelfServices/CardServices/ViewJourneyHistory.aspx',
        'Origin': 'https://www.leapcard.ie',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.97 Safari/537.11',
    }
