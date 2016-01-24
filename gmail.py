import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class Gmail(object):
    def __init__(self, user, password, host=None):
        self.host = 'smtp.gmail.com:587'
        if host:
            self.host = host
        self.user = user
        self.password = password

    def send(self, mail_tos, subject, text, html):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.user
        msg['To'] = ', '.join(mail_tos)

        part1 = MIMEText(text, 'plain')
        msg.attach(part1)

        part2 = MIMEText(html, 'html', 'utf-8')
        msg.attach(part2)

        server = smtplib.SMTP(self.host)
        server.ehlo()
        server.starttls()
        server.login(self.user, self.password)
        server.sendmail(self.user, mail_tos, msg.as_string())
        server.quit()
