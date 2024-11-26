from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import re
from app.models.models import User

auth = Blueprint("auth", __name__)


@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # Trim spaces and validate inputs
        username = request.form.get("username").strip()
        institute_name = request.form.get("institute_name").strip()
        address = request.form.get("address").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        confirm_password = request.form.get("confirm_password").strip()

        # Check if any field is empty or only spaces
        if not all(
            [username, institute_name, address, email, password, confirm_password]
        ):
            flash("Please fill in all required fields without only spaces.", "error")
            return redirect(url_for("auth.signup"))

        if not (
            username.isalpha()
            or re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$", username)
        ):
            flash("Please fill the correct username.", "error")
            return redirect(url_for("auth.signup"))

        if institute_name.isdigit():
            flash(
                "Institute name should contain only alphabetic characters and spaces.",
                "error",
            )
            return redirect(url_for("auth.signup"))

        if not address or not re.match(r"^[A-Za-z0-9\s,.-]+$", address):
            flash(
                "Address should only contain letters, numbers, spaces, commas, periods, and hyphens.",
                "error",
            )
            return redirect(url_for("auth.signup"))

        # Email format validation
        if not re.match(
            r"^[a-zA-Z][a-zA-Z0-9_.+-]*@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$", email
        ):
            flash("Invalid email format.", "error")
            return redirect(url_for("auth.signup"))

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("auth.signup"))

        # Check if username or email already exists
        if (
            User.query.filter_by(username=username).first()
            or User.query.filter_by(email=email).first()
        ):
            flash("Username or email already exists", "error")
            return redirect(url_for("auth.signup"))

        # Password strength validation (e.g., minimum length, containing letters and digits)
        # if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        #     flash("Password should be at least 8 characters long and contain both letters and numbers.", "error")
        #     return redirect(url_for("auth.signup"))

        # Hash the password and save the user
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(
            username=username,
            institute_name=institute_name,
            address=address,
            email=email,
            password=hashed_password,
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("signup.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Get the username and password from the form
        username = request.form.get("username")
        password = request.form.get("password")

        # Query for the user
        user = User.query.filter_by(username=username).first()

        # Validate credentials
        if user and check_password_hash(user.password, password):
            # If credentials match, set session and mark it as permanent
            session["user_id"] = user.id
            session.permanent = True  # Ensures session expiration on inactivity
            flash("Login successful!", "success")
            return redirect(url_for("main.home"))
        else:
            # If credentials don't match, show an error
            flash("Invalid login details. Please try again.", "error")
            return render_template("login.html")

    # If GET request, render the login page
    return render_template("login.html")


@auth.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        email = request.form.get("email").strip()
        new_password = request.form.get("new_password").strip()

        print(email)
        print(new_password)

        # Fetch user by email
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email not found. Please provide a valid email.", "error")
            return redirect(url_for("auth.reset_password"))

        # Update to new password
        user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
        db.session.commit()

        flash("Password reset successful! You can now log in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("forgetpass.html")