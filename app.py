from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash
import sqlalchemy as sa
from flask import Flask, jsonify, request
from dataclasses import dataclass, field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy as sa
import jwt

#change might be required here!
from utils import *

app = Flask(__name__)



connection_url = sa.engine.URL.create(
    "mssql+pyodbc",
    host="localhost",
    database="BriefDB",
    query={
        "driver": "ODBC Driver 17 for SQL Server",
        "trusted_connection": "yes",
        "autocommit": "True",
    },
)

engine = sa.create_engine(connection_url)



# ALL API ROUTES STARTS HERE 
@app.route("/api")
@token_required
def home():
    return jsonify({"status": "ok"})


@app.route('/api/test-db', methods=['GET'])
def test_db_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return jsonify({'message': 'Database connection successful!', 'statusCode': 200, 'status': 'success'}), 200
    except Exception as e:
        return jsonify({'message': 'Database connection failed!', 'error': str(e), 'statusCode': 500, 'status': 'error'}), 500


@app.route('/api/register', methods=['POST'])
def register():

    try:
        with engine.connect() as connection:
            for user in users_data:
                password_hash = generate_password_hash(user["password"])

                insert_query = text("""
                    INSERT INTO [dbo].[user_data] 
                    (username, password, user_firstname, user_lastname, user_email, role) 
                    VALUES (:username, :password, :user_firstname, :user_lastname, :user_email, :role)
                """)
                connection.execute(insert_query, {
                    "username": user["username"],
                    "password": password_hash,
                    "user_firstname": user["user_firstname"],
                    "user_lastname": user["user_lastname"],
                    "user_email": user["user_email"],
                    "role": user["role"]
                })

        return jsonify({'message': 'Users registered successfully!', 'statusCode': 200, 'status': 'success'}), 201

    except SQLAlchemyError as e:
        return jsonify({'message': 'User registration failed!', 'error': str(e), 'statusCode': 500, 'status': 'error'}), 500


@app.route('/api/login', methods=['POST'])
@json_required
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required!', 'statusCode': 400, 'status': 'error'}), 400

    try:
        with engine.connect() as connection:
            user_table_query_string = text("""
                SELECT username, password, is_active, user_id 
                FROM [dbo].[user_data] 
                WHERE username = :username
            """)

            user_table_data = connection.execute(
                user_table_query_string, {"username": username}).fetchall()

            # Check if user exists
            if not user_table_data:
                return jsonify({'message': 'User not found!', 'statusCode': 404, 'status': 'error'}), 404

            # Get the first (and only) user data
            user_data = user_table_data[0]

            # Check if the user is active
            if not user_data.is_active:
                return jsonify({'message': 'User account is inactive!', 'statusCode': 403, 'status': 'error'}), 403

            # Verify the password
            if not check_password_hash(user_data.password, password):
                return jsonify({'message': 'Invalid username or password!', 'statusCode': 401, 'status': 'error'}), 401

            # Create JWT token
            token = jwt.encode({'user_id': user_data.user_id, 'exp': datetime.now(
            ) + timedelta(days=30)}, JWT_SECRECT_KEY, algorithm='HS256')

            return jsonify({'token': token, 'statusCode': 200, 'status': 'Success', "message": "Logged in successfully"}), 200

    except SQLAlchemyError as e:
        return jsonify({'message': 'Login failed!', 'error': str(e), 'statusCode': 500, 'status': 'error'}), 500


@app.route('/api/submit_brief', methods=['POST'])
@json_required
@token_required
def submit_brief(user_id):
    # Check if the user is a Creator
    try:
        with engine.connect() as connection:
            user_query = text("""
                SELECT role FROM [dbo].[user_data] WHERE user_id = :user_id
            """)
            user_role = connection.execute(
                user_query, {"user_id": user_id}).fetchone()

            if not user_role or user_role.role != 'Creator':
                return jsonify({
                    'message': 'Unauthorized: Only Creator role users can submit a brief!',
                    'statusCode': 403,
                    'status': 'error'
                }), 403

            data = request.get_json()

            # Convert lists to comma-separated strings
            city = ', '.join(data.get('city', []))
            npd_stage_gates = ', '.join(data.get('npd_stage_gates', []))

            with engine.connect() as connection:
                insert_query = text("""
                    INSERT INTO [dbo].[research_brief] 
                    (creator_id, category_type, product_type, brand, study_type, 
                    market_objective, research_objective, research_tg, 
                    research_design, key_information_area, deadline, 
                    city, npd_stage_gates, epd_stage, file_attachment) 
                    VALUES (:creator_id, :category_type, :product_type, :brand, :study_type, 
                    :market_objective, :research_objective, :research_tg, 
                    :research_design, :key_information_area, :deadline, 
                    :city, :npd_stage_gates, :epd_stage, :file_attachment)
                """)

                # Create a dictionary for parameters
                params = {
                    'creator_id': user_id,
                    'category_type': data.get('category_type'),
                    'product_type': data.get('product_type'),
                    'brand': data.get('brand'),
                    'study_type': data.get('study_type'),
                    'market_objective': data.get('market_objective'),
                    'research_objective': data.get('research_objective'),
                    'research_tg': data.get('research_tg'),
                    'research_design': data.get('research_design'),
                    'key_information_area': data.get('key_information_area'),
                    'deadline': data.get('deadline'),
                    'city': city,  # Comma-separated string for city
                    'npd_stage_gates': npd_stage_gates,  # Comma-separated string for npd_stage_gates
                    'epd_stage': data.get('epd_stage'),
                    'file_attachment': data.get('file_attachment')
                }

                # Execute the query with the parameters
                connection.execute(insert_query, params)
            
            return jsonify({
                'message': 'Research brief submitted successfully!',
                'statusCode': 200,
                'status': 'success'
            }), 201

    except SQLAlchemyError as e:
        return jsonify({
            'message': 'Brief submission failed!',
            'error': str(e),
            'statusCode': 500,
            'status': 'error'
        }), 500


if __name__ == '__main__':
    app.run(debug=True)
