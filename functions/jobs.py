from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from models import Job
from forms import JobForm

jobs = Blueprint('jobs', __name__)


@jobs.route('/jobs')
def job_board():
    page = request.args.get('page', 1, type=int)
    pagination = Job.active_paginated(page=page, per_page=10)
    return render_template('jobs/board.html', jobs=pagination)


@jobs.route('/jobs/create', methods=['GET', 'POST'])
@login_required
def create_job():
    if not current_user.is_admin:
        flash('Only administrators can post job listings.', 'error')
        return redirect(url_for('jobs.job_board'))
    form = JobForm()
    if form.validate_on_submit():
        Job(None, {
            'title': form.title.data,
            'company': form.company.data,
            'location': form.location.data,
            'description': form.description.data,
            'requirements': form.requirements.data,
            'salary_range': form.salary_range.data,
            'job_type': form.job_type.data,
            'experience_level': form.experience_level.data,
            'skills': form.skills.data,
            'benefits': form.benefits.data,
            'deadline': form.deadline.data,
            'user_id': str(current_user.id),
            'status': 'active',
        }).save()
        flash('Job listing created successfully!', 'success')
        return redirect(url_for('jobs.job_board'))
    return render_template('jobs/create.html', form=form)


@jobs.route('/jobs/<job_id>')
def view_job(job_id):
    job = Job.get_or_404(job_id)
    return render_template('jobs/view.html', job=job)


@jobs.route('/jobs/<job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    job = Job.get_or_404(job_id)
    if job.user_id != str(current_user.id):
        flash('You do not have permission to edit this job listing.', 'error')
        return redirect(url_for('jobs.job_board'))
    if request.method == 'POST':
        job.title = request.form.get('title', job.title)
        job.company = request.form.get('company', job.company)
        job.location = request.form.get('location', job.location)
        job.description = request.form.get('description', job.description)
        job.requirements = request.form.get('requirements', job.requirements)
        job.salary_range = request.form.get('salary_range', job.salary_range)
        job.job_type = request.form.get('job_type', job.job_type)
        job.experience_level = request.form.get('experience_level', job.experience_level)
        job.skills = request.form.get('skills', job.skills)
        deadline_str = request.form.get('deadline')
        if deadline_str:
            job.deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        job.save()
        flash('Job listing updated successfully!', 'success')
        return redirect(url_for('jobs.view_job', job_id=job.id))
    return render_template('jobs/edit.html', job=job)


@jobs.route('/jobs/<job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    job = Job.get_or_404(job_id)
    if job.user_id != str(current_user.id):
        flash('You do not have permission to delete this job listing.', 'error')
        return redirect(url_for('jobs.job_board'))
    job.delete()
    flash('Job listing deleted successfully!', 'success')
    return redirect(url_for('jobs.job_board'))


@jobs.route('/jobs/search')
def search_jobs():
    query = request.args.get('q', '')
    location = request.args.get('location', '')
    job_type = request.args.get('type', '')
    experience = request.args.get('experience', '')
    page = request.args.get('page', 1, type=int)
    pagination = Job.search(
        query=query, location=location, job_type=job_type,
        experience=experience, page=page, per_page=10
    )
    return render_template('jobs/search.html', jobs=pagination, query=query,
                           location=location, job_type=job_type, experience=experience)
