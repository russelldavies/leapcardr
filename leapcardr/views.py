# -*- coding: utf-8 -*-
from functools import wraps
import pickle

from flask import (
    request, session, g, redirect, url_for, abort,
    render_template, flash
)

from . import app
from .forms import flash_errors, LoginForm
from .agent import Account


@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404

@app.errorhandler(500)
def page_not_found(error):
    return render_template('error.html'), 500


@app.before_request
def before_request():
    g.account = None
    if 'username' in session:
        cookies = pickle.loads(session['cookies'])
        g.account = Account(session['username'], session['password'], cookies)


def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session and not g.account.logged_in:
            flash(u'You need to be signed in for this page.')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Logs the user into the Leap Card website and stores the login session
    information locally.
    """
    if g.get('account') is not None:
        return redirect(url_for('overview'))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        account = Account(username, password)
        if account.login():
            session['username'] = username
            session['password'] = password
            session['cookies'] = pickle.dumps([c for c in account.cj])
            if form.remember_me.data:
                session.permanent = True
            return redirect(url_for('overview'))
        else:
            flash("Could not log you in, check username and password", 'error')
    else:
        flash_errors(form)
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('pasword', None)
    session.pop('cookies', None)
    flash('You were logged out.')
    return redirect(url_for('login'))


@app.route('/')
@requires_login
def overview():
    cards = account.list_cards()
    return render_template('overview.html')


@app.route('/journeys')
@requires_login
def show_journeys(card_id):
    """
    Shows a user's journeys for a specific leapcard.
    """
    return render_template('journeys.html', journeys=journeys)
