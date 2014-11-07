# -*- coding: utf-8 -*-
from __future__ import unicode_literals
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
    return render_template('404.html'), 404

@app.errorhandler(500)
def page_not_found(error):
    return render_template('500.html'), 500


@app.before_request
def before_request():
    g.account = None
    if all(k in session for k in ('username', 'password', 'cookies')):
        g.account = Account(session['username'],
                            session['password'],
                            pickle.loads(session['cookies']))


def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #if g.account is None or not g.account.logged_in:
        if 'username' not in session:
            flash(u'You need to be signed in for this page.')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
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
    """
    Main screen that shows all the leapcards and their details.
    """
    return render_template('overview.html', cards=g.account.cards)


@app.route('/journeys/<int:card_id>')
@requires_login
def journeys(card_id):
    """
    Shows a user's journeys for a specific leapcard.
    """
    return render_template('journeys.html',
            journeys=g.account.card_journeys(card_id))
