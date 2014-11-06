# -*- coding: utf-8 -*-
from flask import Flask

from . import config


app = Flask(__name__)
app.config.from_object(config)

from . import views
