#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import hashlib


class SQLAlias():
    aliases = {}
    text_hash = ''

    def __init__(self):
        pass

    def set_alias(self, alias, name):
        if self.aliases.get(alias, '') != name:
            self.aliases[alias] = name

    def get_alias(self, alias):
        return self.aliases.get(alias, '')

    def alias_list(self):
        for alias in self.aliases:
            print('[%s] => <%s>' % (self.aliases[alias], alias))

    def set_text_hash(self, text):
        text_hash = hashlib.md5(text).hexdigest()
        if text_hash != self.text_hash:
            self.text_hash = text_hash
            return True
        else:
            return False

    def get_text_hash(self, text):
        return self.text_hash
