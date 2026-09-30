"""Run the logger: python -m netlogger"""
import threading
from http.server import ThreadingHTTPServer

from . import __version__, ami, audio, config, db, schedule
from .web import Handler


def main():
    db.connect()
    print(f"Net Logger {__version__}", flush=True)
    threading.Thread(target=audio.transcriber, daemon=True).start()
    threading.Thread(target=audio.listener, daemon=True).start()
    schedule.start()
    if config.NODE_CONTROL:
        print(f"node control on: logger node {config.LOGGER_NODE} via {config.AMI_HOST}:{config.AMI_PORT}", flush=True)
        if config.AUTO_CONNECT and config.DEFAULT_NODE:
            threading.Thread(target=ami.auto_connect_loop, daemon=True).start()
    else:
        print("node control off (AMI_HOST not set)", flush=True)
    print(f"dashboard on http://{config.HTTP_HOST}:{config.HTTP_PORT}", flush=True)
    ThreadingHTTPServer((config.HTTP_HOST, config.HTTP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
