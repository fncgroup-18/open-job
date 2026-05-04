from flask_login import UserMixin
from datetime import datetime, date
import uuid

_db = None

def init_db(firestore_client):
    global _db
    _db = firestore_client

def get_db():
    if _db is None:
        raise RuntimeError("Firestore not initialized")
    return _db


class Pagination:
    def __init__(self, items, total, page, per_page):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.pages = max(1, (total + per_page - 1) // per_page)
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1 if self.has_prev else None
        self.next_num = page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=3):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
                    (self.page - left_current - 1 < num < self.page + right_current) or
                    num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def _to_dt(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time())
    return val


class User(UserMixin):
    COLLECTION = 'users'

    def __init__(self, doc_id, data):
        self.id = doc_id
        self.name = data.get('name', '')
        self.username = data.get('username', '')
        self.email = data.get('email', '')
        self.password = data.get('password', '')
        self._is_active = data.get('is_active', True)
        self.is_admin = data.get('is_admin', False)
        self.created_at = data.get('created_at') or datetime.utcnow()

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    def to_dict(self):
        return {
            'name': self.name,
            'username': self.username,
            'email': self.email,
            'password': self.password,
            'is_active': self._is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at,
        }

    @classmethod
    def get_by_id(cls, user_id):
        try:
            doc = get_db().collection(cls.COLLECTION).document(str(user_id)).get()
            return cls(doc.id, doc.to_dict()) if doc.exists else None
        except Exception:
            return None

    @classmethod
    def filter_by(cls, **kwargs):
        q = get_db().collection(cls.COLLECTION)
        for k, v in kwargs.items():
            q = q.where(k, '==', v)
        return [cls(d.id, d.to_dict()) for d in q.stream()]

    @classmethod
    def first_where(cls, **kwargs):
        results = cls.filter_by(**kwargs)
        return results[0] if results else None

    @classmethod
    def count(cls):
        return sum(1 for _ in get_db().collection(cls.COLLECTION).stream())

    @classmethod
    def all_recent(cls, limit=5):
        docs = list(get_db().collection(cls.COLLECTION).stream())
        users = [cls(d.id, d.to_dict()) for d in docs]
        users.sort(key=lambda u: u.created_at or datetime.min, reverse=True)
        return users[:limit]

    @classmethod
    def paginate(cls, page=1, per_page=10):
        docs = list(get_db().collection(cls.COLLECTION).stream())
        users = [cls(d.id, d.to_dict()) for d in docs]
        users.sort(key=lambda u: u.created_at or datetime.min, reverse=True)
        total = len(users)
        start = (page - 1) * per_page
        return Pagination(users[start:start + per_page], total, page, per_page)

    def save(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        get_db().collection(self.COLLECTION).document(self.id).set(self.to_dict())
        return self

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Job:
    COLLECTION = 'jobs'

    def __init__(self, doc_id, data):
        self.id = doc_id
        self.is_deleted = data.get('is_deleted', False)
        self.title = data.get('title', '')
        self.company = data.get('company', '')
        self.location = data.get('location', '')
        self.description = data.get('description', '')
        self.requirements = data.get('requirements', '')
        self.salary_range = data.get('salary_range', '')
        self.job_type = data.get('job_type', '')
        self.experience_level = data.get('experience_level', '')
        self.skills = data.get('skills', '')
        self.benefits = data.get('benefits', '')
        self.remote_option = data.get('remote_option', '')
        self.created_at = data.get('created_at') or datetime.utcnow()
        self.updated_at = data.get('updated_at')
        self.deadline = data.get('deadline')
        self.status = data.get('status', 'active')
        self.views_count = data.get('views_count', 0)
        self.applications_count = data.get('applications_count', 0)
        self.user_id = data.get('user_id', '')
        self._author = None

    @property
    def author(self):
        if self._author is None and self.user_id:
            self._author = User.get_by_id(self.user_id)
        return self._author

    def to_dict(self):
        return {
            'is_deleted': self.is_deleted,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'description': self.description,
            'requirements': self.requirements,
            'salary_range': self.salary_range,
            'job_type': self.job_type,
            'experience_level': self.experience_level,
            'skills': self.skills,
            'benefits': self.benefits,
            'remote_option': self.remote_option,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow(),
            'deadline': _to_dt(self.deadline),
            'status': self.status,
            'views_count': self.views_count,
            'applications_count': self.applications_count,
            'user_id': str(self.user_id) if self.user_id else '',
        }

    @classmethod
    def get_by_id(cls, job_id):
        doc = get_db().collection(cls.COLLECTION).document(str(job_id)).get()
        return cls(doc.id, doc.to_dict()) if doc.exists else None

    @classmethod
    def get_or_404(cls, job_id):
        from flask import abort
        job = cls.get_by_id(job_id)
        if job is None:
            abort(404)
        return job

    @classmethod
    def _fetch_all(cls):
        return [cls(d.id, d.to_dict()) for d in get_db().collection(cls.COLLECTION).stream()]

    @classmethod
    def active_recent(cls, limit=6):
        jobs = [j for j in cls._fetch_all() if j.status == 'active' and not j.is_deleted]
        jobs.sort(key=lambda j: j.created_at or datetime.min, reverse=True)
        return jobs[:limit]

    @classmethod
    def active_paginated(cls, page=1, per_page=10):
        jobs = [j for j in cls._fetch_all() if j.status == 'active' and not j.is_deleted]
        jobs.sort(key=lambda j: j.created_at or datetime.min, reverse=True)
        total = len(jobs)
        start = (page - 1) * per_page
        return Pagination(jobs[start:start + per_page], total, page, per_page)

    @classmethod
    def for_user(cls, user_id):
        jobs = [j for j in cls._fetch_all() if j.user_id == str(user_id)]
        jobs.sort(key=lambda j: j.created_at or datetime.min, reverse=True)
        return jobs

    @classmethod
    def search(cls, query='', location='', job_type='', experience='', page=1, per_page=10):
        jobs = [j for j in cls._fetch_all() if j.status == 'active' and not j.is_deleted]
        if query:
            q = query.lower()
            jobs = [j for j in jobs if q in j.title.lower() or q in j.company.lower()
                    or q in j.description.lower() or q in (j.skills or '').lower()]
        if location:
            jobs = [j for j in jobs if location.lower() in j.location.lower()]
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        if experience:
            jobs = [j for j in jobs if j.experience_level == experience]
        jobs.sort(key=lambda j: j.created_at or datetime.min, reverse=True)
        total = len(jobs)
        start = (page - 1) * per_page
        return Pagination(jobs[start:start + per_page], total, page, per_page)

    @classmethod
    def count(cls):
        return sum(1 for _ in get_db().collection(cls.COLLECTION).stream())

    @classmethod
    def count_by_status(cls, status):
        return sum(1 for j in cls._fetch_all() if j.status == status)

    @classmethod
    def all_recent(cls, limit=5):
        jobs = cls._fetch_all()
        jobs.sort(key=lambda j: j.created_at or datetime.min, reverse=True)
        return jobs[:limit]

    @classmethod
    def all_paginated(cls, page=1, per_page=10):
        jobs = cls._fetch_all()
        jobs.sort(key=lambda j: j.created_at or datetime.min, reverse=True)
        total = len(jobs)
        start = (page - 1) * per_page
        return Pagination(jobs[start:start + per_page], total, page, per_page)

    def save(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        get_db().collection(self.COLLECTION).document(self.id).set(self.to_dict())
        return self

    def delete(self):
        get_db().collection(self.COLLECTION).document(self.id).delete()

    def __repr__(self):
        return f"Job('{self.title}' at '{self.company}')"
