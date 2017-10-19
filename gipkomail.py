#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Version 2 2016-12-12

    Envoie un mail, plain text ou html, avec ou sans pièces jointes, avec ou sans cc et bcc,
    avec un minimum de vérifications : existence des fichiers en PJ, types des arguments, etc.

    Par contre il n'y a pas de vérification structurelle des adresses.
    Pour le jour où les noms de domaine pourront être en chinois...

    Inspiré de http://stackoverflow.com/questions/882712/sending-html-email-using-python pour le html et
    http://stackoverflow.com/questions/3362600/how-to-send-email-attachments-with-python pour les attachements.

    Petit bug remarqué : s'il y a un texte ET un html les DEUX s'affichent dans le message reçu.
    C'est ça ou, si on fait un MIMEMultipart('alternative'), on ne voit pas les PJ...
    Je préfère ça à une censure qui supprimerait arbitrairement l'un des deux.

Version 2.1 2017-10-19

    Accepte le port en paramètre optionnel.

"""
import os
import smtplib
#   from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders


#   ------------------------------------------------------------------------------------------------------------------
def verif_adresses(adresses):
    """
    Comme adresses on accepte les chaines de caractères, éventuellement séparées par des virgules,
    les listes et les tuples de chaines de caractères.
    On ne vérifie toutefois pas la structure des adresses.
    Et on renvoie une liste de str
    """
    if adresses is None:
        return None
        #   Juste pour pas avoir à traiter ça dans le programme principal.

    if type(adresses).__name__ == 'str':
        return [e.strip() for e in adresses.split(',') if e.strip() != '']

    else:
        if type(adresses).__name__ == 'list' or type(adresses).__name__ == 'tuple':
            try:
                liste = [e.strip() for e in adresses if e.strip() != '']
            except:
                texte = 'Adresse incorrecte, "%s". La liste ou le tuple ne doivent contenir '
                texte += 'que des chaînes de caractères'
                raise ValueError(texte % adresses)

            return liste
        else:
            #   OK, ça risque de lever une autre exception si adresses n'est pas imprimable... OSEF
            texte = 'Adresse incorrecte, "%s". Doit être une chaine de caractères '
            texte += 'ou une liste ou un tuple de str'
            raise ValueError(texte % adresses)


#   ------------------------------------------------------------------------------------------------------------------
def envoyer_message(serveur, sender, to, subject, contenu_texte=None, smtp_user=None, smtp_pwd=None,
                    contenu_html=None, cc=None, bcc=None, files=None, port=None):
    #   1 - quelques vérifications
    #       Le serveur DOIT être un str...
    if type(serveur).__name__ != 'str':
        raise ValueError('Paramètre "server" incorrect. Doit être une chaine de caractères')

    #       ...comme l'expéditeur, ...
    if type(sender).__name__ != 'str':
        raise ValueError('Paramètre "sender" incorrect. Doit être une chaine de caractères')

    #       ...l'objet, ...
    if type(subject).__name__ != 'str':
        raise ValueError('Paramètre "subject" incorrect. Doit être une chaine de caractères')

    #       ...le contenu, qu'il soit plain text...
    if contenu_texte is not None and type(contenu_texte).__name__ != 'str':
        raise ValueError('Paramètre "contenu_texte" incorrect. Doit être une chaine de caractères')

    #       ...ou HTML...
    if contenu_html is not None and type(contenu_html).__name__ != 'str':
        raise ValueError('Paramètre "contenu_html" incorrect. Doit être une chaine de caractères')

    #       S'il est spécifié, le smtp_user doit lui aussi être un str
    if smtp_user is not None and type(smtp_user).__name__ != 'str':
        raise ValueError('Paramètre "smtp_user" incorrect. Doit être une chaine de caractères')

    #       S'il est spécifié, le port doir être un entier
    if port is not None and type(port).__name__ != 'int':
        raise ValueError('Paramètre "port" incorrect. Doit être un entier')

    #   L'argument "files" doit être une liste de str
    if files is not None and type(files).__name__ != 'list':
        raise ValueError('Paramètre "files" incorrect. Doit être une liste')

    #   Allez, on vérifie aussi l'existence des éventuelles PJ
    for f in files or []:
        if type(f).__name__ != 'str':
            raise ValueError('Paramètre "file" incorrect, %s. Doit être une chaine de caractères' % f)

        if not os.path.isfile(f):
            raise EnvironmentError('Le fichier %s n\'existe pas (ou n\'est pas un fichier régulier' % f)

    liste_to = verif_adresses(to)
    liste_cc = verif_adresses(cc)
    liste_bcc = verif_adresses(bcc)

    msg = MIMEMultipart('mixed')

    if contenu_texte:
        part1 = MIMEText(contenu_texte.encode('utf-8'), 'plain', 'utf-8')
        msg.attach(part1)

    if contenu_html:
        part2 = MIMEText(contenu_html.encode('utf-8'), 'html', 'utf-8')
        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part2)

    msg['From'] = sender

    if liste_to:
        msg['To'] = ','.join(liste_to)

    if liste_cc:
        msg['CC'] = ','.join(liste_cc)

    if liste_bcc:
        msg['BCC'] = ','.join(liste_bcc)

    msg['Subject'] = subject

    for f in files or []:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(f, "rb").read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)

    addr_from = sender
    addr_to = []

    if liste_to:
        addr_to += liste_to

    if liste_cc:
        addr_to += liste_cc

    if liste_bcc:
        addr_to += liste_bcc

    if port is None:
        s = smtplib.SMTP(serveur)
    else:
        s = smtplib.SMTP(serveur, port)

    if smtp_user is not None:
        if smtp_pwd is None:
            """
            Juste pour que ça ne plante pas sur AttributeError: 'NoneType' object has no attribute 'encode'.
            Dans le pire de cas on aura un "535, 5.7.8 Error: authentication failed", mais après tout on peut
            imaginer un serveur smtp avec un code utilisateur sans mot de passe...
            """
            smtp_pwd = ''
        s.starttls()
        s.login(smtp_user, smtp_pwd)

    rep = s.sendmail(addr_from, addr_to, msg.as_string())
    s.quit()


#   ------------------------------------------------------------------------------------------------------------------
def EnvoyerMessage(serveur, sender, destinataire, subject, contenuTexte, smtp_user=None, smtp_pwd=None,
                   contenuHTML=None, listeCopies=None, listeBCC=None, files=None):
    """
    Ancienne interface. Conservée pour préserver la compatibilité avec l'existant.
    Ne pas utiliser.
    """
    envoyer_message(serveur, sender, destinataire, subject,  contenu_texte=contenuTexte, smtp_user=smtp_user,
                    smtp_pwd=smtp_pwd, contenu_html=contenuHTML, cc=listeCopies, bcc=listeBCC, files=files)

#   ------------------------------------------------------------------------------------------------------------------
