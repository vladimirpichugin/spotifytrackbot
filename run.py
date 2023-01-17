# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import threading
import time

import main
import console


if __name__ == "__main__":
    main.logger.debug("Initializing bot polling..")
    thread_bot = threading.Thread(target=main.bot_polling)
    thread_bot.setName("BotThread")
    thread_bot.daemon = True
    thread_bot.start()

    thread_flask = threading.Thread(target=main.webserver_daemon)
    thread_flask.setName("WebThread")
    thread_flask.daemon = True
    thread_flask.start()

    console_thread = threading.Thread(target=console.console_thread)
    console_thread.setName("ConsoleThread")
    console_thread.daemon = True
    console_thread.start()

    # Поддерживать работу основной программы, пока бот работает.
    while True:
        try:
            if not thread_bot.is_alive():
                main.logger.error("Bot polling pool is not alive, shutting down..")
                break

            time.sleep(10)
        except KeyboardInterrupt:
            main.logger.info("Shutting down..")
            break
