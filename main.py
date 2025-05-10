from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///santinho.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Define models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    party = db.Column(db.String(150))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    flyer_count = db.Column(db.Integer, nullable=False)
    photo_url = db.Column(db.String(150), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Login manager user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    ranking = db.session.query(Candidate, db.func.sum(Post.flyer_count).label('total_flyers')) \
                        .join(Post) \
                        .group_by(Candidate) \
                        .order_by(db.desc('total_flyers')) \
                        .all()
    return render_template('index.html', posts=posts, ranking=ranking)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # In production, use proper password hashing
            login_user(user)
            return redirect(url_for('index'))
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_user = User(username=username, password=password)  # Hash password in production
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    if request.method == 'POST':
        candidate_name = request.form['candidate']
        flyer_count = request.form['flyer_count']
        photo = request.files['photo']
        photo_url = save_photo(photo)
        candidate = Candidate.query.filter_by(name=candidate_name).first()
        if not candidate:
            candidate = Candidate(name=candidate_name)
            db.session.add(candidate)
            db.session.commit()
        new_post = Post(user_id=current_user.id, candidate_id=candidate.id, flyer_count=flyer_count, photo_url=photo_url)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))
    candidates = Candidate.query.all()
    return render_template('post.html', candidates=candidates)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Function to save photo
def save_photo(photo):
    filename = secure_filename(photo.filename)
    unique_filename = str(uuid.uuid4()) + '_' + filename
    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
    return url_for('static', filename='uploads/' + unique_filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)