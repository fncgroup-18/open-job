import os
import requests
from datetime import datetime

RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', '')
_HOST = "linkedin-job-search-api.p.rapidapi.com"
_BASE = f"https://{_HOST}"

_TYPE_MAP = {
    'full-time': 'Full-time', 'fulltime': 'Full-time',
    'part-time': 'Part-time', 'parttime': 'Part-time',
    'contract': 'Contract', 'contractor': 'Contract',
    'internship': 'Internship', 'intern': 'Internship',
    'temporary': 'Contract', 'volunteer': 'Part-time',
}

_LEVEL_MAP = {
    'entry': 'Entry', 'entry level': 'Entry', 'junior': 'Entry', 'associate': 'Entry',
    'mid': 'Mid', 'mid-senior level': 'Mid', 'mid level': 'Mid',
    'senior': 'Senior', 'director': 'Senior', 'executive': 'Senior', 'manager': 'Senior',
}


def search_jobs(title_filter, location_filter='United Kingdom', offset=0):
    """Search LinkedIn jobs via the linkedin-job-search-api on RapidAPI."""
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY not configured.")

    try:
        resp = requests.get(
            f"{_BASE}/active-jb-1h",
            headers={
                "Content-Type": "application/json",
                "x-rapidapi-host": _HOST,
                "x-rapidapi-key": RAPIDAPI_KEY,
            },
            params={
                "offset": str(offset),
                "title_filter": title_filter,
                "location_filter": location_filter,
                "description_type": "text",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict) and data.get('message'):
            msg = data['message']
            if 'not subscribed' in msg.lower():
                raise ValueError(
                    "Not subscribed to this API. Go to rapidapi.com → search "
                    "'LinkedIn Job Search API' → subscribe to the free plan."
                )
            raise ValueError(f"API error: {msg}")

        jobs = data if isinstance(data, list) else data.get('data', data.get('jobs', []))
        return [_format(j) for j in jobs]

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        if code == 429:
            raise ValueError("Rate limit reached. Try again later or upgrade your RapidAPI plan.")
        if code == 403:
            raise ValueError("Invalid or unauthorised RapidAPI key.")
        raise ValueError(f"API error {code}: {e}")
    except requests.exceptions.Timeout:
        raise ValueError("Request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Network error: {e}")


def _get(raw, *keys, default=''):
    """Try multiple possible field names, return first match."""
    for k in keys:
        v = raw.get(k)
        if v is not None and v != '':
            return v
    return default


def _format(raw):
    title = _get(raw, 'title', 'job_title', 'position')
    company = _get(raw, 'company', 'company_name', 'employer', 'organization')
    location = _get(raw, 'location', 'job_location', 'city')
    description = _get(raw, 'description', 'job_description', 'summary')
    apply_url = _get(raw, 'url', 'apply_url', 'job_url', 'link', 'linkedin_url')
    job_id = _get(raw, 'id', 'job_id', 'listing_id')
    emp_type = str(_get(raw, 'employment_type', 'job_type', 'contract_type', default='Full-time')).lower()
    seniority = str(_get(raw, 'seniority_level', 'level', 'experience_level', default='')).lower()
    salary_raw = _get(raw, 'salary', 'salary_range', 'compensation', default='')
    skills_raw = _get(raw, 'skills', 'required_skills', 'job_functions', 'function', default='')
    industries = _get(raw, 'industries', 'industry', default='')
    company_logo = _get(raw, 'company_logo', 'logo', 'company_logo_url', default='')
    posted_raw = _get(raw, 'date', 'date_posted', 'posted_at', 'published_at', default='')

    job_type = _TYPE_MAP.get(emp_type, 'Full-time')
    exp_level = 'Entry'
    for key, val in _LEVEL_MAP.items():
        if key in seniority:
            exp_level = val
            break

    if isinstance(salary_raw, dict):
        lo = salary_raw.get('min') or salary_raw.get('from')
        hi = salary_raw.get('max') or salary_raw.get('to')
        curr = salary_raw.get('currency', '£')
        salary = f"{curr}{int(lo):,} - {curr}{int(hi):,}" if lo and hi else (f"{curr}{int(lo):,}+" if lo else '')
    else:
        salary = str(salary_raw) if salary_raw else ''

    if isinstance(skills_raw, list):
        skills = ', '.join(str(s) for s in skills_raw)
    elif isinstance(industries, list):
        skills = ', '.join(str(s) for s in industries)
    else:
        skills = str(skills_raw or industries or '')

    try:
        if posted_raw:
            posted_at = datetime.fromisoformat(str(posted_raw).replace('Z', '+00:00'))
        else:
            posted_at = datetime.utcnow()
    except (ValueError, TypeError):
        posted_at = datetime.utcnow()

    is_remote = 'remote' in str(location).lower() or 'remote' in str(title).lower()

    return {
        'source_id': str(job_id),
        'source': 'linkedin',
        'source_url': str(apply_url),
        'title': str(title),
        'company': str(company),
        'company_logo': str(company_logo),
        'location': str(location),
        'description': str(description),
        'requirements': '',
        'job_type': job_type,
        'experience_level': exp_level,
        'salary_range': salary,
        'skills': skills,
        'benefits': '',
        'remote_option': 'Remote' if is_remote else 'On-site',
        'posted_at': posted_at,
    }
