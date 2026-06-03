# Secure Web-Based Attendance Management System

## Overview

The Secure Web-Based Attendance Management System is a Flask-based web application developed to automate attendance recording, user management, and attendance monitoring within an educational environment. The system provides separate access levels for administrators, teachers, and students while incorporating multiple security mechanisms to protect user accounts and attendance records.

The project was developed as an individual software engineering project and demonstrates practical implementation of web development, database management, authentication systems, and cybersecurity controls.

---

## Project Information

**Project Type:** Individual Project

**Development Duration:** February 2025 – March 2025

**Technologies Used:**

* Python
* Flask
* Flask-Login
* Flask-SQLAlchemy
* Flask-WTF
* Flask-Mail
* SQLite
* HTML
* CSS
* bcrypt

---

## Key Features

### Authentication & Security

* Secure password hashing using bcrypt
* CAPTCHA verification after multiple failed login attempts
* Login attempt limitation to prevent brute-force attacks
* Automatic account lockout after repeated failed logins
* OTP-based account recovery through email verification
* OTP expiration and resend functionality
* Password strength validation
* Session management
* Role-based access control
* Unauthorized page access prevention

### Administration Module

* Admin dashboard
* Create teacher accounts
* Create student accounts
* Create subjects
* Enroll students into subjects
* View attendance analytics
* Manage users
* Delete user accounts

### Teacher Module

* Teacher dashboard
* Subject management
* Attendance marking
* Student attendance monitoring

### Student Module

* Student dashboard
* Attendance history tracking
* Attendance percentage calculation
* Profile access

### Email Integration

* Teacher account creation notifications
* Student account creation notifications
* OTP verification emails
* Account recovery support

---

## System Architecture

The system follows a role-based architecture consisting of:

### Administrator

Responsible for:

* User management
* Subject creation
* Student enrollment
* Attendance monitoring

### Teacher

Responsible for:

* Managing assigned students
* Marking attendance
* Monitoring attendance records

### Student

Responsible for:

* Viewing attendance records
* Tracking attendance percentages
* Managing account credentials

---

## Security Controls Implemented

Several common web application security risks were identified and mitigated:

| Security Risk             | Mitigation                   |
| ------------------------- | ---------------------------- |
| Brute Force Login Attacks | Login Attempt Limitation     |
| Automated Login Attacks   | CAPTCHA Verification         |
| Weak Passwords            | Password Strength Validation |
| Password Storage Risk     | bcrypt Hashing               |
| Unauthorized Page Access  | Role-Based Access Control    |
| Account Recovery Risk     | OTP Verification             |
| Session Hijacking Risk    | Session Management           |

---

## Database

Database Technology:

* SQLite

Main Database Tables:

* User
* Attendance
* Subject
* TeacherStudentEnrollment

The database stores user credentials, attendance records, subject information, enrollment data, login security information, and account recovery data.

---

## Screenshots

### Login Page

(Add Screenshot)

### Register Page

(Add Screenshot)

### Teacher Dashboard

(Add Screenshot)

### Student Dashboard

(Add Screenshot)

### Attendance Records

(Add Screenshot)

---

## Project Demonstration

A complete video demonstration of the system is available in the Project_Demo folder.

---

## Source Code

The complete source code, database structure, and supporting files are included in this repository.

---

## Learning Outcomes

Through this project, practical experience was gained in:

* Flask Web Development
* Database Design
* Authentication Systems
* Cybersecurity Principles
* Session Management
* Role-Based Access Control
* Secure Password Storage
* Email Integration
* Software Testing and Debugging

---

## Future Improvements

* QR Code Attendance
* Facial Recognition Attendance
* Mobile Application Integration
* Cloud Database Support
* Advanced Analytics Dashboard
* Multi-Institution Deployment

---

## Author

Noor Ur Rashid

Bachelor of Computer Engineering

Asia Pacific University of Technology & Innovation (APU)

GitHub:
https://github.com/Noor-Ur-Rashid

LinkedIn:
https://www.linkedin.com/in/noor-ur-rashid-148b352a3/
