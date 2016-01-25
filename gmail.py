import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class Gmail(object):
    def __init__(self, gmail_service):
        self.service = gmail_service

    def send(self, mail_tos, subject, text, html):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['To'] = ', '.join(mail_tos)

        part1 = MIMEText(text, 'plain')
        msg.attach(part1)

        part2 = MIMEText(html, 'html', 'utf-8')
        msg.attach(part2)

        body = {'raw': base64.b64encode(msg.as_bytes()).decode('utf-8')}
        self.service.users().messages().send(userId='me', body=body).execute()
