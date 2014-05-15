import mechanize
import cookielib
from bs4 import BeautifulSoup
from datetime import datetime
import re

BASE_URL = "https://www.leapcard.ie"


class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class LoginError(Error):
    pass


def login_required(func):
    """
    Decorator to ensure object instance is authenticated before
    function is called.
    """
    def wrapped(self):
        if not self.logged_in and self.login():
            return func(self)
        else:
            raise LoginError('Could not login')
        return func(self)
    return wrapped


class Account(object):
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.logged_in = False

        self.br = mechanize.Browser(factory=mechanize.RobustFactory())
        self.cj = cookielib.CookieJar()
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
        auth_cookie_name = '.ASPXFORMSAUTH'
        if auth_cookie_name in [c.name for c in self.cj]:
            # Get account holder name
            soup = BeautifulSoup(self.br.response().read())
            self.logged_in = True
            self.name = soup.find(id="LoginName1").string

        return self.logged_in

    @login_required
    def list_cards(self):
        """
        Return the cards a user has registered as a dict in
        the form {card_id: {card details}}.
        """
        url = BASE_URL + "/en/SelfServices/CardServices/CardOverView.aspx"
        event_target = 'ctl00$ctl00$ContentPlaceHolder1$TabContainer2$MyCardsTabPanel$ddlMyCardsList'

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
                self.br["__EVENTTARGET"] = event_target
                self.br[event_target] = [card_id]
                self.br.submit()
                soup = BeautifulSoup(self.br.response().read())
                cards[card_id] = self._card_overview(soup)

        return cards

    def card_history(self, card_id):
        """Returns a list of all the journeys for a specific card."""

        url = BASE_URL + "/en/SelfServices/CardServices/ViewJourneyHistory.aspx"
        import ipdb; ipdb.set_trace()
        cardlist_control = "ctl00$ContentPlaceHolder1$ddlUserRegisteredCards"

        self.br.open(url)
        self.br.select_form(nr=0)
        self.br.find_control(cardlist_control).value = [str(card_id)]
        self.br.submit()

        # Get print view which includes all journeys instead of clicking through list
        self.br.select_form(nr=0)
        #br.set_all_readonly(False)
        #br.find_control("ctl00$ContentPlaceHolder1$btnCancel").disabled = True
        #br.find_control("ctl00$ucSiteSearch$btnSearch").disabled = True
        self.br.submit(name='ctl00$ContentPlaceHolder1$btn_Print')

        # Extract print data (contained in js print script)
        pattern = r'printWin.document.write\("(.*)"\);printWin.document.close'
        match = re.search(pattern, self.br.response().read())
        if not match:
            raise ValueError
        soup = BeautifulSoup(match.group(1))

        # Parse journeys
        purse_id = "ContentPlaceHolder1_CardJourneyTabContainer_PurseTransactionTabPanel_gvCardJourney"
        table = soup.find(id=purse_id)
        journeys = []
        #rows = []
        #for bgcolor in ('#EDEDED', '#F2F1F1'):
        #	rows += table.find_all('tr', {'bgcolor': bgcolor})
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            time = cols[0].string.strip() + " " + cols[1].string.strip()
            journeys.append({
                'timestamp': datetime.strptime(time,
                    '%d/%m/%Y %I:%M %p').strftime('%s'),
                'source': cols[2].string.strip(),
                'type': cols[3].string.strip(),
                'amount': cols[4].string.strip(),
                'balance': cols[5].string.strip(),
            })
        return journeys

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
