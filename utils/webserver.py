# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
from flask import Flask, request, redirect, Response, send_from_directory, abort, request_started, request_finished, got_request_exception, request_tearing_down, make_response

import time
import logging
import json

from utils import logger

from settings import Settings


class WebServer:
    @staticmethod
    def ok(response=None, status=200):
        try:
            return Response(
                response=str(response),
                status=status,
                headers=Settings.WEB_HEADERS,
                content_type=Settings.WEB_CONTENT_TYPE,
                direct_passthrough=True
            )
        except:
            logger.error("Unexpected error occurred while creating Response (failed), connection aborted.",
                         exc_info=True)
            return abort(500)  # Internal Server Error

    @staticmethod
    def failed(response=None, status=400):
        logger.debug(response)

        try:
            return Response(
                response=str(response),
                status=status,
                headers=Settings.WEB_HEADERS,
                content_type=Settings.WEB_CONTENT_TYPE,
                direct_passthrough=True
            )
        except:
            logger.error("Unexpected error occurred while creating Response (failed), connection aborted.",
                         exc_info=True)
            return abort(500)  # Internal Server Error

    @staticmethod
    def log_request_state(req, resp=None, error=None) -> None:
        message = "{event} {remote_addr} {protocol}: \"{http_method} {path}\"{http_status}{error}".format(
            event="RESPONSE for" if resp else "REQUEST from",
            protocol=req.environ.get('SERVER_PROTOCOL'),
            remote_addr=req.headers.get('X-Real-IP', req.remote_addr),
            http_method=req.method,
            path=req.path,
            http_status=" — " + resp.status if resp else "",
            error=" — " + error if error else ""
        )

        if error:
            logger.error(message)
        else:
            logger.info(message)

    @staticmethod
    def before_request(sender, **extra):
        WebServer.log_request_state(req=request)

    @staticmethod
    def after_request(sender, response, **extra):
        WebServer.log_request_state(req=request, resp=response)

    @staticmethod
    def exception_request(sender, exception, **extra):
        pass

    @staticmethod
    def down_request(sender, **extra):
        pass

    def get_app(self):
        app = Flask('spotifytrackbot')

        # Отключает внутренние логи Flask.
        logging.getLogger('werkzeug').setLevel(logging.DEBUG if Settings.WERKZEUG_LOGS else logging.ERROR)

        # Отключает сортировку ключей при парсинге JSON-строки.
        app.config['JSON_SORT_KEYS'] = False

        app.config['TESTING'] = False

        request_started.connect(self.before_request, app)
        request_finished.connect(self.after_request, app)
        request_tearing_down.connect(self.down_request, app)
        got_request_exception.connect(self.exception_request, app)

        @app.errorhandler(400)
        @app.errorhandler(404)
        def codes_400(cause=None):
            logger.error("Returned Bad request (from errorhandler codes_400).")
            #if cause:
            #    logger.debug(cause)
            return self.failed("Bad request", 400)

        @app.errorhandler(500)
        def code_500(cause=None):
            logger.error("Returned Internal Server Error (from errorhandler code_500).")
            if cause:
                logger.debug(cause)
            return self.failed("Internal Server Error", 500)

        return app
