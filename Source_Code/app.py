print("Flask file started")

from flask import Flask, render_template, redirect, url_for, request, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length
from datetime import datetime, timedelta
import bcrypt
from captcha_utils import generate_captcha
import io
import random

from config import Config

print("Starting Flask server...")

app = Flask(__name__)

from flask_mail import Mail, Message
import os
from dotenv import load_dotenv

load_dotenv()
print("EMAIL_USER =", os.getenv("EMAIL_USER"))
print("EMAIL_PASS =", os.getenv("EMAIL_PASS"))

# ================= EMAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASS")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("EMAIL_USER")

mail = Mail(app)


app.config.from_object(Config)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ================= DATABASE MODEL =================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True)
    password = db.Column(db.LargeBinary)
    email = db.Column(db.String(50), unique=True)

    role = db.Column(db.String(10), default="student")

    # NEW FIELDS FOR LOGIN LIMITER
    failed_attempts = db.Column(db.Integer, default=0)
    lock_until = db.Column(db.DateTime, nullable=True)
    must_change_password = db.Column(db.Boolean, default=True)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))

    date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Present")

# Add this after the Attendance class in app.py
class TeacherStudentEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

# ================= FORMS =================

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    captcha = StringField("Enter CAPTCHA")
    submit = SubmitField("Login")

class AdminCreateUserForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=4, max=20)])
    email = StringField("Email", validators=[InputRequired(), Length(max=50)])
    submit = SubmitField("Create User")

class AdminCreateStudentForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=4, max=20)])
    email = StringField("Email", validators=[InputRequired(), Length(max=50)])
    submit = SubmitField("Create Student")

class AdminCreateSubjectForm(FlaskForm):
    name = StringField("Subject Name", validators=[InputRequired(), Length(max=50)])
    submit = SubmitField("Create Subject")


# ================= PASSWORD STRENGTH CHECK =================
import re

def is_password_valid(password):
    # Check all requirements
    if (len(password) >= 8 and
        re.search(r"[A-Z]", password) and
        re.search(r"[a-z]", password) and
        re.search(r"[0-9]", password) and
        re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)):
        return True
    return False



# ================= LOGIN MANAGER =================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= ROUTES =================
@app.route("/")
def home():
    return redirect(url_for("login"))



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    remaining_seconds = None
    user = None  # <<< define user here to avoid UnboundLocalError

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user:
            # Check if account locked
            if user.lock_until and datetime.utcnow() < user.lock_until:
                remaining_seconds = int((user.lock_until - datetime.utcnow()).total_seconds())
                flash(f"Account locked. Try again in {remaining_seconds} seconds.")
                return render_template("login.html", form=form, remaining_seconds=remaining_seconds, failed_attempts=user.failed_attempts)

            # Require captcha after 3 failed attempts
            if user.failed_attempts >= 3:
                if form.captcha.data != session.get("captcha_text"):
                    flash("Invalid CAPTCHA")
                    return render_template("login.html", form=form, remaining_seconds=remaining_seconds, failed_attempts=user.failed_attempts)

            # Correct password
            if bcrypt.checkpw(form.password.data.encode("utf-8"), user.password):
                user.failed_attempts = 0
                user.lock_until = None
                db.session.commit()

                login_user(user)
                session['login_success'] = True  # <-- store flag

                # 🔐 Force password change if required
                if user.must_change_password:
                    return redirect(url_for("change_password"))

                # 🎯 Role-based redirect
                if user.role == "admin":
                    return redirect(url_for("admin_dashboard"))
                elif user.role == "teacher":
                    return redirect(url_for("teacher_dashboard"))
                else:
                    return redirect(url_for("student_dashboard"))

            # Wrong password
            else:
                user.failed_attempts += 1

                # Lock after 5 attempts
                if user.failed_attempts >= 5:
                    user.lock_until = datetime.utcnow() + timedelta(minutes=5)
                    remaining_seconds = 5 * 60
                    flash("Too many failed attempts. Account locked for 5 minutes or verify via email.")
                    session['locked_user'] = user.username  # store username for OTP verification

                else:
                    flash("Invalid password")

                db.session.commit()
        else:
            flash("Username not found")

    # Pass failed_attempts safely even if user is None
    failed_attempts = user.failed_attempts if user else 0

    return render_template("login.html", form=form, remaining_seconds=remaining_seconds, failed_attempts=failed_attempts)


@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != "student":
        return redirect(url_for("login"))

    if session.pop('login_success', None):
        flash(f"Welcome {current_user.username}, you have successfully logged in!")

    # your existing code to fetch subjects and percentages
    enrollments = TeacherStudentEnrollment.query.filter_by(
        student_id=current_user.id
    ).all()

    subject_ids = list(set([e.subject_id for e in enrollments]))
    subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()

    records = Attendance.query.filter_by(
        user_id=current_user.id
    ).all()

    subject_percentages = {}
    for subject in subjects:
        total_classes = Attendance.query.filter_by(
            user_id=current_user.id,
            subject_id=subject.id
        ).count()

        present_classes = Attendance.query.filter_by(
            user_id=current_user.id,
            subject_id=subject.id,
            status="Present"
        ).count()

        percentage = round((present_classes / total_classes) * 100, 2) if total_classes > 0 else 0
        subject_percentages[subject.name] = percentage

    return render_template(
        "student_dashboard.html",
        subjects=subjects,
        subject_percentages=subject_percentages
    )




@app.route('/my_attendance')
@login_required
def my_attendance():

    if current_user.role != "student":
        return redirect(url_for("login"))

    records = Attendance.query.filter_by(
        user_id=current_user.id
    ).all()

    subject_percentages = {}

    # Get unique subject IDs
    subject_ids = list(set([r.subject_id for r in records]))

    for subject_id in subject_ids:

        total_classes = Attendance.query.filter_by(
            user_id=current_user.id,
            subject_id=subject_id
        ).count()

        present_classes = Attendance.query.filter_by(
            user_id=current_user.id,
            subject_id=subject_id,
            status="Present"
        ).count()

        percentage = 0
        if total_classes > 0:
            percentage = round((present_classes / total_classes) * 100, 2)

        subject = Subject.query.get(subject_id)
        if subject:
            subject_percentages[subject.name] = percentage

    return render_template(
        "view_attendance.html",
        records=records,
        subject_percentages=subject_percentages
    )



@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        return redirect(url_for("login"))

    # Show login success only once
    if session.pop('login_success', None):
        flash(f"Welcome {current_user.username}, you have successfully logged in!")

    return render_template("admin_dashboard.html")



@app.route("/admin/view-users")
@login_required
def view_users():

    if current_user.role != "admin":
        return redirect(url_for("login"))

    teachers = User.query.filter_by(role="teacher").all()
    students = User.query.filter_by(role="student").all()

    teacher_count = len(teachers)
    student_count = len(students)

    return render_template(
        "view_users.html",
        teachers=teachers,
        students=students,
        teacher_count=teacher_count,
        student_count=student_count
    )


@app.route("/admin/delete-user/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):

    if current_user.role != "admin":
        return redirect(url_for("login"))

    user = User.query.get_or_404(user_id)

    # 🚫 Prevent admin from deleting themselves
    if user.id == current_user.id:
        flash("You cannot delete your own account.")
        return redirect(url_for("view_users"))

    # Delete related attendance records
    Attendance.query.filter_by(user_id=user.id).delete()
    Attendance.query.filter_by(teacher_id=user.id).delete()

    # Delete enrollments
    TeacherStudentEnrollment.query.filter_by(student_id=user.id).delete()
    TeacherStudentEnrollment.query.filter_by(teacher_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()

    flash(f"{user.role.capitalize()} deleted successfully.")

    return redirect(url_for("view_users"))

from sqlalchemy.exc import IntegrityError



@app.route("/admin/create-teacher", methods=["GET", "POST"])
@login_required
def create_teacher():

    if current_user.role != "admin":
        return redirect(url_for("login"))

    form = AdminCreateUserForm()

    if form.validate_on_submit():

        # ✅ Check duplicate username
        existing_username = User.query.filter_by(username=form.username.data).first()
        if existing_username:
            flash("Username already exists.")
            return redirect(url_for("create_teacher"))

        # ✅ Check duplicate email
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash("Email already exists.")
            return redirect(url_for("create_teacher"))

        # Temporary password
        temp_password = "Temp@123"
        hashed_pw = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt())

        new_teacher = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_pw,
            role="teacher",
            must_change_password=True
        )

        db.session.add(new_teacher)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Database error occurred. Please try again.")
            return redirect(url_for("create_teacher"))

        # ✅ Send Email
        msg = Message(
            subject="Your Teacher Account Created",
            recipients=[form.email.data]
        )

        msg.body = f"""
Hello,

Your teacher account has been created.

Username: {form.username.data}
Temporary Password: {temp_password}

You must change your password on first login.

Regards,
Admin
"""

        mail.send(msg)

        flash("Teacher created successfully and email sent.")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_teacher.html", form=form)



@app.route("/admin/create-student", methods=["GET", "POST"])
@login_required
def create_student():
    if current_user.role != "admin":
        return redirect(url_for("login"))

    form = AdminCreateStudentForm()

    if form.validate_on_submit():

        existing_username = User.query.filter_by(username=form.username.data).first()
        if existing_username:
            flash("Username already exists")
            return redirect(url_for("create_student"))

        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash("Email already exists")
            return redirect(url_for("create_student"))

        temp_password = "Student@123"  # temporary password
        hashed_pw = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt())

        new_student = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_pw,
            role="student",
            must_change_password=True
        )

        db.session.add(new_student)
        db.session.commit()

        # Send Email
        msg = Message(
            subject="Your Student Account",
            recipients=[form.email.data]
        )
        msg.body = f"""
Hello,

Your student account has been created.

Username: {form.username.data}
Temporary Password: {temp_password}

You must change your password on first login.

Regards,
Admin
"""
        mail.send(msg)

        flash("Student created and email sent.")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_student.html", form=form)



@app.route("/admin/create-subject", methods=["GET", "POST"])
@login_required
def create_subject():
    if current_user.role != "admin":
        return redirect(url_for("login"))

    form = AdminCreateSubjectForm()

    if form.validate_on_submit():
        existing = Subject.query.filter_by(name=form.name.data).first()
        if existing:
            flash("Subject already exists")
            return redirect(url_for("create_subject"))

        new_subject = Subject(name=form.name.data)
        db.session.add(new_subject)
        db.session.commit()
        flash("Subject created successfully")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_subject.html", form=form)





@app.route('/enroll_student', methods=['GET', 'POST'])
@login_required
def enroll_student():
    if current_user.role != "admin":
        return redirect(url_for("login"))

    teachers = User.query.filter_by(role="teacher").all()
    students = User.query.filter_by(role="student").all()
    subjects = Subject.query.all()  # fetch subjects from DB

    if request.method == "POST":
        teacher_id = request.form.get("teacher_id")
        student_id = request.form.get("student_id")
        subject_id = request.form.get("subject_id")

        subject_obj = Subject.query.get(subject_id)

        # Check if already enrolled
        existing = TeacherStudentEnrollment.query.filter_by(
            teacher_id=teacher_id,
            student_id=student_id,
            subject_id=subject_id
        ).first()

        if existing:
            flash("Student already enrolled for this subject under this teacher.")
        else:
            enrollment = TeacherStudentEnrollment(
                teacher_id=teacher_id,
                student_id=student_id,
                subject_id=subject_id
            )
            db.session.add(enrollment)
            db.session.commit()
            flash("Student enrolled successfully.")

    return render_template("enroll_student.html", teachers=teachers, students=students, subjects=subjects)




@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != "teacher":
        return redirect(url_for("login"))

    if session.pop('login_success', None):
        flash(f"Welcome {current_user.username}, you have successfully logged in!")

    # your existing code to fetch subjects
    enrollments = TeacherStudentEnrollment.query.filter_by(
        teacher_id=current_user.id
    ).all()

    subject_ids = list(set([e.subject_id for e in enrollments]))
    subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()

    return render_template("teacher_dashboard.html", subjects=subjects)


@app.route('/manage_students')
@login_required
def manage_students():

    if current_user.role != "teacher":
        return redirect(url_for("login"))

    students = User.query.filter_by(role="student").all()

    return render_template("manage_students.html", students=students)


@app.route('/teacher/subject/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def teacher_subject_view(subject_id):

    if current_user.role != "teacher":
        return redirect(url_for("login"))

    enrollments = TeacherStudentEnrollment.query.filter_by(
        teacher_id=current_user.id,
        subject_id=subject_id
    ).all()

    students = [User.query.get(e.student_id) for e in enrollments]

    if request.method == "POST":
        student_id = request.form.get("student_id")
        today = datetime.utcnow().date()

        existing = Attendance.query.filter_by(
            user_id=student_id,
            subject_id=subject_id,
            date=today
        ).first()

        if existing:
            flash("Attendance already marked today.")
        else:
            status = request.form.get("status")

            attendance = Attendance(
                user_id=student_id,
                teacher_id=current_user.id,
                subject_id=subject_id,
                date=today,
                status=status
            )
            db.session.add(attendance)
            db.session.commit()
            flash("Attendance marked.")

    subject = Subject.query.get(subject_id)

    return render_template(
        "teacher_subject_view.html",
        students=students,
        subject=subject
    )



@app.route('/view_all_attendance')
@login_required
def view_all_attendance():

    if current_user.role != "admin":
        return redirect(url_for("login"))

    subjects = Subject.query.all()
    summary = []

    for subject in subjects:

        # total students enrolled
        total_students = TeacherStudentEnrollment.query.filter_by(subject_id=subject.id).count()

        # total attendance records
        total_records = Attendance.query.filter_by(subject_id=subject.id).count()

        total_present = Attendance.query.filter_by(
            subject_id=subject.id,
            status="Present"
        ).count()

        total_absent = Attendance.query.filter_by(
            subject_id=subject.id,
            status="Absent"
        ).count()

        percentage = 0
        if total_records > 0:
            percentage = round((total_present / total_records) * 100, 2)

        summary.append({
            "subject_name": subject.name,
            "total_students": total_students,
            "total_records": total_records,
            "present": total_present,
            "absent": total_absent,
            "percentage": percentage
        })

    return render_template("view_all_attendance.html", summary=summary)



@app.route("/send-otp", methods=["POST"])
def send_otp():

    username = request.form.get("username")

    user = User.query.filter_by(username=username).first()

    if not user:
        flash("User not found.")
        return redirect(url_for("login"))

    # Generate OTP
    otp = str(random.randint(100000, 999999))
    otp_expiration = datetime.utcnow() + timedelta(minutes=1)

    session['otp'] = otp
    session['otp_expiration'] = otp_expiration.timestamp()
    session['locked_user'] = user.username
    session['resend_count'] = 0

    # Send Email
    msg = Message(
        subject="Your Login OTP",
        recipients=[user.email]
    )

    msg.body = f"Your OTP is {otp}. It expires in 1 minute."

    mail.send(msg)

    flash("OTP sent to your email.")

    return redirect(url_for("verify_otp"))


@app.route("/resend-otp", methods=["POST"])
def resend_otp():

    username = session.get("locked_user")

    if not username:
        flash("Session expired. Please login again.")
        return redirect(url_for("login"))

    user = User.query.filter_by(username=username).first()

    if not user:
        flash("User not found.")
        return redirect(url_for("login"))

    # 🚫 Prevent resend if OTP still valid
    otp_expiration = session.get("otp_expiration")
    if otp_expiration and datetime.utcnow().timestamp() < otp_expiration:
        flash("You can only resend OTP after it expires.")
        return redirect(url_for("verify_otp"))

    # 🚫 Limit resend attempts
    resend_count = session.get("resend_count", 0)
    if resend_count >= 3:
        flash("Maximum OTP resend attempts reached.")
        return redirect(url_for("login"))

    session["resend_count"] = resend_count + 1

    # Generate new OTP
    otp = str(random.randint(100000, 999999))
    otp_expiration = datetime.utcnow() + timedelta(minutes=1)

    session['otp'] = otp
    session['otp_expiration'] = otp_expiration.timestamp()

    msg = Message(
        subject="Your New Login OTP",
        recipients=[user.email]
    )
    msg.body = f"Your new OTP is {otp}. It expires in 1 minute."
    mail.send(msg)

    flash("New OTP sent successfully.")

    return redirect(url_for("verify_otp"))




@app.route('/captcha')
def captcha():
    text, image_data = generate_captcha()

    session['captcha_text'] = text

    return send_file(
        io.BytesIO(image_data.read()),
        mimetype='image/png'
    )



@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form.get("otp")
        otp = session.get("otp")
        otp_expiration = session.get("otp_expiration")

        if not otp or not otp_expiration:
            flash("No OTP requested. Please request a new OTP.")
            return redirect(url_for("verify_otp"))

        # Timestamp comparison (SAFE VERSION)
        if datetime.utcnow().timestamp() > otp_expiration:
            flash("OTP expired! Please request another OTP.")
            return redirect(url_for("verify_otp"))

        if entered_otp == otp:
            flash("OTP verified! You can now login.")

            session.pop("otp")
            session.pop("otp_expiration")
            session.pop("resend_count", None)

            username = session.get("locked_user")
            user = User.query.filter_by(username=username).first()

            if user:
                user.failed_attempts = 0
                user.lock_until = None
                db.session.commit()

            return redirect(url_for("login"))

        else:
            flash("Incorrect OTP. Try again.")

    remaining_seconds = None

    otp_expiration = session.get('otp_expiration')

    if otp_expiration:
        remaining_seconds = int(float(otp_expiration) - datetime.utcnow().timestamp())

        if remaining_seconds < 0:
            remaining_seconds = 0

    

    return render_template(
        "verify_otp.html",
        remaining_seconds=remaining_seconds
    )


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    if request.method == "POST":

        new_password = request.form.get("new_password")

        if not is_password_valid(new_password):
            flash("Password does not meet requirements.")
            return redirect(url_for("change_password"))

        current_user.password = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt()
        )

        current_user.must_change_password = False
        db.session.commit()

        flash("Password changed successfully.")

        # Redirect based on role
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif current_user.role == "teacher":
            return redirect(url_for("teacher_dashboard"))
        else:
            return redirect(url_for("student_dashboard"))

    return render_template("change_password.html")



@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/test-email")
def test_email():
    msg = Message(
        subject="Test Email",
        recipients=[app.config['MAIL_USERNAME']]
    )
    msg.body = "If you receive this, email is working!"
    mail.send(msg)
    return "Email sent!"




# ================= RUN =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False)


    