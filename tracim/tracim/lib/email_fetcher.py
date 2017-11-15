# -*- coding: utf-8 -*-

import sys
import time
import imaplib
import datetime
import json
from typing import Union
from email.message import Message
from email.header import Header, decode_header, make_header
from email.utils import parseaddr, parsedate_tz, mktime_tz
from email import message_from_bytes

import requests

from tracim.controllers.events import VALID_TOKEN_VALUE


TRACIM_SPECIAL_KEY_HEADER = "X-Tracim-Key"


def str_header(header: Header) -> str:
    return str(make_header(decode_header(header)))


def decode_mail(msg: Message)-> dict:
    """
    Get useful header and body content and decode from Message
    :param msg:
    :return:
    """
    mail_data = {}

    try:
        mail_data['subject'] = str_header(msg['subject'])
        mail_data['msg_id'] = str_header(msg['Message-ID'])
        mail_data['from'] = parseaddr(msg['From'])[1]
        # Reply key
        mail_data['to'] = parseaddr(msg['To'])[1]

        mail_data['references'] = parseaddr(msg['References'])[1]
        if TRACIM_SPECIAL_KEY_HEADER in msg:
            mail_data[TRACIM_SPECIAL_KEY_HEADER] = str_header(msg[TRACIM_SPECIAL_KEY_HEADER])  # nopep8
        # date
        date_h = str_header(msg['Date'])
        date_tuple = parsedate_tz(date_h)

        mail_data['date'] = datetime.datetime.fromtimestamp(
            mktime_tz(date_tuple)
        )

    except Exception:
        # TODO: exception -> mail not correctly formatted
        return {}
    # TODO : msg.get_body look like the best way to get body
    # but it's a new feature now (08112017).
    for part in msg.walk():
        if not part.get_content_type() == "text/plain":
            continue
        else:
            # TODO: check if decoding is working correctly
            charset = part.get_content_charset('iso-8859-1')
            mail_data['body'] = part.get_payload(decode=True).decode(charset)
            break
    return mail_data


def get_tracim_content_key(mail_data: dict) -> Union[str, None]:

    """ Link mail_data dict to tracim content
    First try checking special header, them check 'to' header
    and finally check first(oldest) mail-id of 'references' header
    """
    key = None
    if TRACIM_SPECIAL_KEY_HEADER in mail_data:
        key = mail_data[TRACIM_SPECIAL_KEY_HEADER]
    if key is None and 'to' in mail_data:
        key = find_key_from_mail_adress(mail_data['to'])
    if key is None and 'references' in mail_data:
        mail_adress = mail_data['references']
        key = find_key_from_mail_adress(mail_adress)
    return key


def find_key_from_mail_adress(mail_address: str) -> Union[str, None]:
    """ Parse mail_adress-like string
    to retrieve key.

    :param mail_address: user+key@something like string
    :return: key
    """
    username = mail_address.split('@')[0]
    username_data = username.split('+')
    if len(username_data) == 2:
        key = username_data[1]
    else:
        key = None
    return key


class MailFetcher(object):

    def __init__(self, host, port, user, password, folder, delay, endpoint):
        self._connection = None
        self._mails = []
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.folder = folder
        self.delay = delay
        self.endpoint = endpoint

        self._is_active = True

    def run(self) -> None:
        while self._is_active:
            time.sleep(self.delay)
            self._connect()
            self._fetch()
            self._notify_tracim()
            self._disconnect()

    def stop(self) -> None:
        self._is_active = False

    def _connect(self) -> None:
        # verify if connected ?
        if self._connection:
            self._disconnect()
        # TODO: Support unencrypted connection ?
        # TODO: Support keyfile,certfile ?
        self._connection = imaplib.IMAP4_SSL(self.host, self.port)
        try:
            self._connection.login(self.user, self.password)
        except Exception as e:
            log = 'IMAP login error: {}'
            logger.debug(self, log.format(e.__str__()))

    def _disconnect(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection.logout()
            self._connection = None

    def _fetch(self) -> None:
        """
        Get news message from mailbox
        """

        # select mailbox
        rv, data = self._connection.select(self.folder)
        if rv == 'OK':
            # get mails
            # TODO: search only new mail or drop/moved the added one ?
            rv, data = self._connection.search(None, "(UNSEEN)")
            if rv == 'OK':
                # get mail content
                for num in data[0].split():
                    rv, data = self._connection.fetch(num, '(RFC822)')
                    if rv == 'OK':
                        msg = message_from_bytes(data[0][1])
                        self._mails.append(msg)
                    else:
                        # TODO : Check best debug value
                        log = 'IMAP : Unable to get mail : {}'
                        logger.debug(self, log.format(str(rv)))
            else:
                # TODO : Distinct error from empty mailbox ?
                pass
        else:
            # TODO : Check best debug value
            log = 'IMAP : Unable to open mailbox : {}'
            logger.debug(self, log.format(str(rv)))

    def _notify_tracim(self) -> None:
        while self._mails:
            mail = self._mails.pop()
            decoded_mail = decode_mail(mail)
            msg = {"token": VALID_TOKEN_VALUE,
                   "user_mail": decoded_mail['from'],
                   "content_id": get_tracim_content_key(decoded_mail),
                   "payload": {
                       "content": decoded_mail['body'],
                   }}

            requests.post(self.endpoint, json=msg)
            pass
