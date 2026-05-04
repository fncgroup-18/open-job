from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user, login_user, logout_user
from functools import wraps
from models import db, User, Job
from app import bcrypt

admin = Blueprint('admin_dashboard', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to ensure route is only accessible by authenticated admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_dashboard.login'))
        
        if not current_user.is_admin:
            flash('⚠️ Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
            
        if not session.get('admin_authenticated'):
            flash('Please authenticate as an administrator.', 'error')
            return redirect(url_for('admin_dashboard.login'))
            
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    # If already logged in as admin and authenticated, redirect to dashboard
    if current_user.is_authenticated and current_user.is_admin and session.get('admin_authenticated'):
        return redirect(url_for('admin_dashboard.dashboard'))

    # If logged in but not as admin, log them out first
    if current_user.is_authenticated and not current_user.is_admin:
        logout_user()
        flash('Please log in with admin credentials.', 'info')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, is_admin=True).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            session['admin_authenticated'] = True
            session.permanent = True  # Use permanent session
            flash('✨ Welcome to the admin dashboard!', 'success')
            return redirect(url_for('admin_dashboard.dashboard'))
        else:
            flash('Invalid admin credentials.', 'error')

    return render_template('admin/login.html')

@admin.route('/logout')
def logout():
    """Admin logout."""
    session.pop('admin_authenticated', None)
    if current_user.is_authenticated:
        logout_user()
    flash('You have been logged out of the admin panel.', 'info')
    return redirect(url_for('admin_dashboard.login'))

@admin.route('/')
@admin_required
def dashboard():
    """Admin dashboard with platform metrics."""
    stats = {
        'total_users': User.query.count(),
        'total_jobs': Job.query.count(),
        'active_jobs': Job.query.filter_by(status='active').count(),
        'pending_jobs': Job.query.filter_by(status='pending').count()
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats,
                         recent_users=recent_users,
                         recent_jobs=recent_jobs)

@admin.route('/users')
@admin_required
def manage_users():
    """User management interface."""
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=10)
    return render_template('admin/users.html', users=users)

@admin.route('/jobs')
@admin_required
def manage_jobs():
    """Job listing management interface."""
    page = request.args.get('page', 1, type=int)
    jobs = Job.query.paginate(page=page, per_page=10)
    return render_template('admin/jobs.html', jobs=jobs)

@admin.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status."""
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('⚠️ Cannot modify admin user status.', 'error')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'✨ User {user.username} has been {status}.', 'success')
    return redirect(url_for('admin_dashboard.manage_users'))

@admin.route('/jobs/<int:job_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_job_status(job_id):
    """Toggle job active status."""
    job = Job.query.get_or_404(job_id)
    job.status = 'active' if job.status == 'inactive' else 'inactive'
    db.session.commit()
    flash(f'✨ Job "{job.title}" status updated to {job.status}.', 'success')
    return redirect(url_for('admin_dashboard.manage_jobs'))
