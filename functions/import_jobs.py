import os
import requests
from datetime import datetime

RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', '')
_HOST = "jsearch.p.rapidapi.com"

_TYPE_MAP = {
    'FULLTIME': 'Full-time',
    'PARTTIME': 'Part-time',
    'CONTRACTOR': 'Contract',
    'INTERN': 'Internship',
}


def search_jobs(query, location='', num_pages=1, date_posted='month'):
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY not configured.")

    search_q = f"{query} in {location}" if location else query
    try:
        resp = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": _HOST},
            params={"query": search_q, "page": "1", "num_pages": str(num_pages),
                    "date_posted": date_posted},
            timeout=15,
        )
        resp.raise_for_status()
        return [_format(j) for j in resp.json().get('data', [])]
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        if code == 429:
            raise ValueError("API rate limit reached. Try again later or upgrade your RapidAPI plan.")
        if code == 403:
            raise ValueError("Invalid RapidAPI key. Check your RAPIDAPI_KEY setting.")
        raise ValueError(f"API error {code}: {e}")
    except requests.exceptions.Timeout:
        raise ValueError("Request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Network error: {e}")


def _format(raw):
    highlights = raw.get('job_highlights') or {}
    qualifications = highlights.get('Qualifications') or []
    benefits = highlights.get('Benefits') or []

    parts = [raw.get('job_city', ''), raw.get('job_state', ''), raw.get('job_country', '')]
    location = ', '.join(p for p in parts if p) or ('Remote' if raw.get('job_is_remote') else 'Unknown')

    lo, hi = raw.get('job_min_salary'), raw.get('job_max_salary')
    curr = raw.get('job_salary_currency', '$')
    period = (raw.get('job_salary_period') or 'YEAR').lower()[:2]
    if lo and hi:
        salary = f"{curr}{int(lo):,} - {curr}{int(hi):,}/{period}"
    elif lo:
        salary = f"{curr}{int(lo):,}+/{period}"
    else:
        salary = ''

    skills = raw.get('job_required_skills') or []

    apply_link = raw.get('job_apply_link') or ''
    source = 'linkedin' if 'linkedin' in apply_link.lower() else (
             'indeed' if 'indeed' in apply_link.lower() else 'other')

    posted_raw = raw.get('job_posted_at_datetime_utc', '')
    try:
        posted_at = datetime.fromisoformat(posted_raw.replace('Z', '+00:00')) if posted_raw else datetime.utcnow()
    except ValueError:
        posted_at = datetime.utcnow()

    return {
        'source_id': raw.get('job_id', ''),
        'source': source,
        'source_url': apply_link,
        'title': raw.get('job_title', ''),
        'company': raw.get('employer_name', ''),
        'company_logo': raw.get('employer_logo') or '',
        'location': location,
        'description': raw.get('job_description', ''),
        'requirements': '\n'.join(qualifications) if qualifications else '',
        'job_type': _TYPE_MAP.get(raw.get('job_employment_type', ''), 'Full-time'),
        'experience_level': 'Mid',
        'salary_range': salary,
        'skills': ', '.join(skills) if skills else '',
        'benefits': '\n'.join(benefits) if benefits else '',
        'remote_option': 'Remote' if raw.get('job_is_remote') else 'On-site',
        'posted_at': posted_at,
    }
