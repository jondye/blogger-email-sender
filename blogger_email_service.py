import os
import sys
from functools import wraps

import flask
from flask_sqlalchemy import SQLAlchemy
import httplib2
from apiclient import discovery
from oauth2client import client

import forms
from gmail import Gmail

app = flask.Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)


class Recipient(db.Model):
    blog_id = db.Column(db.String(30), primary_key=True)
    email = db.Column(db.String(120), primary_key=True)

    def __init__(self, blog, email):
        self.blog_id = blog
        self.email = email

    def __repr__(self):
        return '<Recipient %r>' % self.email


def google_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in flask.session:
            return flask.redirect(flask.url_for('.oauth2callback'))
        credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
        if credentials.access_token_expired:
            return flask.redirect(flask.url_for('.oauth2callback'))
        flask.g.http_auth = credentials.authorize(httplib2.Http())
        return f(*args, **kwargs)

    return decorated_function


def blogger_service():
    return discovery.build('blogger', 'v3', http=flask.g.http_auth)


def gmail_service():
    return discovery.build('gmail', 'v1', http=flask.g.http_auth)


@app.route('/')
@google_auth
def blog_list():
    blogs = blogger_service().blogs().listByUser(userId='self').execute()
    return flask.render_template('blog_list.html', blogs=blogs['items'])


@app.route('/blog/<blog_id>')
@google_auth
def blog(blog_id):
    posts = (blogger_service().posts().list(
        blogId=blog_id,
        orderBy='published',
        status='live',
        fetchBodies=False
    ).execute())
    return flask.render_template('post_list.html', blog_id=blog_id, posts=posts['items'])


@app.route('/blog/<blog_id>/post/<post_id>/email', methods=['GET', 'POST'])
@google_auth
def send_email(blog_id, post_id):
    post = (blogger_service().posts().get(
        blogId=blog_id,
        postId=post_id
    ).execute())
    form = forms.Form()
    recipients = Recipient.query.filter_by(blog_id=blog_id).all()
    addresses = [r.email for r in recipients]

    if form.validate_on_submit():
        html = flask.render_template(
            'email.html',
            title=post['title'],
            content=flask.Markup(post['content']))
        text = 'A new blog post is available at ' + post['url']
        gmail = Gmail(gmail_service())
        gmail.send(addresses, post['title'], text, html)
        flask.flash(u"Email sent - {title}".format(**post), "success")
        return flask.redirect(flask.url_for('.blog', blog_id=blog_id))

    return flask.render_template('send_email.html', post=post, form=form, addresses=addresses)


@app.route('/settings', methods=['GET', 'POST'])
@google_auth
def settings():
    blogs = blogger_service().blogs().listByUser(userId='self').execute()
    return flask.render_template('settings.html', blogs=blogs['items'])


@app.route('/settings/<blog_id>', methods=['GET', 'POST'])
@google_auth
def blog_settings(blog_id):
    form = forms.EmailForm()
    blog = blogger_service().blogs().get(blogId=blog_id).execute()
    recipients = Recipient.query.filter_by(blog_id=blog['id']).all()

    if form.validate_on_submit():
        new_emails = form.addresses.data[:]
        for recipient in recipients:
            if recipient.email in new_emails:
                new_emails.remove(recipient.email)
            else:
                db.session.delete(recipient)
        for email in new_emails:
            db.session.add(Recipient(blog_id, email))
        db.session.commit()
        flask.flash(u"Saved settings for {name}".format(**blog), "success")
        return flask.redirect(flask.url_for('.blog_list'))

    for recipient in recipients:
        form.addresses.append_entry(recipient.email)
    if not recipients:
        form.addresses.append_entry("")
    return flask.render_template('blog_settings.html', form=form, blog_name=blog['name'])


@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        os.path.join(sys.path[0], 'client_secrets.json'),
        scope='https://www.googleapis.com/auth/blogger.readonly https://www.googleapis.com/auth/gmail.send',
        redirect_uri=flask.url_for('.oauth2callback', _external=True))
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    return flask.redirect(flask.url_for('.blog_list'))


if __name__ == '__main__':
    app.run()
