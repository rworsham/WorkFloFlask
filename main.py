import os
from flask import Flask, render_template, url_for, redirect, request, flash, send_from_directory
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField, SelectField, IntegerField
from wtforms.validators import DataRequired, NumberRange, InputRequired
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_gravatar import Gravatar
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, Text, desc
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_ckeditor import CKEditorField
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import smtplib
from email.message import EmailMessage
from datetime import date, datetime

UPLOAD_FOLDER = './static/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


app = Flask(__name__)
app.secret_key = "rob"
login_manager = LoginManager()


class Base(DeclarativeBase):
    pass

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
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
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    work_state: Mapped[int] = mapped_column(Integer)
    date: Mapped[str] = mapped_column(String(50))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    project = relationship("Project", back_populates="posts")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author = relationship("User",back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")
    files = relationship("Files", back_populates="parent_post")


class Files(db.Model):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(100), nullable=False)
    filepath: Mapped[str] = mapped_column(String(250), nullable=False)
    parent_post_id: Mapped[int] = mapped_column(Integer, ForeignKey("todo_posts.id"), nullable=True)
    parent_post = relationship("TodoPost", back_populates="files")


class Project(db.Model):
    __tablename__ = "project"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(250), nullable=False)
    posts = relationship("TodoPost", back_populates="project")


class WorkState(db.Model):
    __tablename__ = "workstate"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_state: Mapped[str] = mapped_column(String(250), nullable=False)
    work_state_order: Mapped[int] = mapped_column(Integer)


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
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("todo_posts.id"), nullable=True)
    parent_post = relationship("TodoPost", back_populates="comments")


with app.app_context():
    db.create_all()


class CreateTodoForm(FlaskForm):
    title = StringField("Work Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    work_state = SelectField("Select Work State", coerce=int, validators=[InputRequired()])
    body = CKEditorField("Content", validators=[DataRequired()])
    project = SelectField("Select Project", coerce=int, validators=[InputRequired()])
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
    submit_comment = SubmitField("Submit Comment")
    comment = CKEditorField(" ",validators=[DataRequired()])


class ProjectForm(FlaskForm):
    project_name = StringField(validators=[DataRequired()])
    submit = SubmitField("Save")


class CreateWorkStateForm(FlaskForm):
    work_state = StringField("WorkFlo Name", validators=[DataRequired()])
    work_state_order = IntegerField("WorkFlo Order: 1 Through etc.", validators=[NumberRange(min=1),DataRequired()])
    save = SubmitField("Save")


class WorkStateChange(FlaskForm):
    work_state = SelectField(" ", coerce=int, validators=[InputRequired()])
    save = SubmitField("Save")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    all_work_states = WorkState.query.order_by(WorkState.work_state_order).all()
    all_work_state_list = [all_work_states]
    todos = TodoPost.query.order_by(TodoPost.work_state).all()
    todos_list = [todos]
    available_projects = db.session.query(Project).all()
    projects_list = [(i.id, i.project) for i in available_projects]
    available_work_states = db.session.query(WorkState).all()
    work_state_list = [(i.id, i.work_state) for i in available_work_states]
    form = CreateTodoForm()
    work_state_form = CreateWorkStateForm()
    form.project.choices = projects_list
    form.work_state.choices = work_state_list
    if form.submit.data and form.validate_on_submit():
        new_todo = TodoPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            work_state=form.work_state.data,
            date=date.today().strftime("%B %d, %Y"),
            body=form.body.data,
            project_id=form.project.data,
            author=current_user
        )
        db.session.add(new_todo)
        db.session.commit()
        return redirect(url_for('dashboard'))
    if work_state_form.save.data and work_state_form.validate_on_submit():
        new_state = WorkState(
            work_state=work_state_form.work_state.data,
            work_state_order=work_state_form.work_state_order.data
        )
        db.session.add(new_state)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template("dashboard.html", form=form, work_state_form=work_state_form,
                           work_states=all_work_state_list, todos=todos_list,)


@app.route('/dashboard/<int:id>', methods=['GET', 'POST'])
@login_required
def work_view(id):
    available_work_states = db.session.query(WorkState).all()
    comment_form = CommentForm()
    comment_results = db.session.query(Comment).where(Comment.post_id == id).order_by(desc(Comment.id)).all()
    comment_list = [comment_results]
    file_results = db.session.query(Files).where(Files.parent_post_id == id).order_by(desc(Files.id)).all()
    file_list = [i.filename for i in file_results]
    work_state_form = WorkStateChange()
    work_state_list = [(i.id, i.work_state) for i in available_work_states]
    work_state_form.work_state.choices = work_state_list
    result = db.session.query(TodoPost).where(TodoPost.id == id)
    todo = result.scalar()
    todo_post = db.get_or_404(TodoPost, id)
    current_work_state = db.session.query(WorkState).where(WorkState.id == todo.work_state).scalar()
    current_work_state_name = current_work_state.work_state
    if work_state_form.save.data and work_state_form.validate_on_submit:
        todo_post.work_state = work_state_form.work_state.data
        db.session.commit()
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
    if request.method == "POST":
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            print(filename)
            print(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_file = Files(
                filename=filename,
                filepath=os.path.abspath(filename),
                parent_post_id=id
            )
            db.session.add(new_file)
            db.session.commit()
            return redirect(url_for('work_view', id=id))
            # return redirect(url_for('download_file', name=filename))
    return render_template('todo.html', todo=todo, work_state_change_form=work_state_form,current_work_state=current_work_state_name, comment_form=comment_form, comments=comment_list, files=file_list)


@app.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    form = ProjectForm()
    all_projects = Project.query.order_by(Project.id).all()
    project_list = [all_projects]
    if form.validate_on_submit():
        project_name = form.project_name.data
        result = db.session.execute(db.select(Project).where(Project.project == project_name))
        project_name_result = result.scalar()
        if project_name_result:
            flash("That project already exist, please try again")
            return redirect(url_for('projects'))
        new_project = Project(
            project=form.project_name.data
        )
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('projects'))
    return render_template('projects.html', form=form, projects=project_list)


@app.route('/overview')
@login_required
def overview():
    return render_template('overview.html')


@app.route('/events', methods=['GET', 'POST'])
@login_required
def events():
    return render_template('events.html')


@app.route("/delete/<int:id>")
@login_required
def delete(id):
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


@app.route('/upload<int:id>', methods=['GET', 'POST'])
@login_required
def upload_file(id):
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('download_file', name=filename))
    return


@app.route('/uploads/<name>')
@login_required
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

if __name__ == '__main__':
    app.run(debug=True)