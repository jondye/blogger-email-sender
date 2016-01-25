from flask_wtf import Form
from wtforms import validators, FieldList
from wtforms.fields.html5 import EmailField


class EmailForm(Form):
    addresses = FieldList(EmailField('Email Address', [validators.DataRequired(), validators.Email()]))
