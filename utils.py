from dataclasses import dataclass
from functools import wraps
from flask import jsonify, request
import jwt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine, text

SCHEMA_NAME = "BriefDB"
JWT_SECRECT_KEY = "BriefDB"  # os.getenv("JWT_SECRECT")
USERS_TABLE_NAME = "user_data"
ERROR_MESSAGE_FOR_WRONG_TOKEN = "Session expired, Login again!"
ERROR_MESSAGE_FETCHING_DATA = 'An error occurred while fetching data.'
ERROR_MESSAGE_INVALID_ID = 'An error occurred while fetching data.'
ERROR_MESSAGE_FOR_DATA_TYPE_JSON = 'Request must be a JSON'
ERROR_NO_DATA_FOR_GIVEN_ID = "No data found the given id."
SUCCESS_MESSAGE_FETCHED_DATA = 'Data retrieved successfully.'
# Example hardcoded users data
users_data = [
    {
        "username": "superadmin",
        "password": "superadmin123",
        "user_firstname": "Super",
        "user_lastname": "Admin",
        "user_email": "superadmin@example.com",
        "role": "Super Admin"
    },
    {
        "username": "admin",
        "password": "admin123",
        "user_firstname": "Admin",
        "user_lastname": "User",
        "user_email": "admin@example.com",
        "role": "Admin"
    },
    {
        "username": "coordinator",
        "password": "coordinator123",
        "user_firstname": "Project",
        "user_lastname": "Coordinator",
        "user_email": "coordinator@example.com",
        "role": "Project Coordinator"
    },
    {
        "username": "creator",
        "password": "creator123",
        "user_firstname": "Content",
        "user_lastname": "Creator",
        "user_email": "creator@example.com",
        "role": "Creator"
    }
]


@dataclass(frozen=True, kw_only=True)
class GetQueryStringMaker:
    table_name: str
    schema: str
    columns: str
    condition: str


class GetQueryStringReturn(GetQueryStringMaker):
    def unique_values_of_given_column(self):
        return text(f'SELECT DISTINCT {self.columns} FROM {self.schema}.{self.table_name}')

    def unique_values_of_given_columns_with_condition(self):
        return text(f'SELECT DISTINCT {self.columns} FROM {self.schema}.{self.table_name} WHERE {self.condition}')

    def all_data_of_given_columns(self):
        return text(f'SELECT {self.columns} FROM {self.schema}.{self.table_name}')

    def all_data_of_given_columns_with_condition(self):
        return text(f'SELECT {self.columns} FROM {self.schema}.{self.table_name} WHERE {self.condition}')


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message': ERROR_MESSAGE_FOR_WRONG_TOKEN, "statusCode": 401, "status": "error"}), 401

        try:
            data = jwt.decode(token, JWT_SECRECT_KEY, algorithms=["HS256"])
            user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': ERROR_MESSAGE_FOR_WRONG_TOKEN, "statusCode": 401, "status": "error"}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': ERROR_MESSAGE_FOR_WRONG_TOKEN, "statusCode": 401, "status": "error"}), 401

        return f(user_id, *args, **kwargs)

    return decorated


def json_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                "message": ERROR_MESSAGE_FOR_DATA_TYPE_JSON,
                "error": ERROR_MESSAGE_FOR_DATA_TYPE_JSON,
                "statusCode": 500,
                "status": "error"
            }), 500
        return f(*args, **kwargs)
    return decorated_function


def get_column_names(connection, table_name: str, schema: str):
    """Retrieve column names for a given table."""
    query = text('''
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = :table_name
        AND TABLE_SCHEMA = :schema;
    ''')

    try:
        result = connection.execute(
            query, {"table_name": table_name, "schema": schema})
        return [row[0] for row in result]
    except SQLAlchemyError as e:
        return str(e)


def get_table_data(connection, query, columns):
    """
    Retrieve data from the specified table
    """
    try:
        data_results = connection.execute(query)
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error occurred: {e}") from e

    rows = data_results.fetchall()

    if rows:
        return [
            {column: value for column, value in zip(columns, row)}
            for row in rows
        ]
    else:
        return None
