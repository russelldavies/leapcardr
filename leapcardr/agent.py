"""
Agent that logs into the Leapcard website and scrapes data.
"""
from __future__ import unicode_literals
from functools import wraps

import mechanize
from cookielib import CookieJar
from bs4 import BeautifulSoup
import datetime
import time
import re

BASE_URL = "https://www.leapcard.ie"


class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class ParseError(Error):
    pass


def login_required(func):
    """
    Decorator to ensure object instance is authenticated before
    function is called.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.logged_in:
            self.login()
        return func(self, *args, **kwargs)
    return wrapper


class Account(object):
    login_cookie_name = '.ASPXFORMSAUTH'
    card_selection_event_target = 'ctl00$ctl00$ContentPlaceHolder1$TabContainer2$MyCardsTabPanel$ddlMyCardsList'

    def __init__(self, username=None, password=None, cookies=[]):
        self.username = username
        self.password = password

        self.cj = CookieJar()
        [self.cj.set_cookie(c) for c in cookies]

        self.br = mechanize.Browser(factory=mechanize.RobustFactory())
        self.br.set_cookiejar(self.cj)
        # Browser options
        self.br.set_handle_equiv(True)
        self.br.set_handle_gzip(True)
        self.br.set_handle_redirect(True)
        self.br.set_handle_referer(True)
        self.br.set_handle_robots(False)
        # Follows refresh 0 but not hangs on refresh > 0
        self.br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(),
                                   max_time=1)
        # Required so ASP hidden forms are set properly
        self.br.addheaders = [('User-agent', 'Mozilla/5.0 (comptabile)')]

    def login(self):
        """
        Login and set name if successful.
        """
        url = BASE_URL + '/en/Login.aspx'
        self.br.open(url)
        self.br.select_form(nr=0)
        self.br.form["ctl00$ContentPlaceHolder1$UserName"] = self.username
        self.br.form["ctl00$ContentPlaceHolder1$Password"] = self.password
        self.br.submit(name="ctl00$ContentPlaceHolder1$btnlogin")

        # Upon successful login, this cookie should be set
        login_cookie = None
        for cookie in self.cj:
            if cookie.name == self.login_cookie_name:
                login_cookie = cookie
                break

        if login_cookie:
            # Get account holder name
            soup = BeautifulSoup(self.br.response().read())
            self.name = soup.find(id="LoginName1").string

            login_cookie.discard = True
            future = datetime.datetime.now() + datetime.timedelta(minutes=20)
            unix_time = int(time.mktime(future.timetuple()))
            login_cookie.expires = unix_time
            return True
        else:
            return False

    @property
    def logged_in(self):
        for cookie in self.cj:
            if cookie.name == self.login_cookie_name and not cookie.is_expired():
                return True
        return False

    @login_required
    def list_cards(self):
        """
        Return the cards a user has registered as a dict in
        the form {card_id: {card details}}.
        """
        url = BASE_URL + "/en/SelfServices/CardServices/CardOverView.aspx"

        self.br.open(url)
        soup = BeautifulSoup(self.br.response().read())

        cards = {}
        for tag in soup.find('select').find_all('option'):
            card_id = tag['value']
            card_name = tag.text
            if tag.has_attr('selected'):
                cards[card_id] = self._card_overview(soup)
            else:
                self.br.select_form(nr=0)
                self.br.set_all_readonly(False)
                self.br["__EVENTTARGET"] = self.card_selection_event_target
                self.br[self.card_selection_event_target] = [card_id]
                self.br.submit()
                soup = BeautifulSoup(self.br.response().read())
                cards[card_id] = self._card_overview(soup)

        return cards

    @login_required
    def card_history(self, card_id):
        """Returns a list of all the journeys for a specific card."""

        url = BASE_URL + "/en/SelfServices/CardServices/ViewJourneyHistory.aspx"

        self.br.open(url)
        self.br.select_form(nr=0)

        self.br.set_all_readonly(False)
        self.br["__EVENTTARGET"] = self.card_selection_event_target
        self.br[self.card_selection_event_target] = [card_id]
        self.br.submit()

        # Get print view which includes all journeys instead of clicking through list
        self.br.select_form(nr=0)
        self.br.submit(name="ctl00$ctl00$ContentPlaceHolder1$TabContainer2$MyCardsTabPanel$ContentPlaceHolder1$btn_Print")

        # Extract print data (contained in js print script)
        pattern = r'printWin.document.write\("(.*)"\);printWin.document.close'
        match = None
        match = re.search(pattern, self.br.response().read())
        if not match:
            raise ParseError("Could not extract journey print data.")
        soup = BeautifulSoup(match.group(1))

        return self._journey_list(soup)

    def _card_overview(self, soup):
        """
        Return a dict of card details.
        """
        #[list(tag.stripped_strings) for tag in soup.find(id=re.compile('CardDetails')).find_all('li')[:-1]]
        overview_vals = [tag.contents[2].strip() for tag in
                soup.find(id=re.compile('CardDetails')).find_all('li')[:-1]]
        overview_keys = ('number', 'label', 'type', 'status', 'credit_status',
                'auto_topup', 'init_date', 'expiry_date', 'balance')
        card_overview = dict(zip(overview_keys, overview_vals))

        return card_overview

    def _journey_list(self, soup):
        """
        Return a list of journey dicts.
        """
        table = soup.find(id='gvCardJourney')
        journeys = []
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            time = cols[0].string.strip() + " " + cols[1].string.strip()
            journeys.append({
                'timestamp': datetime.datetime.strptime(time,
                    '%d/%m/%Y %I:%M %p').strftime('%s'),
                'source': cols[2].string.strip(),
                'type': cols[3].string.strip(),
                'amount': cols[4].string.strip(),
                'balance': cols[5].string.strip(),
            })
        return journeys
