import firebase_admin
from firebase_admin import firestore
from firebase_functions import https_fn
from models import init_db
from app import create_app

flask_app = create_app()
_db_initialized = False


def _ensure_db():
    global _db_initialized
    if not _db_initialized:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        init_db(firestore.client())
        _db_initialized = True


@https_fn.on_request(timeout_sec=60, memory=512, invoker="public")
def openjobs(req: https_fn.Request) -> https_fn.Response:
    _ensure_db()
    with flask_app.request_context(req.environ):
        return flask_app.full_dispatch_request()
