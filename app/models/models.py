from datetime import datetime
from app import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    institute_name = db.Column(db.String(150), unique=True, nullable=False) 
    address = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.Date, default=datetime.utcnow)
    created_time = db.Column(db.Time, default=lambda: datetime.utcnow().time())
    last_login = db.Column(db.DateTime, default=None, nullable=True)

    courses = db.relationship('CourseDetails', backref='institute', lazy=True)
    def __repr__(self):
        return f"<User {self.username}>"
    
class CourseDetails(db.Model):
    __tablename__ = 'course_details'

    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)
    course_duration = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    institute_name = db.Column(db.String(150), db.ForeignKey('users.institute_name'), nullable=False)
    students = db.relationship('StudentDetails', backref='course', lazy=True)
    

    def __repr__(self):
        return f"<CourseDetails {self.course_name}>"

class StudentDetails(db.Model):
    __tablename__ = 'student_details'

    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    student_contact = db.Column(db.String(15), nullable=False)
    student_mail = db.Column(db.String(100), unique=True, nullable=False)
    student_address = db.Column(db.String(255), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course_details.id'), nullable=False)
    total_payable_amnt = db.Column(db.Float, nullable=False)
    institute_name = db.Column(db.String(150), db.ForeignKey('users.institute_name'), nullable=False)

    installments = db.relationship('Installment', back_populates='student')  # Relationship with Installments
    payment_history = db.relationship('PaymentHistory', back_populates='student', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<StudentDetails {self.student_name}>"    
    

class Installment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_details.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)  # The amount for each installment 
    due_date = db.Column(db.Date, nullable=False)  # The due date for the installment
    status = db.Column(db.String(20), default="Not Paid") 
    # total_installments = db.Column(db.Integer,nullable=False)
    student = db.relationship('StudentDetails', back_populates='installments')  # Relationship with StudentDetails



class PaymentHistory(db.Model):
    __tablename__ = 'payment_history'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_details.id'), nullable=False)
    paid_amount = db.Column(db.Float, nullable=False)
    paid_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    paid_time = db.Column(db.Time, nullable=False, default=datetime.utcnow().time())

    # Relationship with the StudentDetails model
    student = db.relationship('StudentDetails', back_populates='payment_history')

    def __repr__(self):
        return f"<PaymentHistory StudentID={self.student_id}, Amount={self.paid_amount}>"