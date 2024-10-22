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
    try:
        with engine.connect() as connection:
            user_query = text("""
                SELECT role FROM [dbo].[user_data] WHERE user_id = :user_id
            """)
            user_role = connection.execute(
                user_query, {"user_id": user_id}).fetchone()

            # Check if the user is a Creator
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
                connection.execute(insert_query, params)

                brief_id_query = text(
                    "SELECT IDENT_CURRENT('research_brief') AS [IDENT_CURRENT]")
                brief_id_result = connection.execute(brief_id_query).fetchone()
                print(brief_id_result)
                if brief_id_result is None:
                    return jsonify({
                        'message': 'Failed to retrieve the brief ID!',
                        'statusCode': 500,
                        'status': 'error'
                    }), 500

                brief_id = brief_id_result[0]
                print(brief_id)

                # Insert into brief_status_actions with a status of 'Pending'
                status_insert_query = text("""
                    INSERT INTO [dbo].[brief_status_actions] 
                    (brief_id, status) 
                    VALUES (:brief_id, 'Pending')
                """)

                # Execute the status insert query
                connection.execute(status_insert_query, {'brief_id': brief_id})

            
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


@app.route('/api/approve_brief/<int:brief_id>', methods=['PUT'])
@token_required
@json_required
def approve_brief(user_id, brief_id):
    data = request.get_json()

    # Get required fields
    start_date = data.get('start_date')
    po_approval = data.get('po_approval')
    agency_finalisation = data.get('agency_finalisation')
    questionnaire_coding_date = data.get('questionnaire_coding_date')
    cpi_total = data.get('cpi_total')
    travel_cost = data.get('travel_cost')
    miscellaneous_cost = data.get('miscellaneous_cost')
    total_cost = data.get('total_cost')
    research_design_attachment = data.get('research_design_attachment')

    if not all([start_date, po_approval, agency_finalisation, questionnaire_coding_date, cpi_total, travel_cost, miscellaneous_cost, total_cost]):
        return jsonify({
            'message': 'All fields for approval must be filled!',
            'statusCode': 400,
            'status': 'error'
        }), 400

    try:
        with engine.connect() as connection:
            # Ensure the user is a Project Coordinator (the receiver)
            user_role_query = text("""
                SELECT role FROM [dbo].[user_data] WHERE user_id = :user_id
            """)
            user_role = connection.execute(
                user_role_query, {"user_id": user_id}).fetchone()

            if not user_role or user_role.role != 'Project Coordinator':
                return jsonify({
                    'message': 'Unauthorized: Only Project Coordinators can approve briefs!',
                    'statusCode': 403,
                    'status': 'error'
                }), 403

            # Update the status to 'Approved'
            update_or_insert_query = text("""
                MERGE INTO [dbo].[brief_status_actions] AS target
                USING (VALUES (:brief_id, :user_id, :start_date, :po_approval, :agency_finalisation, :questionnaire_coding_date, :cpi_total, :travel_cost, :miscellaneous_cost, :total_cost, :research_design_attachment))
                AS source (brief_id, user_id, start_date, po_approval, agency_finalisation, questionnaire_coding_date, cpi_total, travel_cost, miscellaneous_cost, total_cost, research_design_attachment)
                ON target.brief_id = source.brief_id

                -- If the row exists, update it
                WHEN MATCHED THEN
                    UPDATE SET
                        target.status = 'Approved',
                        target.approved_by = source.user_id,
                        target.start_date = source.start_date,
                        target.po_approval = source.po_approval,
                        target.agency_finalisation = source.agency_finalisation,
                        target.questionnaire_coding_date = source.questionnaire_coding_date,
                        target.cpi_total = source.cpi_total,
                        target.travel_cost = source.travel_cost,
                        target.miscellaneous_cost = source.miscellaneous_cost,
                        target.total_cost = source.total_cost,
                        target.research_design_attachment = source.research_design_attachment,
                        target.update_date = GETDATE()

                -- If the row does not exist, insert it
                WHEN NOT MATCHED THEN
                    INSERT (brief_id, status, approved_by, start_date, po_approval, agency_finalisation, questionnaire_coding_date,
                            cpi_total, travel_cost, miscellaneous_cost, total_cost, research_design_attachment, update_date)
                    VALUES (source.brief_id, 'Approved', source.user_id, source.start_date, source.po_approval, source.agency_finalisation, source.questionnaire_coding_date,
                            source.cpi_total, source.travel_cost, source.miscellaneous_cost, source.total_cost, source.research_design_attachment, GETDATE());
            """)


            # Execute the query
            connection.execute(update_or_insert_query, {
                'user_id': user_id,
                'start_date': start_date,
                'po_approval': po_approval,
                'agency_finalisation': agency_finalisation,
                'questionnaire_coding_date': questionnaire_coding_date,
                'cpi_total': cpi_total,
                'travel_cost': travel_cost,
                'miscellaneous_cost': miscellaneous_cost,
                'total_cost': total_cost,
                'research_design_attachment': research_design_attachment,
                'brief_id': brief_id
            })


            return jsonify({
                'message': 'Brief approved successfully!',
                'statusCode': 200,
                'status': 'success'
            }), 200

    except SQLAlchemyError as e:
        return jsonify({
            'message': 'Failed to approve the brief!',
            'error': str(e),
            'statusCode': 500,
            'status': 'error'
        }), 500


@app.route('/api/reject_brief/<int:brief_id>', methods=['PUT'])
@token_required
@json_required
def reject_brief(user_id, brief_id):
    data = request.get_json()

    # Get required fields
    rejection_reason = data.get('rejection_reason')

    if not rejection_reason:
        return jsonify({
            'message': 'Rejection reason is required!',
            'statusCode': 400,
            'status': 'error'
        }), 400

    try:
        with engine.connect() as connection:
            # Ensure the user is a Project Coordinator (the receiver)
            user_role_query = text("""
                SELECT role FROM [dbo].[user_data] WHERE user_id = :user_id
            """)
            user_role = connection.execute(
                user_role_query, {"user_id": user_id}).fetchone()

            if not user_role or user_role.role != 'Project Coordinator':
                return jsonify({
                    'message': 'Unauthorized: Only Project Coordinators can reject briefs!',
                    'statusCode': 403,
                    'status': 'error'
                }), 403

            # Update the status to 'Disapproved' and log rejection details
            update_query = text("""
                UPDATE [dbo].[brief_status_actions]
                SET status = 'Disapproved',
                    rejected_by = :user_id,
                    rejection_reason = :rejection_reason,
                    update_date = GETDATE()
                WHERE brief_id = :brief_id
            """)

            connection.execute(update_query, {
                'user_id': user_id,
                'rejection_reason': rejection_reason,
                'brief_id': brief_id
            })

            return jsonify({
                'message': 'Brief rejected successfully!',
                'statusCode': 200,
                'status': 'success'
            }), 200

    except SQLAlchemyError as e:
        return jsonify({
            'message': 'Failed to reject the brief!',
            'error': str(e),
            'statusCode': 500,
            'status': 'error'
        }), 500


@app.route('/api/reviewer/all_briefs', methods=['GET'])
@token_required
def get_all_pending_briefs(user_id):
    try:
        # Check if the user is a receiver
        with engine.connect() as connection:
            user_query = text("""
                SELECT role FROM [dbo].[user_data] WHERE user_id = :user_id
            """)
            user_role = connection.execute(
                user_query, {"user_id": user_id}).fetchone()

            # Check if the user is a Project Coordinator
            if not user_role or user_role.role != 'Project Coordinator':
                return jsonify({
                    'message': 'Unauthorized: Only Project Coordinator can access this endpoint!',
                    'statusCode': 403,
                    'status': 'error'
                }), 403

            query = text("""
                SELECT
                    rb.category_type AS category,
                    rb.product_type,
                    rb.study_type,
                    rb.brand,
                    rb.research_design AS research_type,
                    bsa.total_cost,
                    rb.deadline
                FROM
                    [dbo].[research_brief] rb
                JOIN
                    [dbo].[brief_status_actions] bsa ON rb.brief_id = bsa.brief_id
                WHERE
                    bsa.status = 'Pending'
            """)


            results = connection.execute(query).fetchall()

            # Update the dictionary comprehension to match the selected columns
            briefs = [{
                'category': row[0],
                'product_type': row[1],
                'study_type': row[2],
                'brand': row[3],
                'research_type': row[4],  
                'total_cost': row[5],      
                'deadline': row[6]        
            } for row in results]

            return jsonify({
                'message': 'All pending briefs fetched successfully!',
                'briefs': briefs,
                'statusCode': 200,
                'status': 'success'
            }), 200

    except SQLAlchemyError as e:
        return jsonify({
            'message': 'Failed to fetch briefs!',
            'error': str(e),
            'statusCode': 500,
            'status': 'error'
        }), 500


@app.route('/api/reviewer/todays_deadlines', methods=['GET'])
@token_required
def get_todays_deadlines(user_id):
    try:
        # Check if the user is a receiver
        with engine.connect() as connection:
            user_query = text("""
                SELECT role FROM [dbo].[user_data] WHERE user_id = :user_id
            """)
            user_role = connection.execute(
                user_query, {"user_id": user_id}).fetchone()

            # Check if the user is a Project Coordinator
            if not user_role or user_role.role != 'Project Coordinator':
                return jsonify({
                    'message': 'Unauthorized: Only Project Coordinator can access this endpoint!',
                    'statusCode': 403,
                    'status': 'error'
                }), 403

            query = text("""
                SELECT 
                    rb.category_type AS category, 
                    rb.product_type, 
                    rb.study_type, 
                    rb.brand, 
                    rb.deadline
                FROM 
                    [dbo].[research_brief] rb
                JOIN 
                    [dbo].[brief_status_actions] bsa ON rb.brief_id = bsa.brief_id
                WHERE 
                    bsa.status = 'Pending' AND 
                    CONVERT(date, rb.deadline) = CONVERT(date, GETDATE())
            """)

            results = connection.execute(query).fetchall()

            # Use the correct column names to create a dictionary
            briefs = [{
                'category': row[0],
                'product_type': row[1],
                'study_type': row[2],
                'brand': row[3],
                'deadline': row[4]
            } for row in results]

            return jsonify({
                'message': 'Today\'s deadlines fetched successfully!',
                'briefs': briefs,
                'statusCode': 200,
                'status': 'success'
            }), 200

    except SQLAlchemyError as e:
        return jsonify({
            'message': 'Failed to fetch briefs!',
            'error': str(e),
            'statusCode': 500,
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
