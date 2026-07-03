# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import pymongo
from telebot.types import User

from utils.data import *
from utils.logging import logger


class Storage:
    def __init__(self, connect, database, collections, server_selection_timeout_ms=5000):
        self.mongo_client = pymongo.MongoClient(
            connect,
            serverSelectionTimeoutMS=server_selection_timeout_ms,
            authSource='admin',
            tls=True,
            tlsAllowInvalidCertificates=True,
            tz_aware=True
        )
        self.db = self.mongo_client.get_database(database)
        self.clients = self.db.get_collection(collections.get('clients'))
        self.clients.create_index("key", sparse=True)

    def get_client(self, user: User) -> Client:
        data = self.get_data(self.clients, user.id)

        if not data:
            #logger.debug(f'User <{user.id}:{user.username}> not found.')
            data = SDict({'_id': user.id})

        client = Client(data)

        return client

    def get_client_by_key(self, key):
        data = self.get_data(self.clients, key, "key")

        if not data:
            return None

        client = Client(data)

        return client

    def get_clients(self):
        data = self.clients.find()

        clients = []
        for _ in data:
            clients.append(Client(_))

        return clients

    def save_client(self, client: Client, user=None) -> bool:
        if not user or type(user) is not User:
            user = User(id=client.id, is_bot=False, first_name='Unknown', username='Empty')

        if not client.changed:
            logger.debug(f'Client <{user.id}:{user.username}> already saved, data not changed.')
            return True

        save_result = self.save_data(self.clients, user.id, client)

        if save_result:
            client.changed = False
            logger.debug(f'Client <{user.id}:{user.username}> saved, result: {save_result}')
            return True

        logger.error(f'Client <{user.id}:{user.username}> not saved, result: {save_result}')

        return False

    @staticmethod
    def get_data(c: pymongo.collection.Collection, value, name="_id"):
        data = c.find_one({name: value})

        if data:
            return SDict(data)

        return None

    @staticmethod
    def save_data(c: pymongo.collection.Collection, value, data: SDict, name="_id"):
        payload = dict(data)
        payload[name] = value

        operation = c.replace_one({name: value}, payload, upsert=True)
        result = operation.raw_result if operation else None

        return result
