from smtplib import SMTP_SSL
from ssl import create_default_context
from env import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread

def send_email(recipient, subject, content):
  def thread():
    with SMTP_SSL(SMTP_HOST, SMTP_PORT, context=create_default_context()) as server:
      server.login(SMTP_USERNAME, SMTP_PASSWORD)
      message = MIMEMultipart("alternative")
      message['Subject'] = subject
      message['From'] = 'no-reply@fryx.finance'
      message['To'] = recipient
      message.attach(MIMEText(content, 'html'))
      server.sendmail("no-reply@fryx.finance", recipient, message.as_string())

  Thread(target=thread).start()
