import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from smtplib import *

class EmailSender:

    def __init__(self, SENDER, PASS, CONNECT=True):
        self.sender = SENDER
        self.password = PASS

        self.msg = None

        if CONNECT:
            self.connect()

    def connect(self):
        self.connection = SMTP(host='smtp.gmail.com', port=587)
        self.connection.starttls()
        self.connection.login(user=self.sender, password=self.password)

    def compose(self, target, from_name, to_name, subject, message):
        self.msg = EmailMessage()
        self.msg['From'] = formataddr((from_name, self.sender))
        self.msg['To'] = formataddr((to_name, target))

        self.msg['Subject'] = subject
        self.msg.set_content(message)

    def send(self, CLOSE=True):
        try:
            self.connection.send_message(self.msg)
        except smtplib.SMTPServerDisconnected:
            self.connect()
            self.connection.send_message(self.msg)

        if CLOSE:
            self.close()

    def close(self):
        self.connection.close()
