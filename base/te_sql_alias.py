#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import hashlib
from . import tsql_keywords


class SQLAlias():
    aliases = {}
    text_hash = ''

    def __init__(self):
        pass

    def is_valid_alias(self, val):
        if val.startswith('@'):
            return False
        if val.upper() in tsql_keywords.all_keywords:
            return False
        # print('"{}" is valid alias name'.format(val))
        return True

    def set_alias(self, alias, name):
        if self.is_valid_alias(alias) and self.is_valid_alias(name) and alias not in self.aliases:
            self.aliases[alias] = name

    def get_alias(self, alias):
        return self.aliases.get(alias, '')

    def alias_list(self):
        for alias in self.aliases:
            print('[{table}] => <{alias}>'.format(table=self.aliases[alias], alias=alias))

    def set_text_hash(self, text):
        text_hash = hashlib.md5(text).hexdigest()
        if text_hash != self.text_hash:
            self.text_hash = text_hash
            return True
        else:
            return False

    def get_text_hash(self, text):
        return self.text_hash
