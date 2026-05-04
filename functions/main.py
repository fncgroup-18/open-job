import firebase_admin
from firebase_admin import firestore
from firebase_functions import https_fn, scheduler_fn
from models import init_db, Job
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


@scheduler_fn.on_schedule(schedule="every 24 hours", memory=512, timeout_sec=120)
def auto_import_jobs(event: scheduler_fn.ScheduledEvent) -> None:
    """Runs daily: imports new jobs based on saved search terms in Firestore."""
    _ensure_db()
    from import_jobs import search_jobs
    from datetime import datetime, timedelta

    db = firestore.client()
    settings_doc = db.collection('settings').document('auto_import').get()
    if not settings_doc.exists:
        return

    config = settings_doc.to_dict()
    if not config.get('enabled'):
        return

    search_terms = config.get('search_terms', [])
    location = config.get('location', '')
    admin_user_id = config.get('admin_user_id', '')
    deadline = datetime.utcnow() + timedelta(days=30)

    total_imported = 0
    for term in search_terms:
        try:
            results = search_jobs(term, location or 'United Kingdom')
            for data in results:
                source_id = data.get('source_id', '')
                if source_id and Job.source_id_exists(source_id):
                    continue
                Job(None, {
                    'title': data.get('title', ''),
                    'company': data.get('company', ''),
                    'location': data.get('location', ''),
                    'description': data.get('description', ''),
                    'requirements': data.get('requirements', ''),
                    'salary_range': data.get('salary_range', ''),
                    'job_type': data.get('job_type', 'Full-time'),
                    'experience_level': data.get('experience_level', 'Mid'),
                    'skills': data.get('skills', ''),
                    'benefits': data.get('benefits', ''),
                    'remote_option': data.get('remote_option', 'On-site'),
                    'source_id': source_id,
                    'source': data.get('source', ''),
                    'source_url': data.get('source_url', ''),
                    'deadline': deadline,
                    'status': 'active',
                    'user_id': admin_user_id,
                }).save()
                total_imported += 1
        except Exception:
            pass  # log silently, continue with next term

    db.collection('settings').document('auto_import').update({
        'last_run': datetime.utcnow(),
        'last_imported': total_imported,
    })
