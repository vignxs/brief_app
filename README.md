
# Brief Management Flask Application

This is a Flask-based application that handles user roles (SuperAdmin, Admin, Creator, Receiver) and allows users to create and manage project briefs. 

## Table of Contents
1. [Requirements](#requirements)
2. [Setup](#setup)
3. [Running the Application](#running-the-application)
4. [API Endpoints](#api-endpoints)
   - [Create SuperAdmin](#1-create-superadmin)
   - [Login](#2-login)
   - [Create Admin, Creator, and Receiver](#3-create-admin-creator-and-receiver)
   - [Create Brief](#4-create-brief)
   - [Get All Briefs](#5-get-all-briefs)
5. [Author](#author)

## Requirements

- Python 3.x
- Flask
- Flask-JWT-Extended
- Flask-SQLAlchemy
- Flask-CORS
- SQLAlchemy

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your database in `config.py` as needed for SQLAlchemy.

4. Initialize the database:
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

## Running the Application

To run the Flask application, use the following command:

```bash
flask run
```

By default, the application will be available at `http://localhost:5000`.

## API Endpoints

### 1. Create SuperAdmin
**Endpoint:** `/create_superadmin`  
**Method:** `POST`  
**Body:**
```json
{
    "username": "admin",
    "password": "password123",
    "user_firstname": "Super",
    "user_lastname": "Admin",
    "user_email": "admin@example.com"
}
```
**Description:**  
This endpoint is used to create the SuperAdmin account. Only one SuperAdmin can exist in the system.

### 2. Login
**Endpoint:** `/login`  
**Method:** `POST`  
**Body:**
```json
{
    "username": "admin",
    "password": "password123"
}
```
**Response:**
```json
{
    "access_token": "your_jwt_token"
}
```
**Description:**  
Log in with the username and password. Upon successful login, you'll receive an access_token for further authenticated requests.

### 3. Create Admin, Creator, and Receiver
**Endpoint:** `/register`  
**Method:** `POST`  
**Headers:**  
`Authorization: Bearer <access_token>`  
**Body:**
```json
{
    "username": "creator",
    "password": "cpassword123",
    "email": "creator@example.com",
    "user_firstname": "New",
    "user_lastname": "Creator",
    "role": "creator"
}
```
**Description:**  
The SuperAdmin can create Admin users, and Admin users can create Creator and Receiver accounts.

### 4. Create Brief
**Endpoint:** `/briefs`  
**Method:** `POST`  
**Headers:**  
`Authorization: Bearer <access_token>`  
**Body:**
```json
{
    "category": "Marketing Research",
    "priority": "High",
    "brand": "BrandX",
    "study_type": "Qualitative",
    "comments": "This is an urgent research request.",
    "previous_research": "No prior research available.",
    "market_objective": "Increase market share.",
    "research_objective": "Understand consumer preferences.",
    "research_tg": "Age 25-40, urban professionals",
    "research_design": "Focus groups and in-depth interviews",
    "key_information_area": "Consumer attitudes, brand perception",
    "deadline": "2024-10-30",
    "additional_information": "Please prioritize data collection in New York and LA.",
    "city": "New York",
    "stimulus_dispatch_date": "2024-10-20",
    "status": "waiting_for_approval",
    "attachments": "link_to_file.pdf",
    "approved": false,
    "approved_by": null,
    "rejection_reason": null,
    "rejection_date": null,
    "budget": 10000.00,
    "total_cost": null,
    "brief_creator_id": 1
}
```
**Description:**  
This endpoint allows users with the Creator role to create a new brief.

### 5. Get All Briefs
**Endpoint:** `/briefs`  
**Method:** `GET`  
**Headers:**  
`Authorization: Bearer <access_token>`  
**Description:**  
This endpoint fetches all briefs. The response will differ based on the role of the user:

- **Creators**: Fetch briefs created by the user.
- **Receivers**: Fetch briefs waiting for approval.
- **Admins/SuperAdmins**: Fetch all briefs.

## Author
This Flask application was developed by Dhivya Udayakumar. It serves as a backend for a project management platform focusing on brief submissions and approvals.
