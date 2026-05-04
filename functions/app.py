import os
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, Email, Regexp
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import User, Job

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'


def create_app():
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(32).hex()),
        TEMPLATES_AUTO_RELOAD=True,
        WTF_CSRF_ENABLED=True,
    )

    bcrypt.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    from jobs import jobs
    from admin import admin as admin_blueprint
    app.register_blueprint(jobs)
    app.register_blueprint(admin_blueprint)

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return dict(current_user=current_user, now=datetime.now)

    class RegisterForm(FlaskForm):
        name = StringField('Full Name',
                           validators=[InputRequired(), Length(min=2, max=100)],
                           render_kw={"placeholder": "Full Name", "class": "form-input"})
        username = StringField('Username',
                               validators=[
                                   InputRequired(), Length(min=4, max=20),
                                   Regexp(r'^[\w]+$', message="Username must contain only letters, numbers and underscores")
                               ],
                               render_kw={"placeholder": "Username", "class": "form-input"})
        email = StringField('Email',
                            validators=[InputRequired(), Email()],
                            render_kw={"placeholder": "Email", "class": "form-input"})
        password = PasswordField('Password',
                                 validators=[InputRequired(), Length(min=12, max=72)],
                                 render_kw={"placeholder": "Password", "class": "form-input"})
        submit = SubmitField("Register", render_kw={"class": "submit-btn"})

        def validate_username(self, username):
            if User.first_where(username=username.data):
                raise ValidationError("That username already exists. Please choose a different one.")

        def validate_email(self, email):
            if User.first_where(email=email.data):
                raise ValidationError("That email is already registered. Please use a different one.")

    class LoginForm(FlaskForm):
        username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                               render_kw={"placeholder": "Username", "class": "form-input"})
        password = PasswordField(validators=[InputRequired(), Length(min=12, max=72)],
                                 render_kw={"placeholder": "Password", "class": "form-input"})
        submit = SubmitField("Login", render_kw={"class": "submit-btn"})

    @app.route('/')
    def index():
        admin_exists = User.first_where(is_admin=True)
        if not admin_exists:
            return redirect(url_for('admin_setup'))
        latest_jobs = Job.active_recent(limit=6)
        return render_template('index.html', latest_jobs=latest_jobs)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            hashed = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            User(None, {
                'name': form.name.data,
                'username': form.username.data,
                'email': form.email.data,
                'password': hashed,
                'is_admin': False,
                'is_active': True,
            }).save()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.first_where(username=form.username.data)
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                flash('Welcome back!', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid username or password. Please try again.', 'error')
        return render_template('login.html', form=form)

    @app.route('/logout', methods=['GET', 'POST'])
    @login_required
    def logout():
        session.pop('admin_authenticated', None)
        logout_user()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('index'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user_jobs = Job.for_user(current_user.id)
        return render_template('dashboard.html', name=current_user.username, jobs=user_jobs)

    @app.route('/admin-setup', methods=['GET', 'POST'])
    def admin_setup():
        if User.first_where(is_admin=True):
            return redirect(url_for('index'))
        form = RegisterForm()
        if form.validate_on_submit():
            hashed = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            User(None, {
                'name': form.name.data,
                'username': form.username.data,
                'email': form.email.data,
                'password': hashed,
                'is_admin': True,
                'is_active': True,
            }).save()
            flash('Admin user created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('admin_setup.html', form=form)

    return app
