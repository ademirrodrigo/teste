import io
import os
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def database_uri() -> str:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    return f"sqlite:///{os.path.join(BASE_DIR, 'pilates.db')}"


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "change-this-key"),
    SQLALCHEMY_DATABASE_URI=database_uri(),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Studio(db.Model):
    __tablename__ = "studios"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    trade_name = db.Column(db.String(120))
    tax_id = db.Column(db.String(20))  # CPF ou CNPJ
    owner_name = db.Column(db.String(120), nullable=False)
    owner_cpf = db.Column(db.String(20), nullable=False)
    owner_email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    whatsapp = db.Column(db.String(30))
    address = db.Column(db.String(200))
    city = db.Column(db.String(120))
    state = db.Column(db.String(2))
    zip_code = db.Column(db.String(15))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", back_populates="studio", cascade="all, delete")
    students = db.relationship("Student", back_populates="studio", cascade="all, delete")
    instructors = db.relationship(
        "Instructor", back_populates="studio", cascade="all, delete"
    )
    classes = db.relationship(
        "ClassSchedule", back_populates="studio", cascade="all, delete"
    )
    payments = db.relationship("Payment", back_populates="studio", cascade="all, delete")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="staff")  # owner, staff, instructor, superadmin
    active = db.Column(db.Boolean, default=True)
    studio_id = db.Column(db.Integer, db.ForeignKey("studios.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    studio = db.relationship("Studio", back_populates="users")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_superadmin(self) -> bool:
        return self.role == "superadmin"


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    studio_id = db.Column(db.Integer, db.ForeignKey("studios.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    whatsapp = db.Column(db.String(30))
    tax_id = db.Column(db.String(20))
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    studio = db.relationship("Studio", back_populates="students")
    payments = db.relationship("Payment", back_populates="student", cascade="all, delete")
    enrollments = db.relationship(
        "ClassEnrollment", back_populates="student", cascade="all, delete"
    )


class Instructor(db.Model):
    __tablename__ = "instructors"

    id = db.Column(db.Integer, primary_key=True)
    studio_id = db.Column(db.Integer, db.ForeignKey("studios.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    whatsapp = db.Column(db.String(30))
    bio = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)

    studio = db.relationship("Studio", back_populates="instructors")
    classes = db.relationship("ClassSchedule", back_populates="instructor")


class ClassSchedule(db.Model):
    __tablename__ = "class_schedules"

    id = db.Column(db.Integer, primary_key=True)
    studio_id = db.Column(db.Integer, db.ForeignKey("studios.id"), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey("instructors.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(120))
    capacity = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text)

    studio = db.relationship("Studio", back_populates="classes")
    instructor = db.relationship("Instructor", back_populates="classes")
    enrollments = db.relationship(
        "ClassEnrollment", back_populates="class_schedule", cascade="all, delete"
    )


class ClassEnrollment(db.Model):
    __tablename__ = "class_enrollments"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_schedules.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    status = db.Column(db.String(20), default="confirmed")  # confirmed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class_schedule = db.relationship("ClassSchedule", back_populates="enrollments")
    student = db.relationship("Student", back_populates="enrollments")


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    studio_id = db.Column(db.Integer, db.ForeignKey("studios.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(40), default="mensalidade")
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default="pendente")  # pendente, pago, cancelado
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    method = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    studio = db.relationship("Studio", back_populates="payments")
    student = db.relationship("Student", back_populates="payments")


class ReminderLog(db.Model):
    __tablename__ = "reminder_logs"

    id = db.Column(db.Integer, primary_key=True)
    studio_id = db.Column(db.Integer, db.ForeignKey("studios.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("class_schedules.id"))
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    channel = db.Column(db.String(20))  # email, whatsapp, manual
    message = db.Column(db.Text)
    scheduled_for = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    studio = db.relationship("Studio")
    class_schedule = db.relationship("ClassSchedule")
    student = db.relationship("Student")


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


def current_studio():
    if not current_user.is_authenticated:
        return None
    if current_user.studio_id:
        return Studio.query.get(current_user.studio_id)
    if current_user.is_superadmin:
        studio_id = session.get("selected_studio_id")
        if studio_id:
            return Studio.query.get(studio_id)
    return None


@app.context_processor
def inject_globals():
    return {
        "current_studio": current_studio(),
        "today": date.today(),
    }


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def require_studio():
    if current_user.is_superadmin:
        studio_id = request.args.get("studio_id", type=int)
        if studio_id:
            session["selected_studio_id"] = studio_id
        selected = session.get("selected_studio_id")
        if selected:
            studio = Studio.query.get(selected)
            if studio:
                return studio
            session.pop("selected_studio_id", None)
        flash("Selecione um estúdio para continuar.")
        return redirect(url_for("studios"))
    studio = current_studio()
    if not studio:
        flash("Nenhum estúdio associado ao usuário.")
        return redirect(url_for("logout"))
    return studio


def parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("Data/hora em formato inválido. Use AAAA-MM-DDTHH:MM")


# ---------------------------------------------------------------------------
# Authentication routes
# ---------------------------------------------------------------------------


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        studio_name = request.form.get("studio_name")
        owner_name = request.form.get("owner_name")
        owner_cpf = request.form.get("owner_cpf")
        owner_email = request.form.get("owner_email")
        password = request.form.get("password")
        phone = request.form.get("phone")
        whatsapp = request.form.get("whatsapp")

        if not all([studio_name, owner_name, owner_cpf, owner_email, password]):
            flash("Preencha todos os campos obrigatórios.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=owner_email).first():
            flash("E-mail já está em uso.")
            return redirect(url_for("register"))

        studio = Studio(
            name=studio_name,
            trade_name=studio_name,
            owner_name=owner_name,
            owner_cpf=owner_cpf,
            owner_email=owner_email,
            phone=phone,
            whatsapp=whatsapp,
        )
        user = User(email=owner_email, name=owner_name, role="owner", studio=studio)
        user.set_password(password)

        db.session.add(studio)
        db.session.add(user)
        db.session.commit()
        flash("Estúdio criado com sucesso. Faça login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email, active=True).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Credenciais inválidas ou usuário desativado.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard & overview
# ---------------------------------------------------------------------------


@app.route("/")
@login_required
def dashboard():
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio  # redirect response

    today_start = datetime.combine(date.today(), datetime.min.time())
    next_classes = (
        ClassSchedule.query.filter_by(studio_id=studio.id)
        .filter(ClassSchedule.start_time >= today_start)
        .order_by(ClassSchedule.start_time)
        .limit(5)
        .all()
    )

    pending_payments = (
        Payment.query.filter_by(studio_id=studio.id, status="pendente")
        .order_by(Payment.due_date)
        .limit(5)
        .all()
    )

    paid_this_month = float(
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter_by(studio_id=studio.id, status="pago")
        .filter(
            Payment.paid_date >= date.today().replace(day=1),
            Payment.paid_date <= date.today(),
        )
        .scalar()
    )

    overdue_amount = float(
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter_by(studio_id=studio.id, status="pendente")
        .filter(Payment.due_date < date.today())
        .scalar()
    )

    active_students = Student.query.filter_by(studio_id=studio.id, active=True).count()
    active_instructors = (
        Instructor.query.filter_by(studio_id=studio.id, active=True).count()
    )

    return render_template(
        "dashboard.html",
        studio=studio,
        next_classes=next_classes,
        pending_payments=pending_payments,
        paid_this_month=paid_this_month,
        overdue_amount=overdue_amount,
        active_students=active_students,
        active_instructors=active_instructors,
    )


# ---------------------------------------------------------------------------
# CRUD routes
# ---------------------------------------------------------------------------


@app.route("/students", methods=["GET", "POST"])
@login_required
def students():
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    if request.method == "POST":
        student = Student(
            studio_id=studio.id,
            name=request.form.get("name"),
            email=request.form.get("email"),
            whatsapp=request.form.get("whatsapp"),
            tax_id=request.form.get("tax_id"),
            notes=request.form.get("notes"),
        )
        if not student.name:
            flash("Nome é obrigatório.")
            return redirect(url_for("students"))
        db.session.add(student)
        db.session.commit()
        flash("Aluno salvo com sucesso.")
        return redirect(url_for("students"))

    students_list = Student.query.filter_by(studio_id=studio.id).order_by(Student.name).all()
    return render_template("students.html", students=students_list)


@app.route("/students/<int:student_id>/toggle", methods=["POST"])
@login_required
def toggle_student(student_id: int):
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    student = Student.query.filter_by(id=student_id, studio_id=studio.id).first_or_404()
    student.active = not student.active
    db.session.commit()
    flash("Status do aluno atualizado.")
    return redirect(url_for("students"))


@app.route("/instructors", methods=["GET", "POST"])
@login_required
def instructors():
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    if request.method == "POST":
        instructor = Instructor(
            studio_id=studio.id,
            name=request.form.get("name"),
            email=request.form.get("email"),
            whatsapp=request.form.get("whatsapp"),
            bio=request.form.get("bio"),
        )
        if not instructor.name:
            flash("Nome é obrigatório.")
            return redirect(url_for("instructors"))
        db.session.add(instructor)
        db.session.commit()
        flash("Instrutor salvo com sucesso.")
        return redirect(url_for("instructors"))

    instructor_list = (
        Instructor.query.filter_by(studio_id=studio.id).order_by(Instructor.name).all()
    )
    return render_template("instructors.html", instructors=instructor_list)


@app.route("/classes", methods=["GET", "POST"])
@login_required
def classes():
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    instructors_list = Instructor.query.filter_by(studio_id=studio.id, active=True).all()
    students_list = Student.query.filter_by(studio_id=studio.id, active=True).all()

    if request.method == "POST":
        try:
            start_time = parse_datetime(request.form.get("start_time"))
            end_time = parse_datetime(request.form.get("end_time"))
        except ValueError as exc:
            flash(str(exc))
            return redirect(url_for("classes"))

        instructor_id = request.form.get("instructor_id", type=int)
        if not instructor_id:
            flash("Selecione um instrutor.")
            return redirect(url_for("classes"))

        if end_time <= start_time:
            flash("Horário final deve ser após o início.")
            return redirect(url_for("classes"))

        class_schedule = ClassSchedule(
            studio_id=studio.id,
            title=request.form.get("title") or "Aula",
            instructor_id=instructor_id,
            start_time=start_time,
            end_time=end_time,
            location=request.form.get("location"),
            capacity=request.form.get("capacity", type=int) or 1,
            notes=request.form.get("notes"),
        )
        db.session.add(class_schedule)
        db.session.commit()

        student_ids = request.form.getlist("student_ids")
        for student_id in student_ids:
            student_id_int = int(student_id)
            exists = ClassEnrollment.query.filter_by(
                class_id=class_schedule.id, student_id=student_id_int
            ).first()
            if exists:
                continue
            enrollment = ClassEnrollment(
                class_id=class_schedule.id,
                student_id=student_id_int,
            )
            db.session.add(enrollment)
        db.session.commit()
        flash("Aula agendada com sucesso.")
        return redirect(url_for("classes"))

    schedules = (
        ClassSchedule.query.filter_by(studio_id=studio.id)
        .order_by(ClassSchedule.start_time.desc())
        .limit(30)
        .all()
    )
    return render_template(
        "classes.html",
        schedules=schedules,
        students=students_list,
        instructors=instructors_list,
    )


@app.route("/classes/<int:class_id>/enroll", methods=["POST"])
@login_required
def enroll_student(class_id: int):
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    class_schedule = ClassSchedule.query.filter_by(
        id=class_id, studio_id=studio.id
    ).first_or_404()
    student_id = request.form.get("student_id", type=int)
    if not student_id:
        flash("Selecione um aluno.")
        return redirect(url_for("classes"))
    exists = ClassEnrollment.query.filter_by(
        class_id=class_schedule.id, student_id=student_id
    ).first()
    if exists:
        flash("Aluno já matriculado nesta aula.")
        return redirect(url_for("classes"))
    enrollment = ClassEnrollment(
        class_id=class_schedule.id,
        student_id=student_id,
    )
    db.session.add(enrollment)
    db.session.commit()
    flash("Aluno matriculado na aula.")
    return redirect(url_for("classes"))


@app.route("/payments", methods=["GET", "POST"])
@login_required
def payments():
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    students_list = Student.query.filter_by(studio_id=studio.id, active=True).all()

    if request.method == "POST":
        student_id = request.form.get("student_id", type=int)
        amount_raw = request.form.get("amount")
        due_date = request.form.get("due_date")
        paid_date = request.form.get("paid_date") or None

        try:
            amount = Decimal(amount_raw).quantize(Decimal("0.01"))
        except (TypeError, InvalidOperation):
            amount = None

        if not (student_id and amount and due_date):
            flash("Aluno, valor e data de vencimento são obrigatórios.")
            return redirect(url_for("payments"))

        payment = Payment(
            studio_id=studio.id,
            student_id=student_id,
            amount=amount,
            category=request.form.get("category") or "mensalidade",
            description=request.form.get("description"),
            status=request.form.get("status") or "pendente",
            due_date=datetime.fromisoformat(due_date).date(),
            method=request.form.get("method"),
        )
        if paid_date:
            payment.paid_date = datetime.fromisoformat(paid_date).date()
        if payment.paid_date and payment.status == "pendente":
            payment.status = "pago"

        db.session.add(payment)
        db.session.commit()
        flash("Pagamento registrado.")
        return redirect(url_for("payments"))

    payments_list = (
        Payment.query.filter_by(studio_id=studio.id)
        .order_by(Payment.due_date.desc())
        .limit(100)
        .all()
    )
    return render_template("payments.html", payments=payments_list, students=students_list)


@app.route("/payments/<int:payment_id>/status", methods=["POST"])
@login_required
def update_payment_status(payment_id: int):
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    payment = Payment.query.filter_by(id=payment_id, studio_id=studio.id).first_or_404()
    new_status = request.form.get("status")
    if new_status not in {"pendente", "pago", "cancelado"}:
        flash("Status inválido.")
        return redirect(url_for("payments"))
    payment.status = new_status
    if new_status == "pago" and not payment.paid_date:
        payment.paid_date = date.today()
    db.session.commit()
    flash("Status atualizado.")
    return redirect(url_for("payments"))


# ---------------------------------------------------------------------------
# Reminders and communication
# ---------------------------------------------------------------------------


@app.route("/reminders", methods=["GET", "POST"])
@login_required
def reminders():
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    upcoming_classes = (
        ClassSchedule.query.filter_by(studio_id=studio.id)
        .filter(ClassSchedule.start_time >= datetime.utcnow())
        .order_by(ClassSchedule.start_time)
        .limit(20)
        .all()
    )

    if request.method == "POST":
        class_id = request.form.get("class_id", type=int)
        channel = request.form.get("channel") or "manual"
        message = request.form.get("message")

        enrollment_ids = request.form.getlist("enrollment_ids")
        if not enrollment_ids:
            flash("Selecione pelo menos um aluno para enviar lembrete.")
            return redirect(url_for("reminders"))

        for enrollment_id in enrollment_ids:
            enrollment = ClassEnrollment.query.get(int(enrollment_id))
            if not enrollment or enrollment.class_schedule.studio_id != studio.id:
                continue
            reminder = ReminderLog(
                studio_id=studio.id,
                class_id=class_id,
                student_id=enrollment.student_id,
                channel=channel,
                message=message,
                scheduled_for=enrollment.class_schedule.start_time - timedelta(hours=2),
            )
            db.session.add(reminder)
        db.session.commit()
        flash(
            "Lembretes registrados. Use os dados para envio manual ou integre com o canal escolhido."
        )
        return redirect(url_for("reminders"))

    reminder_history = (
        ReminderLog.query.filter_by(studio_id=studio.id)
        .order_by(ReminderLog.sent_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "reminders.html",
        upcoming_classes=upcoming_classes,
        reminder_history=reminder_history,
    )


# ---------------------------------------------------------------------------
# Users & studio management
# ---------------------------------------------------------------------------


def owner_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_superadmin and current_user.role != "owner":
            flash("Acesso restrito aos proprietários do estúdio.")
            return redirect(url_for("dashboard"))
        return func(*args, **kwargs)

    return wrapper


@app.route("/users", methods=["GET", "POST"])
@login_required
@owner_required
def manage_users():
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        role = request.form.get("role") or "staff"
        password = request.form.get("password")
        if not all([name, email, password]):
            flash("Nome, e-mail e senha são obrigatórios.")
            return redirect(url_for("manage_users"))
        if User.query.filter_by(email=email).first():
            flash("E-mail já está sendo utilizado.")
            return redirect(url_for("manage_users"))
        new_user = User(
            name=name,
            email=email,
            role=role,
            studio_id=studio.id,
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Usuário criado.")
        return redirect(url_for("manage_users"))

    users = (
        User.query.filter_by(studio_id=studio.id)
        .order_by(User.created_at.desc())
        .all()
    )
    return render_template("users.html", users=users)


@app.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@owner_required
def toggle_user(user_id: int):
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    user = User.query.filter_by(id=user_id, studio_id=studio.id).first_or_404()
    if user.id == current_user.id:
        flash("Você não pode desativar a si mesmo.")
        return redirect(url_for("manage_users"))
    user.active = not user.active
    db.session.commit()
    flash("Status do usuário atualizado.")
    return redirect(url_for("manage_users"))


@app.route("/studios")
@login_required
def studios():
    if not current_user.is_superadmin:
        flash("Apenas super administradores podem gerenciar múltiplos estúdios.")
        return redirect(url_for("dashboard"))
    studios_list = Studio.query.order_by(Studio.created_at.desc()).all()
    return render_template("studios.html", studios=studios_list)


# ---------------------------------------------------------------------------
# LCDPR / Carnê-Leão
# ---------------------------------------------------------------------------


def build_lcdpr_lines(studio: Studio, year: int):
    lines = ["LCDPR|1.0|"]
    lines.append(f"0000|LECD|1|{year}|")
    lines.append("0001|0|")

    lines.append(
        "0100|{owner_name}|{owner_cpf}|{owner_email}|{phone}|".format(
            owner_name=studio.owner_name,
            owner_cpf=studio.owner_cpf,
            owner_email=studio.owner_email,
            phone=studio.phone or "",
        )
    )

    lines.append(
        "0200|{trade}|{tax}|F|{address}|{city}|{state}|{zip}|".format(
            trade=studio.trade_name or studio.name,
            tax=studio.tax_id or studio.owner_cpf,
            address=studio.address or "",
            city=studio.city or "",
            state=studio.state or "",
            zip=studio.zip_code or "",
        )
    )

    revenues = (
        Payment.query.filter_by(studio_id=studio.id, status="pago")
        .filter(
            Payment.paid_date >= date(year, 1, 1),
            Payment.paid_date <= date(year, 12, 31),
        )
        .order_by(Payment.paid_date)
        .all()
    )

    for payment in revenues:
        student = payment.student
        lines.append(
            "0500|{date}|{description}|{amount:.2f}|{method}|{student_name}|{student_tax}|".format(
                date=payment.paid_date.strftime("%Y%m%d") if payment.paid_date else "",
                description=payment.description or payment.category,
                amount=float(payment.amount),
                method=payment.method or "",
                student_name=student.name if student else "",
                student_tax=student.tax_id if student and student.tax_id else "",
            )
        )

    total_lines = len(lines) + 1
    lines.append(f"9900|{total_lines}|")
    return lines


@app.route("/reports/lcdpr", methods=["GET", "POST"])
@login_required
def lcdpr_report():
    studio = require_studio()
    if not isinstance(studio, Studio):
        return studio

    if request.method == "POST":
        year = request.form.get("year", type=int)
        if not year:
            flash("Informe o ano desejado.")
            return redirect(url_for("lcdpr_report"))
        lines = build_lcdpr_lines(studio, year)
        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))
        filename = f"LCDPR_{studio.trade_name or studio.name}_{year}.txt"
        return send_file(
            buffer,
            mimetype="text/plain",
            as_attachment=True,
            download_name=filename,
        )

    return render_template("lcdpr.html")


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    print("Banco de dados inicializado.")


@app.cli.command("create-superuser")
def create_superuser():
    """Cria um usuário superadmin via linha de comando."""

    email = input("E-mail: ")
    name = input("Nome: ")
    password = input("Senha: ")

    if User.query.filter_by(email=email).first():
        print("E-mail já cadastrado.")
        return

    user = User(email=email, name=name, role="superadmin")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print("Superusuário criado com sucesso.")


@app.cli.command("seed-demo")
def seed_demo():
    """Popula dados de demonstração para testes rápidos."""

    if Studio.query.count() > 0:
        print("Dados já existentes. Abortando.")
        return

    studio = Studio(
        name="Pilates Prime",
        trade_name="Pilates Prime",
        owner_name="Ana Souza",
        owner_cpf="12345678901",
        owner_email="ana@example.com",
        phone="11999999999",
        whatsapp="11999999999",
        address="Rua das Flores, 123",
        city="São Paulo",
        state="SP",
        zip_code="01000000",
    )
    owner = User(
        email="ana@example.com",
        name="Ana Souza",
        role="owner",
        studio=studio,
    )
    owner.set_password("123456")

    db.session.add(studio)
    db.session.add(owner)

    student = Student(
        studio=studio,
        name="Carlos Oliveira",
        email="carlos@example.com",
        whatsapp="11988887777",
        tax_id="11122233344",
    )
    instructor = Instructor(
        studio=studio,
        name="Marina Lima",
        email="marina@example.com",
    )

    db.session.add(student)
    db.session.add(instructor)
    db.session.commit()

    class_schedule = ClassSchedule(
        studio=studio,
        instructor=instructor,
        title="Aula Experimental",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        location="Sala 1",
        capacity=5,
    )
    db.session.add(class_schedule)
    db.session.commit()

    enrollment = ClassEnrollment(class_schedule=class_schedule, student=student)
    db.session.add(enrollment)

    payment = Payment(
        studio=studio,
        student=student,
        amount=200.00,
        category="mensalidade",
        description="Mensalidade agosto",
        status="pago",
        due_date=date.today(),
        paid_date=date.today(),
        method="pix",
    )
    db.session.add(payment)

    db.session.commit()
    print("Dados de demonstração criados.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
