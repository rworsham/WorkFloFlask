from flask import Flask, render_template, url_for, redirect, request, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, EmailField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_gravatar import Gravatar
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, ForeignKey, Text, DATE
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_ckeditor import CKEditorField
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.message import EmailMessage
import datetime

app = Flask(__name__)
app.secret_key = "rob"
login_manager = LoginManager()


class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todos.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)
login_manager.init_app(app)
bootstrap = Bootstrap5(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


class TodoPost(db.Model):
    __tablename__ = "todo_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    work_state: Mapped[str] = mapped_column(String(50))
    date: Mapped[str] = mapped_column(DATE)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # project = relationship("Project", back_populates=)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author = relationship("User",back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")



# class Project(db.Model):
#     __tablename__ = "project"
#     project: Mapped[str] = mapped_column(String(250), nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    posts = relationship("TodoPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id: Mapped[str] = mapped_column(Integer,db.ForeignKey("todo_posts.id"))
    parent_post = relationship("TodoPost", back_populates="comments")


with app.app_context():
    db.create_all()


class CreateTodoForm(FlaskForm):
    title = StringField("Work Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    body = CKEditorField("Content", validators=[DataRequired()])
    submit = SubmitField("Submit Work")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class RegistrationForm(FlaskForm):
    email = EmailField("Email Address", validators=[DataRequired()])
    password = PasswordField("Enter Password", validators=[DataRequired()])
    name = StringField("Username", validators=[DataRequired()])
    submit = SubmitField("Sign Up")


class CommentForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route('/', methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if not user:
            flash("That email does not exist, please try again")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash("Password Incorrect. Please try again")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template("login.html", form=form)


@app.route('/register',methods=["GET","POST"])
@login_required
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        result = db.session.execute(db.select(User).where(User.email == email))
        user_email = result.scalar()
        name = form.name.data
        name_result = db.session.execute(db.select(User).where(User.name == name))
        user_name = name_result.scalar()
        if user_email:
            flash("Email already exist")
            return redirect(url_for('login'))
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=generate_password_hash(password=form.password.data,method="pbkdf2:sha256",salt_length=8)
        )
        if user_name:
            message = "Username already exist, please try again"
            return render_template("register.html", messages=message)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))
    return render_template("register.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")



if __name__ == '__main__':
    app.run(debug=True)