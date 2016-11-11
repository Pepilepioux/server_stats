#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Envoie un mail

Inspiré de http://stackoverflow.com/questions/882712/sending-html-email-using-python
pour le html

"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text   import MIMEText

#	------------------------------------------------------------------------------------
def EnvoyerMessage (serveur, sender, destinataire, subject, contenuTexte, smtp_user = None , smtp_pwd = None, contenuHTML = None, listeCopies = None) :
    if contenuHTML is None :
        msg = MIMEText( contenuTexte.encode('utf-8'), 'plain', 'utf-8' )
    else :
        msg = MIMEMultipart('alternative')
        part1 = MIMEText(contenuTexte.encode('utf-8'), 'plain', 'utf-8')
        part2 = MIMEText(contenuHTML.encode('utf-8'), 'html', 'utf-8')
        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)
        
    msg['From'] = sender
    msg['To'] = destinataire
    if  listeCopies :
        msg['CC'] = ','.join(listeCopies)
    msg['Subject'] = subject

    addr_from = sender
    addr_to = []
    addr_to.append ( destinataire )
    if  listeCopies :
        addr_to += listeCopies
    
    s = smtplib.SMTP( serveur )
    
    if smtp_user is not None :
        s.starttls()
        s.login(smtp_user,smtp_pwd)
    
    rep = s.sendmail(addr_from, addr_to, msg.as_string())
    s.quit()
