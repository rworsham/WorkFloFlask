import os
from flask import (Flask, render_template, url_for, redirect,
                   request, flash, send_from_directory, jsonify)
from flask_wtf import FlaskForm
from wtforms import (StringField, SubmitField, EmailField, PasswordField,
                     SelectField, IntegerField, DateField, BooleanField)
from wtforms.validators import DataRequired, NumberRange, InputRequired
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_gravatar import Gravatar
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, Text, desc, BOOLEAN
from flask_login import (UserMixin, login_user, LoginManager, login_required,
                         current_user, logout_user)
from flask_ckeditor import CKEditorField
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import smtplib
from email.message import EmailMessage
from datetime import date, datetime
import plotly
import plotly.express as px
import pandas as pd
import json

UPLOAD_FOLDER = './static/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
EMAIL_ADDRESS = "dalcomworkflo@gmail.com"
EMAIL_PASSWORD = ("apppassword")

app = Flask(__name__)
app.secret_key = "rob"
login_manager = LoginManager()


class Base(DeclarativeBase):
    pass


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Workflo.db'
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
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    work_state: Mapped[int] = mapped_column(Integer)
    date_created: Mapped[str] = mapped_column(String(50))
    due_date: Mapped[str] = mapped_column(String(50))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    project = relationship("Project", back_populates="posts")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")
    files = relationship("Files", back_populates="parent_post")
    subscribed_users = relationship("Subscribed", back_populates="parent_post")
    show_on_calendar: Mapped[bool] = mapped_column(BOOLEAN)
    calendar_date: Mapped[str] = mapped_column(String(50), nullable=True)


class Files(db.Model):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(100), nullable=False)
    filepath: Mapped[str] = mapped_column(String(250), nullable=False)
    parent_post_id: Mapped[int] = mapped_column(Integer,
                                                ForeignKey("todo_posts.id"),
                                                nullable=True)
    parent_post = relationship("TodoPost", back_populates="files")


class Project(db.Model):
    __tablename__ = "project"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(250), nullable=False)
    project_color: Mapped[str] = mapped_column(String(7))
    posts = relationship("TodoPost", back_populates="project")


class WorkState(db.Model):
    __tablename__ = "workstate"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_state: Mapped[str] = mapped_column(String(250), nullable=False)
    is_hidden: Mapped[bool] = mapped_column(BOOLEAN)
    work_state_order: Mapped[int] = mapped_column(Integer)

class TodoType(db.Model):
    __tablename__ = "todotype"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_type: Mapped[str] = mapped_column(String(15), nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_admin: Mapped[bool] = mapped_column(BOOLEAN)
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
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("todo_posts.id"),
                                         nullable=True)
    parent_post = relationship("TodoPost", back_populates="comments")


class Subscribed(db.Model):
    __tablename__ = "subscribed"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_email: Mapped[str] = mapped_column(String(100))
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("todo_posts.id"),
                                         nullable=True)
    parent_post = relationship("TodoPost", back_populates="subscribed_users")


with app.app_context():
    db.create_all()


class CreateTodoForm(FlaskForm):
    title = StringField("Work Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    work_state = SelectField("Select Work State", coerce=int,
                             validators=[InputRequired()])
    body = CKEditorField("Content", validators=[DataRequired()])
    due_date = DateField()
    show_on_calendar = BooleanField("Show on Calendar?")
    type = SelectField("Select Project Type", coerce=int)
    project = SelectField("Select Project",
                          coerce=int, validators=[InputRequired()])
    submit = SubmitField("Submit Work")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password",
                             validators=[DataRequired()])
    submit = SubmitField("Log In")


class RegistrationForm(FlaskForm):
    email = EmailField("Email Address", validators=[DataRequired()])
    password = PasswordField("Enter Password",
                             validators=[DataRequired()])
    name = StringField("Username", validators=[DataRequired()])
    is_admin = BooleanField("Set Admin")
    submit = SubmitField("Register")


class CommentForm(FlaskForm):
    submit_comment = SubmitField("Submit Comment")
    comment = CKEditorField(" ", validators=[DataRequired()])


class ProjectForm(FlaskForm):
    project_name = StringField(validators=[DataRequired()])
    submit = SubmitField("Save")


class CreateWorkStateForm(FlaskForm):
    work_state = StringField("WorkFlo Name", validators=[DataRequired()])
    work_state_order = IntegerField("WorkFlo Order: 1 Through etc.",
                                    validators=[NumberRange(min=1), DataRequired()])
    is_hidden = BooleanField("Hide from Dashboard?")
    save = SubmitField("Save")


class WorkStateChange(FlaskForm):
    work_state = SelectField(" ", coerce=int,
                             validators=[InputRequired()])
    save = SubmitField("Save")


class EditWorkState(FlaskForm):
    work_state_order = IntegerField("WorkFlo Order: 1 Through etc.",
                                    validators=[NumberRange(min=1), DataRequired()])
    is_hidden = BooleanField("Hide from Dashboard?")
    save = SubmitField("Save")


class EditTodoForm(FlaskForm):
    todo_title = StringField("Title")
    todo_subtitle = StringField("Subtitle")
    todo_body = CKEditorField("Description")
    todo_due_date = DateField(default=datetime.today())
    show_on_calendar = BooleanField("Show on calendar?")
    todo_type = SelectField("Select Project Type", coerce=int)
    todo_project = SelectField("Select Project", coerce=int)
    save_updates = SubmitField("Save")


class SubscribeForm(FlaskForm):
    subscribe = SubmitField("Subscribe to Updates")


class UnsubscribeForm(FlaskForm):
    unsubscribe = SubmitField("Unsubscribe to Updates")


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route('/', methods=["GET", "POST"])
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


@app.route('/register', methods=["GET", "POST"])
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
            is_admin=form.is_admin.data,
            password=generate_password_hash(password=form.password.data,
                                            method="pbkdf2:sha256",
                                            salt_length=8)
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


@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    all_work_states = WorkState.query.order_by(WorkState.work_state_order).where(WorkState.is_hidden == False).all()
    all_work_state_list = [all_work_states]
    todos = TodoPost.query.order_by(TodoPost.work_state).all()
    todos_list = [todos]
    available_projects = db.session.query(Project).all()
    projects_list = [(i.id, i.project) for i in available_projects]
    available_work_states = db.session.query(WorkState).all()
    work_state_list = [(i.id, i.work_state) for i in available_work_states]
    type_list = [(1, "New Install"), (2, "Feature"), (3, "Bug")]
    form = CreateTodoForm()
    work_state_form = CreateWorkStateForm()
    form.project.choices = projects_list
    form.work_state.choices = work_state_list
    form.type.choices = type_list
    if form.submit.data and form.validate_on_submit():
        new_todo = TodoPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            work_state=form.work_state.data,
            date_created=date.today().strftime("%B %d, %Y"),
            due_date=datetime.strftime(form.due_date.data, "%B %d, %Y"),
            body=form.body.data,
            type=form.type.data,
            project_id=form.project.data,
            author=current_user,
            show_on_calendar=form.show_on_calendar.data,
            calendar_date=datetime.strftime(form.due_date.data, "%Y%m%d")
        )
        db.session.add(new_todo)
        db.session.commit()
        return redirect(url_for('dashboard'))
    if current_user.is_admin:
        if work_state_form.save.data and work_state_form.validate_on_submit():
            new_state = WorkState(
                work_state=work_state_form.work_state.data,
                work_state_order=work_state_form.work_state_order.data,
                is_hidden=work_state_form.is_hidden.data
            )
            db.session.add(new_state)
            db.session.commit()
            return redirect(url_for('dashboard'))
    return render_template("dashboard.html",
                           form=form,
                           work_state_form=work_state_form,
                           work_states=all_work_state_list,
                           todos=todos_list, )


@app.route('/dashboard/<int:id>', methods=['GET', 'POST'])
@login_required
def work_view(id):
    todo_post = db.get_or_404(TodoPost, id)
    subscribe = SubscribeForm()
    unsubscribe = UnsubscribeForm()
    edit_form = EditTodoForm()
    if todo_post.show_on_calendar == True:
        edit_form.show_on_calendar.data = True
    available_projects = db.session.query(Project).all()
    projects_list = ([(i.id, i.project) for i in available_projects])
    projects_list.insert(0, (0, ""))
    available_work_states = db.session.query(WorkState).all()
    edit_form.todo_project.choices = projects_list
    comment_form = CommentForm()
    comment_results = db.session.query(Comment).where(Comment.post_id == id).order_by(desc(Comment.id)).all()
    comment_list = [comment_results]
    file_results = db.session.query(Files).where(Files.parent_post_id == id).order_by(desc(Files.id)).all()
    file_list = [file_results]
    work_state_form = WorkStateChange()
    work_state_list = [(i.id, i.work_state) for i in available_work_states]
    work_state_form.work_state.choices = work_state_list
    result = db.session.query(TodoPost).where(TodoPost.id == id)
    todo = result.scalar()
    current_work_state = db.session.query(WorkState).where(WorkState.id == todo.work_state).scalar()
    current_work_state_name = current_work_state.work_state
    current_project = db.session.query(Project).where(Project.id == todo.project_id).scalar()
    current_project_name = current_project.project
    subject = todo.title
    subscribed_user_result = db.session.query(Subscribed).where(Subscribed.post_id == id).all()
    subscribed_user_list = [i.user_email for i in subscribed_user_result]
    if current_user.email in subscribed_user_list:
        user_is_subscribed_to_updates = True
    elif current_user.email not in subscribed_user_list:
        user_is_subscribed_to_updates = False
    if work_state_form.save.data and work_state_form.validate_on_submit:
        todo_post.work_state = work_state_form.work_state.data
        changed_work_state = db.session.query(WorkState).where(WorkState.id == work_state_form.work_state.data).scalar()
        db.session.commit()
        message = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body bgcolor="#F5F8FA" style="width: 100%; margin:auto; font-family:Lato, sans-serif; font-size:18px;">
            <div>
                <table role="presentation" width="100%">
                    <tr>
                        <td bgcolor="#004990" align="center" style="color: white;">
                            <h1 style="font-size:56px;">ID:{todo.id} - {todo.title} </h1>
                        </td>
                </table>
                <table role="presentation" border="0" cellpadding="0" cellspacing="10px" style="padding: 30px 30px 30px 60px;">
                    <tr>
                        <td style="vertical-align:top;">
                            <h2>{todo.title}</h2>
                            <p>
                                {current_user.name} changed work state from {current_work_state_name} to {changed_work_state.work_state}.
                            </p>
                        </td>
                    </tr>
                </table>
            </div>
            </body>
            </html>
            '''
        for reciever in subscribed_user_list:
            notification(message, reciever, subject)
        return redirect(url_for('work_view', id=id))

    if comment_form.submit_comment.data and comment_form.validate_on_submit():
        new_comment = Comment(
            text=comment_form.comment.data,
            date=datetime.now().strftime("%b/%d/%Y | %I:%M:%p"),
            comment_author=current_user,
            post_id=id
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('work_view', id=id))

    if edit_form.save_updates.data and edit_form.validate_on_submit():
        if edit_form.todo_title.data:
            todo_post.title = edit_form.todo_title.data
            db.session.commit()
        if edit_form.todo_subtitle.data:
            todo_post.subtitle = edit_form.todo_subtitle.data
            db.session.commit()
        if edit_form.todo_body.data:
            todo_post.body = edit_form.todo_body.data
            db.session.commit()
        if edit_form.todo_due_date.data:
            if edit_form.todo_due_date.data != datetime.date(datetime.today()):
                todo_post.due_date = datetime.strftime(edit_form.todo_due_date.data, "%B %d, %Y")
                todo_post.calendar_date = datetime.strftime(edit_form.todo_due_date.data, "%Y%m%d")
                db.session.commit()
        if request.form.get('show_on_calendar') == "y":
            todo_post.show_on_calendar = 1
            db.session.commit()
        if request.form.get('show_on_calendar') == None:
            todo_post.show_on_calendar = 0
            db.session.commit()
        if edit_form.todo_project.data:
            if edit_form.todo_project.data != "":
                todo_post.project_id = int(edit_form.todo_project.data)
                db.session.commit()

        return redirect(url_for('work_view', id=id))

    if request.files and request.method == "POST":
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if not os.path.exists(f"{UPLOAD_FOLDER}/{id}"):
                os.makedirs(f"{UPLOAD_FOLDER}/{id}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], str(id), filename))
            new_file = Files(
                filename=filename,
                filepath=os.path.abspath(filename),
                parent_post_id=id
            )
            db.session.add(new_file)
            db.session.commit()
            return redirect(url_for('work_view', id=id))
    if subscribe.subscribe.data:
        sub_user = Subscribed(
            user_email=current_user.email,
            post_id=id
        )
        db.session.add(sub_user)
        db.session.commit()
        return redirect(url_for('work_view', id=id))

    if unsubscribe.unsubscribe.data:
        subbed_user = db.session.query(Subscribed).where(Subscribed.post_id == id).where(
            Subscribed.user_email == current_user.email).scalar()
        subbed_user.post_id = ""
        db.session.commit()
        return redirect(url_for('work_view', id=id))

    return render_template('todo.html', todo=todo,
                           work_state_change_form=work_state_form,
                           current_work_state=current_work_state_name,
                           current_project=current_project_name,
                           comment_form=comment_form,
                           edit_form=edit_form,
                           comments=comment_list,
                           files=file_list,
                           subscribe_form=subscribe,
                           unsubscribe_form=unsubscribe,
                           user_is_subscribed_to_updates=user_is_subscribed_to_updates
                           )


@app.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    all_projects = Project.query.order_by(Project.id).all()
    project_list = [all_projects]
    if request.method == "POST":
        project_name = request.form['ProjectName']
        if len(project_name) > 90:
            flash("Please limit name to 90 characters")
            return redirect(url_for('projects'))
        result = db.session.execute(db.select(Project).where(Project.project == project_name))
        project_name_result = result.scalar()
        if project_name_result:
            flash("That project already exist, please try again")
            return redirect(url_for('projects'))
        new_project = Project(
            project=request.form['ProjectName'],
            project_color=request.form['ColorInput']
        )
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('projects'))
    return render_template('projects.html', projects=project_list)


@app.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@login_required
def projects_view(project_id):
    project = db.get_or_404(Project, project_id)
    project_todo_result = db.session.query(TodoPost).where(TodoPost.project_id == project_id).all()
    project_todo_list = [project_todo_result]
    available_work_states = db.session.query(WorkState).all()
    work_state_list = [(i.id, i.work_state) for i in available_work_states]
    return render_template('project_view.html',
                           project=project,
                           project_todo_list=project_todo_list,
                           work_states=work_state_list)


@app.route('/overview')
@login_required
def overview():
    bar_chart = bar_chart_todo()
    return render_template('overview.html', bar_chart=bar_chart)


@app.route('/eventdata')
@login_required
def event_data():
    data = []
    start_date = request.args.get('start').replace("-", "")[:8]
    end_date = request.args.get('end').replace("-", "")[:8]
    calendar_events = db.session.query(TodoPost).where(TodoPost.show_on_calendar == True).order_by(
        TodoPost.calendar_date).all()
    for calendar in calendar_events:
        if int(start_date) <= int(calendar.calendar_date) <= int(end_date):
            event = {
                "title": f"{calendar.title}",
                "start": f"{calendar.calendar_date}",
                "end": f"{calendar.calendar_date}",
                "url": url_for('work_view', id=calendar.id)
            }
            data.append(event)
    return jsonify(data)


@app.route('/events', methods=['GET', 'POST'])
@login_required
def events():
    return render_template('events.html')


@app.route('/edit_work_state/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_work_state(id):
    if current_user.is_admin:
        work_state_to_edit = db.get_or_404(WorkState, id)
        work_state_to_edit.work_state_order = request.form['work_state_order']
        form_is_hidden = request.form.get('is_hidden')
        work_state_to_edit.is_hidden = False
        if form_is_hidden:
            if form_is_hidden == "y":
                work_state_to_edit.is_hidden = True
        db.session.commit()
        return redirect(url_for('settings'))
    return redirect(url_for('settings'))


@app.route("/delete_user/<int:id>")
@login_required
def delete_user(id):
    if current_user.is_admin:
        user_to_delete = db.get_or_404(User, id)
        db.session.delete(user_to_delete)
        db.session.commit()
        return redirect(url_for('settings'))
    return redirect(url_for('settings'))


@app.route("/delete_state/<int:id>")
@login_required
def delete_work_state(id):
    if current_user.is_admin:
        work_state_to_delete = db.get_or_404(WorkState, id)
        db.session.delete(work_state_to_delete)
        db.session.commit()
        return redirect(url_for('settings'))
    return redirect(url_for('settings'))


@app.route("/delete_todo/<int:id>")
@login_required
def delete_todo(id):
    todo_to_delete = db.get_or_404(TodoPost, id)
    db.session.delete(todo_to_delete)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/delete_comment/<int:id>")
@login_required
def delete_comment(id):
    comment_to_delete = db.get_or_404(Comment, id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/delete_project/<int:id>")
@login_required
def delete_project(id):
    project_to_delete = db.get_or_404(Project, id)
    db.session.delete(project_to_delete)
    db.session.commit()
    return redirect(url_for('projects'))


@app.route('/<int:post_id>/<int:file_id>')
@login_required
def download_file(post_id, file_id):
    filename_result = db.session.query(Files.filename).where(Files.id == file_id)
    filename = filename_result.scalar()
    path = UPLOAD_FOLDER + "/" + str(post_id)
    return send_from_directory(path, filename)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user_results = db.session.query(User).all()
    user_list = [user_results]
    work_state_results = WorkState.query.order_by(WorkState.work_state_order).all()
    work_state_list = [work_state_results]
    work_state_form = CreateWorkStateForm()
    register_new_user_form = RegistrationForm()
    work_state_edit_form = EditWorkState()
    if current_user.is_admin:
        if register_new_user_form.submit.data and register_new_user_form.validate_on_submit():
            new_user = User(
                name=register_new_user_form.name.data,
                email=register_new_user_form.email.data,
                is_admin=register_new_user_form.is_admin.data,
                password=generate_password_hash(password=register_new_user_form.password.data,
                                                method="pbkdf2:sha256",
                                                salt_length=8)
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('settings'))
    if current_user.is_admin:
        if work_state_form.save.data and work_state_form.validate_on_submit():
            new_work_state = WorkState(
                work_state=work_state_form.work_state.data,
                work_state_order=work_state_form.work_state_order.data,
                is_hidden=work_state_form.is_hidden.data
            )
            db.session.add(new_work_state)
            db.session.commit()
            return redirect(url_for('settings'))
    return render_template('settings.html',
                           user_list=user_list,
                           work_state_list=work_state_list,
                           work_state_form=work_state_form,
                           register_new_user_form=register_new_user_form,
                           work_state_edit_form=work_state_edit_form)


def bar_chart_todo():
    df_todo = pd.read_sql(sql=db.session.query(TodoPost).with_entities(TodoPost.work_state).statement, con=db.engine)
    df_todo_count = df_todo.groupby("work_state").size()
    df_todo_graph = df_todo_count.rename("# of To-do's")
    df_work_state = pd.read_sql(sql=db.session.query(WorkState).with_entities(WorkState.work_state).order_by(
        WorkState.work_state_order).statement, con=db.engine)
    df_work_state.index += 1
    df_graph = df_work_state.join(df_todo_graph)
    fig = px.bar(df_graph, x="work_state", y="# of To-do's", labels={'work_state': 'Work State'}, barmode="group")
    fig.update_layout(yaxis_range=[0, 20])
    fig.update_traces(marker_color='green')
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


def notification(message, reciever, subject):
    msg = EmailMessage()
    msg.set_content(message, subtype='html')

    msg['Subject'] = subject
    msg['From'] = "Dalcom WorkFlo"
    msg['To'] = reciever

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(401)
def page_not_found(e):
    return render_template('401.html'), 401


if __name__ == '__main__':
    app.run(debug=True)
