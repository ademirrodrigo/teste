from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pilates.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'change-this-key'

db = SQLAlchemy(app)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120))

class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)

class ClassSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructor.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)

    instructor = db.relationship('Instructor')
    student = db.relationship('Student')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_at = db.Column(db.Date, default=datetime.utcnow)

    student = db.relationship('Student')

@app.route('/')
def index():
    schedules = ClassSchedule.query.order_by(ClassSchedule.start_time).all()
    return render_template('index.html', schedules=schedules)

@app.route('/students', methods=['GET', 'POST'])
def students():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form.get('email')
        if name:
            student = Student(name=name, email=email)
            db.session.add(student)
            db.session.commit()
            flash('Aluno adicionado com sucesso!')
        return redirect(url_for('students'))
    students = Student.query.all()
    return render_template('students.html', students=students)

@app.route('/instructors', methods=['GET', 'POST'])
def instructors():
    if request.method == 'POST':
        name = request.form['name']
        if name:
            instructor = Instructor(name=name)
            db.session.add(instructor)
            db.session.commit()
            flash('Instrutor adicionado com sucesso!')
        return redirect(url_for('instructors'))
    instructors = Instructor.query.all()
    return render_template('instructors.html', instructors=instructors)

@app.route('/classes', methods=['GET', 'POST'])
def classes():
    students = Student.query.all()
    instructors = Instructor.query.all()
    if request.method == 'POST':
        instructor_id = request.form['instructor_id']
        student_id = request.form['student_id']
        start_time = datetime.fromisoformat(request.form['start_time'])
        schedule = ClassSchedule(instructor_id=instructor_id, student_id=student_id, start_time=start_time)
        db.session.add(schedule)
        db.session.commit()
        flash('Aula agendada com sucesso!')
        return redirect(url_for('classes'))
    schedules = ClassSchedule.query.order_by(ClassSchedule.start_time).all()
    return render_template('classes.html', schedules=schedules, students=students, instructors=instructors)

@app.route('/payments', methods=['GET', 'POST'])
def payments():
    students = Student.query.all()
    if request.method == 'POST':
        student_id = request.form['student_id']
        amount = float(request.form['amount'])
        payment = Payment(student_id=student_id, amount=amount)
        db.session.add(payment)
        db.session.commit()
        flash('Pagamento registrado com sucesso!')
        return redirect(url_for('payments'))
    payments = Payment.query.order_by(Payment.paid_at.desc()).all()
    return render_template('payments.html', payments=payments, students=students)

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Banco de dados inicializado.')

if __name__ == '__main__':
    app.run(debug=True)
