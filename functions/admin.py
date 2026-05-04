from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import current_user, login_user, logout_user
from functools import wraps
from models import User, Job
from app import bcrypt

admin = Blueprint('admin_dashboard', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_dashboard.login'))
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        if not session.get('admin_authenticated'):
            flash('Please authenticate as an administrator.', 'error')
            return redirect(url_for('admin_dashboard.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and current_user.is_admin and session.get('admin_authenticated'):
        return redirect(url_for('admin_dashboard.dashboard'))
    if current_user.is_authenticated and not current_user.is_admin:
        logout_user()
        flash('Please log in with admin credentials.', 'info')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.first_where(email=email, is_admin=True)
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            session['admin_authenticated'] = True
            session.permanent = True
            flash('Welcome to the admin dashboard!', 'success')
            return redirect(url_for('admin_dashboard.dashboard'))
        flash('Invalid admin credentials.', 'error')
    return render_template('admin/login.html')


@admin.route('/logout')
def logout():
    session.pop('admin_authenticated', None)
    if current_user.is_authenticated:
        logout_user()
    flash('You have been logged out of the admin panel.', 'info')
    return redirect(url_for('admin_dashboard.login'))


@admin.route('/')
@admin_required
def dashboard():
    stats = {
        'total_users': User.count(),
        'total_jobs': Job.count(),
        'active_jobs': Job.count_by_status('active'),
        'pending_jobs': Job.count_by_status('pending'),
    }
    return render_template('admin/dashboard.html',
                           stats=stats,
                           recent_users=User.all_recent(limit=5),
                           recent_jobs=Job.all_recent(limit=5))


@admin.route('/users')
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    return render_template('admin/users.html', users=User.paginate(page=page, per_page=10))


@admin.route('/jobs')
@admin_required
def manage_jobs():
    page = request.args.get('page', 1, type=int)
    return render_template('admin/jobs.html', jobs=Job.all_paginated(page=page, per_page=10))


@admin.route('/users/<user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = User.get_by_id(user_id)
    if user is None:
        flash('User not found.', 'error')
    elif user.is_admin:
        flash('Cannot modify admin user status.', 'error')
    else:
        user.is_active = not user.is_active
        user.save()
        flash(f'User {user.username} has been {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin_dashboard.manage_users'))


@admin.route('/jobs/<job_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_job_status(job_id):
    job = Job.get_by_id(job_id)
    if job is None:
        flash('Job not found.', 'error')
    else:
        job.status = 'active' if job.status == 'inactive' else 'inactive'
        job.save()
        flash(f'Job "{job.title}" status updated to {job.status}.', 'success')
    return redirect(url_for('admin_dashboard.manage_jobs'))
