from flask import Blueprint, render_template,request, flash ,redirect,url_for, session,jsonify,send_file
from app.models.models import StudentDetails,CourseDetails, User, Installment,PaymentHistory
from app import db, mail
from flask_mail import Message
import re
from sqlalchemy import desc
from app.auth.decorators import login_required
from datetime import datetime, timedelta
from fpdf import FPDF
import os


main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html', title="Home")

# This is for forget password
@main.route('/forget')
def index1():
    return render_template('forgetpass.html', title="forget")

# This is for login 
@main.route("/home")
@login_required
def home():
    # Get the user_id from session
    user_id = session.get('user_id')

    if user_id:
        user = User.query.get(user_id)
    else:
        user = None

    if user:
        institute_name = user.institute_name
    else:
        institute_name = "Institute not found"

    # Get the selected course_id and student_name from the URL parameters (if any)
    course_id = request.args.get('course_id')
    student_name = request.args.get('student_name', '').strip()
    page = request.args.get('page', 1, type=int)  # Get current page from query params, default to 1
    per_page = 7

    # Filter students by course and/or student name
    query = StudentDetails.query.filter_by(institute_name=institute_name)       
    
    if course_id:
        query = query.filter_by(course_id=course_id)
    
    if student_name:
        query = query.filter(StudentDetails.student_name.ilike(f'%{student_name}%'))  # Case-insensitive search for student name
    
    query = query.order_by(desc(StudentDetails.id))

    # students = query.all()
    # Paginate students
    students_pagination = query.paginate(page=page, per_page=per_page)
    students = students_pagination.items 

    course = CourseDetails.query.filter_by(institute_name=institute_name).all()

    upcoming_installments = {}
    current_date = datetime.utcnow().date()
    print(current_date)
    # Loop through each student
    for student in students:
    # Initialize an empty list to store the first upcoming installment
      student_upcoming_installments = []

    # Loop through each installment and break once we find the first upcoming one
      for installment in student.installments:
          if (installment.due_date > current_date) and (installment.status == "Not Paid"):
            student_upcoming_installments.append(installment)
            break  # Stop iterating once the first upcoming installment is found

    # Store the first upcoming installment for the student
      upcoming_installments[student.id] = student_upcoming_installments
    #   {1 : [4000]}

    # Display message if no students found  
    if not students:
        flash("No students found !", "error")

    return render_template("home.html", institute_name=institute_name, students=students, course=course, upcoming_installments=upcoming_installments, pagination=students_pagination)

# This is for Course
@main.route('/course')
@login_required
def course():
    # Get the user_id from session
    user_id = session.get('user_id')

    if user_id:
        user = User.query.get(user_id)
    else:
        user = None

    # Get the institute name for the logged-in user
    if user:
        institute_name = user.institute_name
    else:
        institute_name = "Institute not found"

    # Filter courses by institute_name
    courseDetails = CourseDetails.query.filter_by(institute_name=institute_name).all()
    
    return render_template('course.html', courseDetails=courseDetails, institute_name=institute_name)


# This is for Edit Course
@main.route('/edit-course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit(course_id):
    course = CourseDetails.query.get_or_404(course_id)

    if request.method == 'POST':
        course_name = request.form['course_name'].strip()
        course_duration = request.form['course_duration'].strip()
        price = request.form['price'].strip()

        # Validation
        if not course_name or not course_duration or not price:
            flash("Please fill in all required fields without spaces only.", "error")
            return redirect(url_for("main.edit", course_id=course_id))

        if course_name.isdigit():
            flash("Please enter a correct course name.", "error")
            return redirect(url_for("main.edit", course_id=course_id))

        if not course_duration.isdigit():
            flash("Duration should be entered in digits.", "error")
            return redirect(url_for("main.edit", course_id=course_id))

        if not price.isdigit():
            flash("Price should be entered in digits.", "error")
            return redirect(url_for("main.edit", course_id=course_id))

        # Check if a different course with the same name already exists
        if CourseDetails.query.filter(CourseDetails.id != course_id, CourseDetails.course_name == course_name).first():
            flash("A course with this name already exists.", "error")
            return redirect(url_for("main.edit", course_id=course_id))

        # Only update the course after successful validation
        course.course_name = course_name
        course.course_duration = course_duration
        course.price = price
        db.session.commit()

        flash("Course updated successfully!", "success")
        return redirect(url_for("main.course"))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return JSON response for AJAX requests
        return jsonify({
            'course_name': course.course_name,
            'course_duration': course.course_duration,
            'price': course.price
        })

    return render_template('course.html', course=course)


# This is for Delete any Course
@main.route('/delete-course/<int:course_id>', methods=['GET',"POST"])
@login_required
def delete(course_id):
    course = CourseDetails.query.get_or_404(course_id)
    if not course.students:
        db.session.delete(course)
        db.session.commit()
        flash("course deleted successfully",'error')
        return redirect(url_for('main.course'))
    flash("The course cannot be deleted because there are still students enrolled.", "error")
    return redirect(url_for('main.course'))

@main.route('/addstu', methods=['POST'])
@login_required
def Add_Student():
    if request.method == 'POST':
        student_name = request.form['student_name'].strip()
        student_contact = request.form['student_contact'].strip()
        student_mail = request.form['student_mail'].strip()
        student_address = request.form['student_address'].strip()
        course_id = request.form['course_id']
        total_payable_amnt = float(request.form['total_payable_amnt'])
        installments_count = int(request.form['installments'])

        # Check if any field is empty or only spaces
        if not student_name or not student_contact or not student_mail or not total_payable_amnt:
            flash("Please fill in all required fields without spaces only.", "error")
            return redirect(url_for("main.home"))

        if student_name.isdigit():
            flash("Student name should be in Alphabetical character", "error")
            return redirect(url_for("main.home"))
            

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_.+-]*@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$", student_mail):
            flash("Invalid email format.", "error")
            return redirect(url_for("main.home"))

        # Validate contact number format 
        if not student_contact.isdigit() or len(student_contact) != 10:
            flash("Contact number should be 10 digits long and number should be in digit.", "error")
            return redirect(url_for("main.home"))     

        # Check if email already exists
        if StudentDetails.query.filter_by(student_mail=student_mail).first():
            flash("Email id already exists", "error")
            return redirect(url_for("main.home"))

        user_id = session.get('user_id')
        user = User.query.filter_by(id=user_id).first()
        
        # Create a new student and assign the institute_name
        new_student = StudentDetails(
            student_name=student_name,
            student_contact=student_contact,
            student_mail=student_mail,
            student_address=student_address,
            course_id=course_id,
            total_payable_amnt=round(float(total_payable_amnt)),  
            institute_name=user.institute_name  
        )

        # Add the new student to the database
        db.session.add(new_student)
        db.session.commit()


        # Calculate installment amount and gap_months
        installment_amount = total_payable_amnt / installments_count
        # course1 = CourseDetails.query.get(course_id)
        course1 = CourseDetails.query.filter_by(id=course_id, institute_name=user.institute_name).first()
        course_duration = course1.course_duration
        print(course_duration)
        course_duration_months = course_duration  # Adjust this dynamically based on course 
        gap_months = course_duration_months / installments_count  # Months gap between installments

        # Calculate installment due dates
        current_date = datetime.now()
        for i in range(installments_count):
            due_date = current_date + timedelta(days=gap_months * 30)  # Approximate 30 days for each month
            new_installment = Installment(
                student_id=new_student.id,
                amount=installment_amount,
                due_date=due_date.date()  # Store as date in the DB
            )
            db.session.add(new_installment)
            current_date = due_date  # Set the current date to the last installment's due date

        db.session.commit()
        flash("Added student successfully!", "success")
        return redirect(url_for("main.home"))


# This is for add any Course
@main.route('/add-course', methods=['GET', 'POST'])
@login_required
def Add_Course():
    if request.method == 'POST':
        course_name = request.form['course_name'].strip()
        course_duration = request.form['course_duration'].strip()
        price = request.form['price'].strip()

        if not course_name or not course_duration or not price:
            flash("Please fill in all required fields without spaces only.", "error")
            return redirect(url_for("main.course"))
    

        if course_name.isdigit():
            flash("Please enter a correct course name.", "error")
            return redirect(url_for("main.course"))

        if not course_duration.isdigit():
            flash("Duration should be enter in Digit", "error")
            return redirect(url_for("main.course"))

        user_id = session.get('user_id')
        if CourseDetails.query.filter_by(course_name=course_name).first():
            flash("This name of Course already exists", "error" )
            return redirect(url_for("main.course"))
        
        user_id = session.get('user_id')

        # Query the logged-in user's institute_name
        user = User.query.filter_by(id=user_id).first()

        # If the user is not found, handle the error
        if not user:
            flash("User not found.")
            return redirect(url_for("main.course"))
        
        # Create new course
        new_course = CourseDetails(
            course_name=course_name,
            course_duration=course_duration,
            price=price,
            institute_name = user.institute_name
        )

        db.session.add(new_course)
        db.session.commit()

        flash("Added Course successfully!", "success")
        return redirect(url_for("main.course"))
        

@main.route('/student_details/<int:student_id>')
@login_required
def student_details(student_id):
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
    else:
        user = None

    if user:
        institute_name = user.institute_name
    else:
        institute_name = "Institute not found"

    student = StudentDetails.query.get_or_404(student_id)
    
    # Fetch payment details (installments) for the student
    installments = Installment.query.filter_by(student_id=student_id).all()

    for installment in installments:
        installment.amount = round(installment.amount)

    course_id = request.args.get('course_id', type = int)
    if course_id:
        students = StudentDetails.query.filter_by(course_id=course_id).all()
    else:
        students = [student]  # Just pass the selected student if no course filter

    courses = CourseDetails.query.all()

    return render_template('studentdetails.html', student=student, students=students, institute_name=institute_name, courses=courses, installments=installments)


@main.route('/update_student/<int:student_id>', methods=['POST'])
@login_required
def update_student(student_id):

        student = StudentDetails.query.get_or_404(student_id)
        student_name = request.form['student_name'].strip()
        student_contact = request.form['student_contact'].strip()
        student_mail = request.form['student_mail'].strip()
        student_address = request.form['student_address'].strip()
        total_payable_amnt = request.form['total_payable_amnt'].strip()
        course_id = request.form['course_id'].strip()

         # Check if any field is empty or only spaces
        if not student_name or not student_contact or not student_mail or not student_address:
            flash("Please fill in all required fields without spaces only.", "error")
            return redirect(url_for("main.home"))
        
         # Check if email already exists
        if StudentDetails.query.filter_by(student_mail=student_mail).first():
            flash("Email id already exists", "error")
            return redirect(url_for("main.home"))
        
        if student_name.isdigit():
            flash("Student name should be in Alphabetical character", "error")
            return redirect(url_for("main.home"))
            

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_.+-]*@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$", student_mail):
            flash("Invalid email format.", "error")
            return redirect(url_for("main.home"))

        # Validate contact number format 
        if not student_contact.isdigit() or len(student_contact) != 10:
            flash("Contact number should be 10 digits long and number should be in digit.", "error")
            return redirect(url_for("main.home"))     


        student.student_name = student_name
        student.student_contact = student_contact
        student.student_mail = student_mail
        student.student_address = student_address
        # student.course_id = request.form['course_id'].strip()
        # student.total_payable_amnt = request.form['total_payable_amnt'].strip()
        db.session.commit()  
        # flash("Student details updated successfully!", "success")
        # return redirect('/home')

        courses = CourseDetails.query.filter_by(id= student.course_id).all()
        installments = Installment.query.filter_by(student_id=student_id).all()

        return render_template('studentdetails.html', student=student,courses=courses, installments=installments)

# This is for Delete any Students
@main.route('/delete_student/<int:student_id>')
@login_required
def delete_student(student_id):
    student = StudentDetails.query.get_or_404(student_id)
    Installment.query.filter_by(student_id=student.id).delete()

    db.session.delete(student)
    db.session.commit()
    flash("Student deleted successfully !", "success")
    return redirect('/home')

# @main.route('/payment')
# def payment():
#     # Retrieve the payment amount from the query parameter
#     amount = request.args.get('amount', default=0)
#     return render_template('payment.html', amount=amount)

@main.route('/add-installments/<int:student_id>', methods=['POST'])
@login_required
def add_installments(student_id):
    student = StudentDetails.query.get_or_404(student_id)
    print(student.course.price)

    # Get the current number of installments
    current_installments_count = len(student.installments)
    # print(student.installments)
    # print(current_installments_count)
    total_amount = student.total_payable_amnt
    f = True
    if current_installments_count == 1:
        total_amount = student.total_payable_amnt + student.course.price * 0.15
        student.total_payable_amnt = total_amount
        flash("New installment added. You will now receive only 10%.", "success")  
        f = False

    elif current_installments_count == 2:
        total_amount = student.total_payable_amnt + student.course.price * 0.10
        student.total_payable_amnt = total_amount
        flash("New installment added. You did not receive any discount.", "success")
        f = False

    # Get the total amount for the student
    total_amount = total_amount
    # Calculate the new installment amount
    new_installments_count = current_installments_count + 1  # Add one more installment
    new_installment_amount = total_amount / new_installments_count

    # Recalculate all existing installments to the new amount
    for installment in student.installments:
        installment.amount = new_installment_amount

    # Calculate the due date for the new installment
    course1 = CourseDetails.query.get(student.course_id)
    course_duration = course1.course_duration  # Total course duration in months
    gap_months = course_duration / new_installments_count  # Gap in months between installments

    # Calculate the due date for the new installment
    latest_due_date = max(installment.due_date for installment in student.installments)  # Get the latest due date
    new_due_date = latest_due_date + timedelta(days=gap_months * 30)  # Add the gap

    # Add the new installment
    new_installment = Installment(
        student_id=student.id,
        amount=new_installment_amount,
        due_date=new_due_date
    )
    db.session.add(new_installment)

    # Commit changes to the database
    db.session.commit()

    # Show a success message
    if f:
        flash(f"New installment added. All installments are now {new_installment_amount} each.", "success")

    return redirect(url_for('main.student_details', student_id=student.id))


@main.route('/delete-installment/<int:student_id>', methods=['POST'])
@login_required
def delete_installment(student_id):

    student = StudentDetails.query.get_or_404(student_id)
    # Get all installments for the student and sort by ID (assuming ID reflects creation order)
    installments = student.installments
    f =True
    if not installments:
        flash("No installments to delete.", "warning")
        return redirect(url_for('main.student_details', student_id=student_id))
    elif len(installments) == 1:
        flash("Only 1 installment remaining , You cannot delete it .", "error")
        return redirect(url_for('main.student_details', student_id=student_id))
    
    current_installments_count = len(student.installments)

    if current_installments_count == 3:
        total_amount = student.total_payable_amnt - student.course.price * 0.10
        student.total_payable_amnt = total_amount
        flash("Now you have 2 installment . You will now receive only 10%.", "success") 
        f = False 
    elif current_installments_count == 2:
        total_amount = student.total_payable_amnt - student.course.price * 0.15
        student.total_payable_amnt = total_amount
        flash("Now you have 1 installment . You will now receive only 25%.", "success")
        f = False
    
    # Find the latest installment (last added)
    latest_installment = sorted(installments, key=lambda i: i.id, reverse=True)[0]

    # Remove the latest installment from the database
    db.session.delete(latest_installment)
    db.session.commit()

    # Recalculate the installment amount for the remaining installments
    remaining_installments = student.installments  # Fetch again after deletion
    if remaining_installments:
        # Calculate the new installment amount
        new_installment_amount = student.total_payable_amnt / len(remaining_installments)
        for installment in remaining_installments:
            installment.amount = new_installment_amount

        # Commit the changes    
        db.session.commit()

    if f:
        flash("Latest installment deleted and amounts updated.", "error")
    return redirect(url_for('main.student_details', student_id=student_id))

@main.route('/add_payment', methods=['POST'])
def add_payment():
    # Get data from the request
    student_id = request.json.get('student_id')
    installment_id = request.json.get('installment_id')
    installment_amount = request.json.get('installment_amount')

    if not student_id or not installment_id or not installment_amount:
        return jsonify({"error": "Missing required fields"}), 400

    # Find the relevant installment and student
    installment = Installment.query.filter_by(id=installment_id, student_id=student_id).first()
    student = StudentDetails.query.filter_by(id=student_id).first()

    if not installment or not student:
        return jsonify({"error": "Invalid student or installment ID"}), 404

    # Check if the installment is already paid
    if installment.status == "Paid":
        return jsonify({"error": "This installment has already been paid"}), 400

    # Create a new payment history record
    payment = PaymentHistory(
        student_id=student_id,
        paid_amount=installment_amount,
        paid_date=datetime.utcnow().date(),
        paid_time=datetime.utcnow().time()
    )

    # Add the payment history record to the database
    db.session.add(payment)

    # Update the installment status to 'Paid'
    installment.status = "Paid"
    
    # Commit the transaction
    db.session.commit()

    return jsonify({
        "message": "Payment successfully recorded",
        "installment_status": installment.status,
        "paid_amount": payment.paid_amount,
    }), 200


@main.route('/generate_receipt/<int:student_id>/<int:installment_id>', methods=['POST'])
def generate_receipt(student_id, installment_id):
    data = request.get_json()
    amount = data.get('amount')
    # student_course = data.get('course')

    student = StudentDetails.query.get_or_404(student_id)
    # course = student.course.course_name

    total_fee = student.total_payable_amnt
    remaining_amount = total_fee - float(amount)
    remaining_amount = round(remaining_amount)
    
    if remaining_amount < 0:
        flash("No fees remaining.", "error")
        return redirect(url_for('main.student_details', student_id=student_id))
    student.total_payable_amnt = remaining_amount
    db.session.commit()

    # Generate PDF
    receipt_pdf = FPDF()
    receipt_pdf.add_page()
    # Add Logo (replace 'logo.png' with your logo file path)
   # Logo and Header
    receipt_pdf.image(r'C:\Shahid\MCC\Main Project\Ledger_management_system\Ledger-Mangement-System\app\static\logo.jpeg', x=10, y=8, w=20, h=20)
    receipt_pdf.set_y(20)  # Move to a lower position after the logo

    receipt_pdf.set_font("Arial", style='B', size=20)
    receipt_pdf.set_text_color(0, 51, 102)  # Dark blue
    receipt_pdf.cell(0, 10, txt=student.institute_name, ln=True, align='C')

    # Institute Details
    receipt_pdf.set_font("Arial", size=10)
    receipt_pdf.set_text_color(50, 50, 50)  # Gray
    receipt_pdf.cell(0, 6, txt="Address: Opp Radiance Academy, Tilak Nagar 90 feet Road, Near Sakinaka Metro Station, Mumbai-400072.", ln=True, align='C')
    receipt_pdf.cell(0, 6, txt="Contact: +91 9702328507 | Email: mumbaicodingclub@gmail.com", ln=True, align='C')
    receipt_pdf.cell(0, 6, txt="Website: https://mumbaicodingclub.com/", ln=True, align='C')
    receipt_pdf.ln(10)

    # Receipt Title
    receipt_pdf.set_font("Arial", style='B', size=16)
    receipt_pdf.set_text_color(0, 0, 0)  # Black
    receipt_pdf.cell(0, 10, txt="FEE RECEIPT", ln=True, align='C')
    receipt_pdf.ln(5)

    # Receipt Metadata
    receipt_pdf.set_font("Arial", size=10)
    receipt_pdf.set_text_color(100, 100, 100)  # Light gray
    receipt_pdf.cell(0, 6, txt=f"Receipt No: unique_receipt_id", ln=True, align='R')  # Replace with unique logic
    receipt_pdf.cell(0, 6, txt=f"Issue Date: {datetime.utcnow().strftime('%d-%m-%Y')}", ln=True, align='R')
    receipt_pdf.ln(10)

    # Line Separator
    receipt_pdf.set_draw_color(0, 51, 102)  # Dark blue
    receipt_pdf.set_line_width(0.5)
    receipt_pdf.line(10, receipt_pdf.get_y(), 200, receipt_pdf.get_y())
    receipt_pdf.ln(5)

    # Student Details Section
    receipt_pdf.set_font("Arial", style='B', size=12)
    receipt_pdf.set_text_color(0, 51, 102)  # Dark blue
    receipt_pdf.cell(0, 10, txt="STUDENT DETAILS", ln=True, align='C')  # Centered header
    receipt_pdf.ln(5)

    # Using a table-like approach to align student info
    receipt_pdf.set_font("Arial", size=10)
    receipt_pdf.set_text_color(0, 0, 0)  # Black

    # Adjusting widths to balance the content
    receipt_pdf.cell(40, 8, txt="Name:", border=1, align='L')  # Label with border
    receipt_pdf.cell(0, 8, txt=f"{student.student_name}", border=1, align='L')  # Value with border
    receipt_pdf.ln(8)  # Line break

    receipt_pdf.cell(40, 8, txt="Contact:", border=1, align='L')
    receipt_pdf.cell(0, 8, txt=f"{student.student_contact}", border=1, align='L')
    receipt_pdf.ln(8)

    receipt_pdf.cell(40, 8, txt="Email:", border=1, align='L')
    receipt_pdf.cell(0, 8, txt=f"{student.student_mail}", border=1, align='L')
    receipt_pdf.ln(10)

    # Payment Details Section
    receipt_pdf.set_font("Arial", style='B', size=12)
    receipt_pdf.set_text_color(0, 51, 102)  # Dark blue
    receipt_pdf.cell(0, 10, txt="PAYMENT DETAILS", ln=True, align='C')  # Centered header
    receipt_pdf.ln(5)

    # Using a table-like approach to align payment info
    receipt_pdf.set_font("Arial", size=10)
    receipt_pdf.set_text_color(0, 0, 0)  # Black

    receipt_pdf.cell(40, 8, txt="Course Name:", border=1, align='L')
    receipt_pdf.cell(0, 8, txt=f"{student.course.course_name}", border=1, align='L')
    receipt_pdf.ln(8)

    receipt_pdf.cell(40, 8, txt="Total Fee:", border=1, align='L')
    receipt_pdf.cell(0, 8, txt=f"{student.course.price} Rs.", border=1, align='L')
    receipt_pdf.ln(8)

    receipt_pdf.cell(40, 8, txt="Installment No:", border=1, align='L')
    receipt_pdf.cell(0, 8, txt=f"{installment_id}", border=1, align='L')
    receipt_pdf.ln(8)

    receipt_pdf.cell(40, 8, txt="Amount Paid:", border=1, align='L')
    receipt_pdf.cell(0, 8, txt=f"{amount} Rs.", border=1, align='L')
    receipt_pdf.ln(8)

    receipt_pdf.cell(40, 8, txt="Remaining Balance:", border=1, align='L')
    receipt_pdf.cell(0, 8, txt=f"{remaining_amount} Rs.", border=1, align='L')
    receipt_pdf.ln(10)
    # Footer Section
    receipt_pdf.set_draw_color(200, 200, 200)  # Light gray
    receipt_pdf.set_line_width(0.3)
    receipt_pdf.line(10, receipt_pdf.get_y(), 200, receipt_pdf.get_y())
    receipt_pdf.ln(5)
    receipt_pdf.set_font("Arial", style='B', size=10)
    receipt_pdf.set_text_color(50, 50, 50)  # Gray
    receipt_pdf.cell(0, 8, txt="Thank you for your payment!", ln=True, align='C')
    receipt_pdf.cell(0, 8, txt="This receipt is computer-generated and does not require a signature.", ln=True, align='C')

    receipt_filename = f"{student_id}_{installment_id}_receipt.pdf"
    receipt_filepath = os.path.join('app/static/receipts', receipt_filename)
    os.makedirs(os.path.dirname(receipt_filepath), exist_ok=True)
    receipt_pdf.output(receipt_filepath)

    # Send Email
    email_subject = "Your Fee Receipt"
    email_body = f"""
    Dear {student.student_name},

    Thank you for your payment.

    Amount Paid: {amount} Rs.
    Remaining Amount: {remaining_amount} Rs.

    Please find the receipt attached.
    """
    try:
        send_email(
            recipient_email=student.student_mail,
            subject=email_subject,
            body=email_body,
            attachment_path=receipt_filepath,
            attachment_filename=receipt_filename
        )
    except Exception as e:
        flash(f"Failed to send receipt email: {e}", "error")

    return jsonify({
        'success': True,
        'receiptUrl': f'/static/receipts/{receipt_filename}'
    })



def send_email(recipient_email, subject, body, attachment_path, attachment_filename):
    """Helper function to send email with an attachment."""
    try:
        # Create the email message
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=body
        )

        # Attach the PDF file
        with open(attachment_path, 'rb') as attachment:
            msg.attach(
                filename=attachment_filename,
                content_type='application/pdf',
                data=attachment.read()
            )

        # Send the email
        mail.send(msg)
        print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")