# -*- coding: utf-8 -*-
from flask import flash

from flask.ext.wtf import Form
from wtforms import TextField, PasswordField, BooleanField
from wtforms.validators import Required


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text, error), 'error')


class LoginForm(Form):
    username = TextField(validators=[Required()])
    password = PasswordField(validators=[Required()])
    remember_me = BooleanField('Remember me')
