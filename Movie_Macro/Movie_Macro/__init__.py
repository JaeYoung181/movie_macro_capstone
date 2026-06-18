"""
The flask application package.
"""

from flask import Flask
app = Flask(__name__)
app.secret_key = 'movie_macro_secret'

import Movie_Macro.views
