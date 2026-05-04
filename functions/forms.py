from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, DateField
from wtforms.validators import InputRequired, Length, ValidationError, Email, Regexp


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
        from models import User
        if User.first_where(username=username.data):
            raise ValidationError("That username already exists. Please choose a different one.")

    def validate_email(self, email):
        from models import User
        if User.first_where(email=email.data):
            raise ValidationError("That email is already registered. Please use a different one.")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username", "class": "form-input"})
    password = PasswordField(validators=[InputRequired(), Length(min=12, max=72)],
                             render_kw={"placeholder": "Password", "class": "form-input"})
    submit = SubmitField("Login", render_kw={"class": "submit-btn"})


class JobForm(FlaskForm):
    title = StringField('Job Title',
                        validators=[InputRequired(), Length(min=5, max=200)],
                        render_kw={"placeholder": "e.g., Senior Software Engineer", "class": "form-input"})
    company = StringField('Company Name',
                          validators=[InputRequired(), Length(min=2, max=100)],
                          render_kw={"placeholder": "Your company name", "class": "form-input"})
    location = StringField('Location',
                           validators=[InputRequired(), Length(min=2, max=100)],
                           render_kw={"placeholder": "e.g., Lagos, Nigeria", "class": "form-input"})
    job_type = SelectField('Job Type',
                           choices=[
                               ('', 'Select job type'),
                               ('Full-time', 'Full-time'),
                               ('Part-time', 'Part-time'),
                               ('Contract', 'Contract'),
                               ('Internship', 'Internship')
                           ],
                           validators=[InputRequired()],
                           render_kw={"class": "form-select"})
    experience_level = SelectField('Experience Level',
                                   choices=[
                                       ('', 'Select experience level'),
                                       ('Entry', 'Entry Level'),
                                       ('Mid', 'Mid Level'),
                                       ('Senior', 'Senior Level')
                                   ],
                                   validators=[InputRequired()],
                                   render_kw={"class": "form-select"})
    salary_range = StringField('Salary Range',
                               validators=[Length(max=100)],
                               render_kw={"placeholder": "e.g., $60,000 - $80,000", "class": "form-input"})
    skills = StringField('Required Skills',
                         validators=[InputRequired(), Length(min=5, max=500)],
                         render_kw={"placeholder": "e.g., Python, React, AWS (comma-separated)", "class": "form-input"})
    description = TextAreaField('Job Description',
                                validators=[InputRequired(), Length(min=50, max=5000)],
                                render_kw={"placeholder": "Describe the role and responsibilities",
                                           "class": "form-textarea", "rows": "6"})
    requirements = TextAreaField('Requirements',
                                 validators=[InputRequired(), Length(min=50, max=3000)],
                                 render_kw={"placeholder": "List qualifications and required skills",
                                            "class": "form-textarea", "rows": "6"})
    deadline = DateField('Application Deadline',
                         validators=[InputRequired()],
                         render_kw={"class": "form-input"})
    benefits = TextAreaField('Benefits & Perks',
                             validators=[Length(max=2000)],
                             render_kw={"placeholder": "e.g., Health insurance, flexible hours",
                                        "class": "form-textarea", "rows": "4"})
    submit = SubmitField('Create Job Listing', render_kw={"class": "submit-btn"})
