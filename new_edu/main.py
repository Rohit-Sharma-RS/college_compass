import dns.resolver
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from roadmap import SemRoadMap
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'hfOnmSAtHTUwFHUywdXTqevRRsWWVTEzjZNh'  # Required for session management
roadmap = SemRoadMap()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

with app.app_context():
    class User(UserMixin, db.Model):
        __tablename__ = "users"
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(100), unique=True)
        password = db.Column(db.String(100))
        name = db.Column(db.String(100))
        phone = db.Column(db.String(16))
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/road', methods=['GET', 'POST'])
@login_required
def index():
    semester_code = session.get('semester_code', 'sem_2')
    if int(semester_code.split('_')[1]) > 5 and int(semester_code.split('_')[1]) <= 8:  # Check if semester is greater than 3
        return redirect(url_for('coming_soon'))

    if 'week' not in session:
        session['week'] = "Week 1"  # Start with Week 1
        session['quiz_passed'] = False  # Track whether the quiz was passed

    if request.method == 'POST':
        if 'start_quiz' in request.form:
            return redirect(url_for('quiz'))

    semester_code = session.get('semester_code', 'sem_2')  # Default to 'sem2'
    week_data = roadmap.get_week_data(semester_code, session['week'])

    return render_template('roadmap.html', week=session['week'], week_data=week_data, quiz_passed=session['quiz_passed'])


@app.route('/coming_soon')
def coming_soon():
    return render_template('coming_soon.html')


@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/set_semester', methods=['POST'])
def set_semester():
    semester_code = request.form.get('semester_code')
    semester_number = int(semester_code.split('_')[1])
    if semester_number > 5 and semester_number <= 8:
        return redirect(url_for('coming_soon'))
    if hasattr(roadmap, semester_code):
        session['semester_code'] = semester_code
        session['week'] = "Week 1"  # Reset to Week 1 when semester is set
        session['quiz_passed'] = False
        return redirect(url_for('index'))
    return "Invalid Semester Code", 400


@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    current_week = session['week']
    semester_code = session['semester_code']
    quiz_data = roadmap.get_quiz(semester_code, current_week)

    if request.method == 'POST':
        score = 0
        total_questions = len(quiz_data['questions'])
        for idx, question in enumerate(quiz_data['questions']):
            selected_option = request.form.get(f'question-{idx}')
            if selected_option == question['answer']:
                score += 1

        # Calculate percentage score
        percentage = (score / total_questions) * 100
        if percentage >= 70:
            session['quiz_passed'] = True
            # Move to the next week if quiz is passed
            semester_code = session.get('semester_code', 'sem2')
            weeks = list(getattr(roadmap, semester_code).keys())
            current_index = weeks.index(current_week)
            if current_index < len(weeks) - 1:
                session['week'] = weeks[current_index + 1]
            return redirect(url_for('index'))
        else:
            session['quiz_passed'] = False
            return render_template('quiz_failed.html', score=percentage)

    return render_template('quiz.html', quiz_data=quiz_data, enumerate=enumerate)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        hash_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(
            email=email,
            name=name,
            password=hash_password,
            phone=phone
        )
        user = User.query.filter_by(email=new_user.email).first()
        # Check if the email already exists in the dummy database
        if user:
            flash("Email already exists")
            return redirect(url_for('login'))
        else:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("index"))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/profile')
@login_required
def profile():
    print(f"User logged in: {current_user.is_authenticated}")
    return render_template('profile.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("This email does not exist", "error")
        elif not check_password_hash(user.password, password):
            flash("Password incorrect", "error")
        else:
            login_user(user)
            return redirect(url_for('index'))
    return render_template("login.html")
        # Check if the user exists and the password is correct


if __name__ == '__main__':
    app.run(debug=True)
