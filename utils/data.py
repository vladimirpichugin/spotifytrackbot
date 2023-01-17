# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import datetime
import dateutil.parser

from bson.objectid import ObjectId


class SDict(dict):
    def __init__(self, *args, **kwargs):
        self.changed = False
        super().__init__(*args, **kwargs)

    def __getitem__(self, item):
        return super().__getitem__(item)

    def __setitem__(self, item, value):
        try:
            if super().__getitem__(item) != value:
                self.changed = True
        except KeyError:
            self.changed = True

        return super().__setitem__(item, value)

    def __delitem__(self, item):
        self.changed = True
        super().__delitem__(item)

    def getraw(self, item, default=None):
        try:
            return super().__getitem__(item)
        except KeyError:
            return default

    def setraw(self, item, value):
        super().__setitem__(item, value)

    def delraw(self, item):
        super().__delitem__(item)


class Client(SDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.id = self.getraw('_id')

    def get_id(self) -> int:
        return self.id

    @staticmethod
    def create(data):
        return Client(data)
