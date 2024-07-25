from flask import Flask, render_template, request, send_file, redirect, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from flask_login import LoginManager, UserMixin, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dotenv import load_dotenv
import os
import base64

from sender import EmailSender

load_dotenv()

sender = EmailSender(SENDER=os.getenv('EMAIL'), PASS=os.getenv('EMAIL_APP_PASS'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('PORTFOLIO_KEY')

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('PORTFOLIO_DB_URI')
db.init_app(app)

class Work(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(25), nullable=False)
    type: Mapped[str] = mapped_column(String(25), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    efforts: Mapped[str] = mapped_column(Text, nullable=False)
    image = mapped_column(db.LargeBinary, nullable=False)
    source_code_link: Mapped[str] = mapped_column(Text, nullable=True)
    website_link: Mapped[str] = mapped_column(Text, nullable=True)

class Admin(db.Model, UserMixin):
    id: Mapped[str] = mapped_column(String[10], primary_key=True)
    password: Mapped[str] = mapped_column(String(20), nullable=False)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)

def login_required(func):
    @wraps(func)
    def inner():
        if current_user.is_active:
            return func()
        else:
            return redirect(url_for('home'))
    return inner

def login_not_allowed(func):
    @wraps(func)
    def inner():
        if not current_user.is_active:
            return func()
        else:
            return redirect(url_for('home'))
    return inner

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired(), Email()])
    subject = StringField('Subject', validators=[InputRequired()])
    message = TextAreaField('Message', validators=[InputRequired()])
    submit = SubmitField('Send Message')

class NewWorkForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    type = StringField('Type', validators=[InputRequired()])
    description = TextAreaField('Description', validators=[InputRequired(), Length(min=100)])
    efforts = TextAreaField('Efforts (list them and separate them with a new line)', validators=[InputRequired()])
    image = FileField('Image', validators=[FileAllowed(['png', 'jpg', 'gif'], 'Images only')])
    source_code_link = StringField('Source Code Link (Nullable)')
    website_link = StringField('Website Link (Nullable)')
    submit = SubmitField('Create New Work')

class EditWorkForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    type = StringField('Type', validators=[InputRequired()])
    description = TextAreaField('Description', validators=[InputRequired(), Length(min=100)])
    efforts = TextAreaField('Efforts (list them and separate them with a new line)', validators=[InputRequired()])
    image = FileField('Image', validators=[FileAllowed(['png', 'jpg', 'gif'], 'Images only'), FileRequired()])
    source_code_link = StringField('Source Code Link (Nullable)')
    website_link = StringField('Website Link (Nullable)')
    submit = SubmitField('Edit Work')

class LoginForm(FlaskForm):
    id = StringField('ID', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

@login_manager.user_loader
def load_admin(id):
    with db.session.no_autoflush:
        return db.session.query(Admin).filter(Admin.id == id).first()

@app.route('/')
def home():
    works = list(db.session.execute(db.select(Work).order_by(Work.id)).scalars())
    for work in works:
        work.image = work.image.decode()

    is_admin = current_user.is_active

    return render_template('index.html', works=works, is_admin=is_admin)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    if form.validate_on_submit():
        form_data = {
            'name': form.name.data,
            'email': form.email.data,
            'subject': form.subject.data,
            'message': form.message.data
        }

        errors = {
            'name': (),
            'email': (),
            'subject': (),
            'message': ()
        }

        msg = f"This message was sent by {form_data['name']} ({form_data['email']}):\n\n{form_data['message']}"

        sender.compose(target=os.getenv('EMAIL'), from_name='Your Portfolio Contact', to_name='Raphael Manayon', subject=form_data['subject'], message=msg)
        sender.send()

        return render_template('contact.html', form=form, feedback='Form successfully sent! You will be contacted within 2-3 business days.', errors=errors)
    elif request.method == 'POST':
        errors = {
            'name': form.name.errors,
            'email': form.email.errors,
            'subject': form.subject.errors,
            'message': form.message.errors
        }

        return render_template('contact.html', form=form, feedback='', errors=errors)

    return render_template('contact.html', form=form, feedback='', errors={'name': [], 'email': [], 'subject': [], 'message': []})

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/works')
def works():
    works = list(db.session.execute(db.select(Work).order_by(Work.id)).scalars())
    for work in works:
        work.image = work.image.decode()

    is_admin = current_user.is_active

    return render_template('works.html', works=works, is_admin=is_admin)

@app.route('/work_single')
def work_single():
    id = request.args.get('id')
    work = Work.query.get(id)

    work.image = work.image.decode()

    is_admin = current_user.is_active

    return render_template('work-single.html', work=work, is_admin=is_admin)

@app.route('/new_work', methods=['GET', 'POST'])
@login_required
def new_work():
    form = NewWorkForm()

    if form.validate_on_submit():
        form.image.data.stream.seek(0)
        image_string = base64.b64encode(form.image.data.read())

        NewWork = Work(
            name=form.name.data,
            type=form.type.data,
            description=form.description.data,
            efforts=form.efforts.data,
            image=image_string,
            source_code_link=form.source_code_link.data if form.source_code_link.data.strip() != "" else "null",
            website_link=form.website_link.data if form.website_link.data.strip() != "" else "null",
        )

        with app.app_context():
            db.session.add(NewWork)
            db.session.commit()

        return redirect(url_for('home'))
    elif request.method == 'POST':
        errors = {
            'name': form.name.errors,
            'type': form.type.errors,
            'description': form.description.errors,
            'efforts': form.efforts.errors,
            'image': form.image.errors
        }

        return render_template('new_work.html', form=form, errors=errors)

    return render_template('new_work.html', form=form, errors={'name': (), 'type': (), 'description': (), 'efforts': (), 'image': ()})

@app.route('/edit_work', methods=['GET', 'POST'])
@login_required
def edit_work():
    id = request.args.get('id')
    work = Work.query.get(id)

    form = EditWorkForm(
        name = work.name,
        type = work.type,
        description = work.description,
        efforts = work.efforts,
        source_code_link = work.source_code_link,
        website_link = work.website_link
    )

    if form.validate_on_submit():
        form.image.data.stream.seek(0)
        image_string = base64.b64encode(form.image.data.read())

        work.name = form.name.data
        work.type = form.type.data
        work.description = form.description.data
        work.efforts = form.efforts.data
        work.image = image_string
        work.source_code_link = form.source_code_link.data
        work.website_link = form.website_link.data
        db.session.commit()

        return redirect(url_for('home'))
    elif request.method == 'POST':
        errors = {
            'name': form.name.errors,
            'type': form.type.errors,
            'description': form.description.errors,
            'efforts': form.efforts.errors,
            'image': form.image.errors
        }

        return render_template('edit_work.html', form=form, errors=errors, id=id)

    return render_template('edit_work.html', form=form, errors={'name': (), 'type': (), 'description': (), 'efforts': (), 'image': ()}, id=id)

@app.route('/delete_work')
@login_required
def delete_work():
    id = request.args.get('id')
    work = Work.query.get(id)

    db.session.delete(work)
    db.session.commit()

    return redirect(url_for('home'))

@app.route('/rephysaysopensesamelogin', methods=['GET', 'POST'])
@login_not_allowed
def login():
    form = LoginForm()

    all_users = list(db.session.execute(db.select(Admin)).scalars())
    if len(all_users) == 0:
        db.session.add(Admin(id='REPHY2011', password=generate_password_hash('REPHY2011!', salt_length=16)))

    if form.validate_on_submit():
        users = list(db.session.execute(db.select(Admin).where(Admin.id == form.id.data)).scalars())
        if len(users) == 0:
            errors = {
                'id': ['Invalid ID.'],
                'password': form.password.errors
            }

            return render_template('login.html', form=form, errors=errors)

        if not check_password_hash(users[0].password, form.password.data):
            errors = {
                'id': form.id.errors,
                'password': ['Incorrect password.']
            }

            return render_template('login.html', form=form, errors=errors)

        login_user(users[0])

        return redirect(url_for('home'))
    elif request.method == 'POST':
        errors = {
            'id': form.id.errors,
            'password': form.password.errors
        }

        return render_template('login.html', form=form, errors=errors)

    return render_template('login.html', form=form, errors={'id': (), 'password': ()})

@app.route('/resume')
def resume():
    return send_file('Resume.pdf', as_attachment=True)

@app.errorhandler(404)
def not_found(e):
    works = list(db.session.execute(db.select(Work).order_by(Work.id)).scalars())
    for work in works:
        work.image = work.image.decode()

    return render_template('error404.html', works=works)

if __name__ == '__main__':
    app.run()
