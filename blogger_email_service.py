import os
import sys
from functools import wraps

import flask
import httplib2
from apiclient import discovery
from oauth2client import client

import forms
from gmail import Gmail

app = flask.Flask(__name__)


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
    addresses = flask.session.get('addresses', [])

    if form.validate_on_submit():
        html = flask.render_template(
            'email.html',
            title=post['title'],
            content=flask.Markup(post['content']))
        text = 'A new blog post is available at ' + post['url']
        gmail = Gmail(gmail_service())
        gmail.send(addresses, post['title'], text, html)
        return flask.redirect(flask.url_for('.blog', blog_id=blog_id))

    return flask.render_template('send_email.html', post=post, form=form, addresses=addresses)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    form = forms.EmailForm()
    if form.validate_on_submit():
        flask.session['addresses'] = form.addresses.data
        return flask.redirect(flask.url_for('.blog_list'))
    for email in flask.session.get('addresses', ['']):
        form.addresses.append_entry(email)
    return flask.render_template('settings.html', form=form)


@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        os.path.join(sys.path[0], 'client_secrets.json'),
        scope='https://www.googleapis.com/auth/blogger https://www.googleapis.com/auth/gmail.send',
        redirect_uri=flask.url_for('.oauth2callback', _external=True))
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    return flask.redirect(flask.url_for('.blog_list'))


if __name__ == '__main__':
    app.config.from_object('config')
    app.run()
