from flask import Flask, jsonify,request
from dataclasses import dataclass,field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy as sa
import os,jwt,ast,time,random,re
import uuid,base64
from azure.storage.blob import BlobServiceClient, ContentSettings
from datetime import datetime,timedelta
import pytz

kolkata_tz = pytz.timezone('Asia/Kolkata')

load_dotenv()

app = Flask(__name__)
blob_service_client = BlobServiceClient.from_connection_string(f"{os.getenv("AZURE_BLOB_CONNECTION_STRING")}")
AZURE_BLOB_CONTAINER_NAME = "distributorkpi"
QUESTIONS_TABLE_NAME="questions_new"
USERS_TABLE_NAME="user_data"
RESPONSE_TABLE_NAME="response"
DISTRIBUTOR_STOCK_TABLE_NAME="distributorStock"
RESPONSE_IMAGE_TABLE_NAME="response_image"
RESPONSE_SUMMARY_TABLE_NAME="response_summary"
SALES_HIERARCHY_TABLE_NAME="salesHierarchy"
DIGITAL_TABLE='digitalResponse'
SCHEMA_NAME="asmkpi"
JWT_SECRECT_KEY=os.getenv("JWT_SECRECT")
ERROR_MESSAGE_FOR_WRONG_TOKEN="Session expired, Login again!"
ERROR_MESSAGE_FETCHING_DATA='An error occurred while fetching data.'
ERROR_MESSAGE_INVALID_ID='An error occurred while fetching data.'
ERROR_MESSAGE_FOR_DATA_TYPE_JSON='Request must be a JSON'
ERROR_NO_DATA_FOR_GIVEN_ID="No data found the given id."
SUCCESS_MESSAGE_FETCHED_DATA='Data retrieved successfully.'
DISTRIBUTOR_QUESTIONS_SERIES_START_VALUE=3
DISTRIBUTOR_QUESTIONS_SERIES_END_VALUE=31
ADMINISTRATIVE_CAPABILITY_IMAGES_FOLDER_IN_AZURE='admin_capability'

app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  #25mb

connection_url = sa.engine.URL.create(
    os.getenv('DB_TYPE'),
    username=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    query={
        "driver": os.getenv('DB_DRIVER'),
        "autocommit": os.getenv('DB_AUTOCOMMIT'),
    },
)

engine = sa.create_engine(connection_url)

    
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
 

def uuid_to_unique_int():
    timestamp = str(int(time.time() * 1000))[-4:]  
    random_suffix = ''.join(random.choices('0123456789', k=4))
    unique_id = timestamp + random_suffix
    return int(unique_id)


def yes_no_text_covert_to_label_value(obj) :
    if obj["ans"]:
        list_of_options=(obj["ans"]) 
        list_of_options=ast.literal_eval(list_of_options)
        obj["ans"]=[]
        for option in list_of_options:
            obj["ans"].append({
                "label":option,
                "value":option,
            })
    return obj["ans"] 


def accordion_list_retun(data_questions_table):
    """This is hard coded code whenever an new accordion is added this must be filled with new value
    Return: will return list of accordion parents and its childer
    """
    accordion_obj={
            "Financial Capability":{
                "expand": "no",
                "label_text": "",
                "q_name": "Financial Capability",
                "response_type": "accordion",
                "section_order": 3,
                "children": list()
            },
            "Administrative Capability":{
                "expand": "no",
                "label_text": "",
                "q_name": "Administrative Capability",
                "response_type": "accordion",
                "section_order": 4,
                "children": list()
            },
            "Leadership Capability":{
                "expand": "no",
                "label_text": "",
                "q_name": "Leadership Capability",
                "response_type": "accordion",
                "section_order": 5,
                "children": list()
            }
            }
    
    for obj in data_questions_table:
        try:
            a=accordion_obj[obj["section"]]
            yes_no_text_covert_to_label_value(obj)
            a["children"].append(obj)
        except Exception as error:
            print(error) 
    return [item for item in accordion_obj.values()]

                      

def get_column_names(connection, table_name: str, schema: str):
    """Retrieve column names for a given table."""
    query = text('''
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = :table_name
        AND TABLE_SCHEMA = :schema;
    ''')
    
    try:
        result = connection.execute(query, {"table_name": table_name, "schema": schema})
        return [row[0] for row in result]
    except SQLAlchemyError as e:
        return str(e) 

    
def get_table_data(connection,query,columns):
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
    
def identify_input(username):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    phone_regex = r'^\+?\d{0,2}?\d{10}$' 
    if re.match(email_regex, username):
        return "Email"
    
    elif re.match(phone_regex, username):
        return "Phone Number"
    
    else:
        return "Invalid Input"+" "+username

def list_to_string(list_obj):
    """sumary_line
    Keyword arguments:
    argument -- EXPECTING LIST
    Return: LIST VALUES AS STRING SEP BY COMMA
    """
    
    if isinstance(list_obj,list):
        return ",".join(list_obj)
    return str(list_obj)

def child_checking_appendig_to_its_parent_as_list_obj(all_questions):
    questions_to_process = all_questions[:]
    questions_to_remove = []

    for quest in questions_to_process:
        dep_q_id = quest.get("dep_q_id")
        if dep_q_id:
            for question in all_questions:
                question_available = question.get("ques_id")
                if question_available == dep_q_id:
                    if "children" not in question:
                        question["children"] = []
                    question["children"].append(quest)
                    questions_to_remove.append(quest)  
                    break
    for quest in questions_to_remove:
        all_questions.remove(quest)
    return all_questions
def  token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        
        if not token:
            return jsonify({'message': ERROR_MESSAGE_FOR_WRONG_TOKEN,"statusCode": 401, "status": "error"}), 401

        try:
            data = jwt.decode(token, JWT_SECRECT_KEY, algorithms=["HS256"])
            user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': ERROR_MESSAGE_FOR_WRONG_TOKEN,"statusCode": 401,"status": "error"}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': ERROR_MESSAGE_FOR_WRONG_TOKEN,"statusCode": 401,"status": "error"}), 401
        
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


def key_required(key):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            pk = data.get(key, None)
            if not pk:
                return jsonify({
                    "message": f"Invalid or missing {key} in request.",
                    "error": ERROR_MESSAGE_INVALID_ID,
                    "statusCode": 500,
                    "status": "error"
                }), 500
            return f(pk, *args, **kwargs)
        return decorated_function
    return decorator

    
@app.errorhandler(413)
def request_entity_too_large(error):
           return jsonify({
                "message": "Request entity too large. Please upload a smaller file.",
				"error": str(error),
				"statusCode": 413,
				"status": "error"
            }), 413
        
# ALL API ROUTES STARTS HERE  ----------------------------------------
@app.route("/api")
@token_required
def home():
    return jsonify({"status": "ok"})

@app.route('/api/register', methods=['POST'])
@json_required
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user_mobile = data.get('user_mobile', None)
    user_email = data.get('user_email', None)

    if not username or not password or not user_mobile or not user_email:
        return jsonify({'message': 'Username, password, mobile number, and email are required!', 'statusCode': 400, 'status': 'error'}), 400

    try:
        with engine.connect() as connection:
            username_query = text("SELECT COUNT(*) FROM [asmkpi].[user_data] WHERE username = :username")
            username_exists = connection.execute(username_query, {"username": username}).scalar() > 0
            
            email_query = text("SELECT COUNT(*) FROM [asmkpi].[user_data] WHERE user_email = :user_email")
            email_exists = connection.execute(email_query, {"user_email": user_email}).scalar() > 0
            
            mobile_query = text("SELECT COUNT(*) FROM [asmkpi].[user_data] WHERE user_mobile = :user_mobile")
            mobile_exists = connection.execute(mobile_query, {"user_mobile": user_mobile}).scalar() > 0

            if username_exists:
                return jsonify({'message': 'Username is already taken!', 'statusCode': 400, 'status': 'error'}), 400
            
            if email_exists:
                return jsonify({'message': 'Email is already registered!', 'statusCode': 400, 'status': 'error'}), 400
            
            if mobile_exists:
                return jsonify({'message': 'Mobile number is already registered!', 'statusCode': 400, 'status': 'error'}), 400

            password_hash = generate_password_hash(password)
            insert_query = text("INSERT INTO [asmkpi].[user_data] (username, password, user_mobile, user_email) VALUES (:username, :password, :user_mobile, :user_email)")
            connection.execute(insert_query, {"username": username, "password": password_hash, "user_mobile": user_mobile, "user_email": user_email})

        return jsonify({'message': 'User registered successfully!', 'statusCode': 200, 'status': 'success'}), 201

    except SQLAlchemyError as e:
        return jsonify({'message': 'User registration failed!', 'error': str(e), 'statusCode': 500, 'status': 'error'}), 500


@app.route('/api/login', methods=['POST'])
@json_required
def login():
    data = request.get_json()
    username = data.get('username')
    password = str(data.get('password',None))
    msal = data.get('msal')
    
    result_type = identify_input(username)

    if not username or not password:
        return jsonify({'message': 'Username and password are required!', 'statusCode': 400, 'status': 'error'}), 400

    try:
        with engine.connect() as connection:
            user_table_data=None
            if result_type == "Email":
                user_table_query_string_obj=GetQueryStringReturn(table_name=USERS_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns='"username","user_mobile","user_email","password","is_active","user_id"',
                                             condition=f"user_email='{str(username)}'",
                                             )
 
                user_table_exec_string=user_table_query_string_obj.all_data_of_given_columns_with_condition()
                print(user_table_exec_string)
                user_table_data = get_table_data(connection,user_table_exec_string, ["username","user_mobile","user_email","password","is_active","user_id"])
            elif result_type == "Phone Number":
                user_table_query_string_obj=GetQueryStringReturn(table_name=USERS_TABLE_NAME,
                                schema=SCHEMA_NAME,
                                columns='"username","user_mobile","user_email","password","is_active","user_id"',
                                condition=f"user_mobile={int(username)}",
                                )
 
                user_table_exec_string=user_table_query_string_obj.all_data_of_given_columns_with_condition()
                user_table_data = get_table_data(connection,user_table_exec_string, ["username","user_mobile","user_email","password","is_active","user_id"])
                print(user_table_data)

            else:
                return jsonify({'message': 'Invalid username format!', 'statusCode': 400, 'status': 'error'}), 400
            if not user_table_data:
                return jsonify({'message': 'User not found!', 'statusCode': 404, 'status': 'error'}), 404
            if msal!=1:
                if not check_password_hash(user_table_data[0]['password'], password):
                    return jsonify({'message': 'Invalid username or password!', 'statusCode': 401, 'status': 'error'}), 401

            token = jwt.encode({'user_id': user_table_data[0]['user_id'], 'exp': datetime.now() + timedelta(days=30)}, JWT_SECRECT_KEY, algorithm='HS256')

            return jsonify({'token': token, 'statusCode': 200, 'status': 'Success',"message":"Logged in successfully"}), 200
    except SQLAlchemyError as e:
        return jsonify({'message': 'Login failed!', 'error': str(e), 'statusCode': 500, 'status': 'error'}), 500



@app.route("/api/get_questions_asm")
def get_questions_and_asm_list():
    try:
        with engine.connect() as connection:
            try:
                columns = get_column_names(connection, QUESTIONS_TABLE_NAME,SCHEMA_NAME)
            except Exception as e:
                print(f"Error: {e}")
                
            colum_values_question_table_as_string=list_to_string(columns)
            
            question_table_accordion_only=GetQueryStringReturn(table_name=QUESTIONS_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns=colum_values_question_table_as_string,
                                             condition="expand!='yes';")
            question_table_accordion_only_exec_string=question_table_accordion_only.all_data_of_given_columns_with_condition()
            data_questions_table_accordion_only = get_table_data(connection,question_table_accordion_only_exec_string, columns)
            list_of_accordions=accordion_list_retun(data_questions_table_accordion_only)
            
            question_table_except_accordion=GetQueryStringReturn(table_name=QUESTIONS_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns=colum_values_question_table_as_string,
                                             condition="expand='yes';")
            question_table_except_accordion_exec_string=question_table_except_accordion.all_data_of_given_columns_with_condition()
            list_of_non_accordions = get_table_data(connection,question_table_except_accordion_exec_string, columns)
            for obj in list_of_non_accordions:
                yes_no_text_covert_to_label_value(obj)
            sales_hierarchy_table=GetQueryStringReturn(table_name=SALES_HIERARCHY_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns='"asm_name" AS label,"asm_emp_id"  AS value',
                                             condition="")
            sales_hierarchy_table_exec_string=sales_hierarchy_table.unique_values_of_given_column()
            
            data_asm_list = get_table_data(connection, sales_hierarchy_table_exec_string,["label","value"])
            
            all_questions=[]
            all_questions.extend(list_of_accordions)
            all_questions.extend(list_of_non_accordions)
            if not all_questions:
                 return jsonify({'message': 'data not found', 'error': 'data not found', 'statusCode': 400, 'status': 'error'}), 400

            """sorting by sectio_ order key for the final result"""
            all_questions=sorted(all_questions,key=lambda x:int(x["section_order"]))
            all_questions=child_checking_appendig_to_its_parent_as_list_obj(all_questions)
            
            all_data_questions_table={
                "questions":all_questions,
                "asm_list":{
                    "q_id":1,
                    "ans":data_asm_list
                    },
            }
            return jsonify(
				{
                "message": SUCCESS_MESSAGE_FETCHED_DATA,
                "result":all_data_questions_table,
                "statusCode": 200,
                "status": "success"
            }
			),200
    except Exception as e:
        return jsonify({
                "message": ERROR_MESSAGE_FETCHING_DATA,
				"error": str(e),
				"statusCode": 500,
				"status": "error"
            }), 500
        
   
@app.route("/api/get_distributor_sde",methods=["POST"])
@json_required
@key_required("asm_code")
def get_distributor_and_sde_for_the_asm(pk):
    try:
        with engine.connect() as connection:
            sales_hierarchy_table=GetQueryStringReturn(table_name=SALES_HIERARCHY_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns='"rs_code" AS value,"rs_name" AS label',
                                             condition=f"asm_emp_id='{str(pk)}'")
            sales_hierarchy_table_exec_string=sales_hierarchy_table.unique_values_of_given_columns_with_condition()
            print(sales_hierarchy_table_exec_string)
            data_distributors_list = get_table_data(connection, sales_hierarchy_table_exec_string,["value","label"])
            sales_hierarchy_table=GetQueryStringReturn(table_name=SALES_HIERARCHY_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns='"sde_emp_id" AS value,"sde_name" AS label',
                                             condition=f"asm_emp_id='{str(pk)}'")
            sales_hierarchy_table_exec_string=sales_hierarchy_table.unique_values_of_given_columns_with_condition()
            data_sde_list = get_table_data(connection, sales_hierarchy_table_exec_string,["value","label"])
              
            results_of_asm_list=[
                    {
                    "q_id":2,
                    "ans":data_distributors_list
                    },
                   {
                    "q_id":42,
                    "ans":data_sde_list
                    },
                ]
       
            return jsonify({
                "message": SUCCESS_MESSAGE_FETCHED_DATA,
                "result":results_of_asm_list,
                "statusCode": 200,
                "status": "success"
                }),200
        
    except Exception as e:
        return jsonify({
                "message": ERROR_MESSAGE_FETCHING_DATA,
				"error": str(e),
				"statusCode": 500,
				"status": "error"
            }), 500


@app.route("/api/get_salesman",methods=["POST"])
@json_required
@key_required("rs_code")
def get_salesman_and_all_questions_for_the_distributor(pk):
    try:
        with engine.connect() as connection:
            sales_hierarchy_table=GetQueryStringReturn(table_name=SALES_HIERARCHY_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns='"sm_name" as label,"sm_number" as value',
                                             condition=f"rs_code='{str(pk)}'")
            sales_hierarchy_table_exec_string=sales_hierarchy_table.unique_values_of_given_columns_with_condition()
            data_salesman_list = get_table_data(connection, sales_hierarchy_table_exec_string,
                                                ["label","value"])
            digital_table=GetQueryStringReturn(table_name=DIGITAL_TABLE,
                                             schema=SCHEMA_NAME,
                                             columns='"metrics","value"',
                                             condition=f"rscode='{str(pk)}'")
            sales_hierarchy_table_exec_string=digital_table.all_data_of_given_columns_with_condition()
            rs_digital_table_datae = get_table_data(connection, sales_hierarchy_table_exec_string,["metrics","value"])
            distributor_stock_table=GetQueryStringReturn(table_name=DISTRIBUTOR_STOCK_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns='"brand" AS label',
                                             condition=f"rscode='{str(pk)}'")
            distributor_stock_table_exec_string=distributor_stock_table.unique_values_of_given_columns_with_condition()
            data_stock_list = get_table_data(connection, distributor_stock_table_exec_string,["label"])
            if not data_stock_list:
                data_stock_list=[]
            all_values_digital_table_for_the_rs = []
            
            """ HARD CODE"""
            if rs_digital_table_datae:
                for rs_digital_table_data in rs_digital_table_datae:
                    key = rs_digital_table_data.get("metrics") 
                    if key is not None:
                        temp_dict={}
                        if key=="% Primary":
                            temp_dict["q_id"]=46
                            temp_dict["ans"]=rs_digital_table_data["value"]
                        elif key=="% Xdm":
                            temp_dict["q_id"]=5
                            temp_dict["ans"]=rs_digital_table_data["value"]
                        elif key=="Nach":
                            temp_dict["q_id"]=6
                            temp_dict["ans"]=rs_digital_table_data["value"]
                        elif key=="Current_stock":
                            temp_dict["q_id"]=3
                            temp_dict["ans"]=rs_digital_table_data["value"]
                    all_values_digital_table_for_the_rs.append(temp_dict)

            print(all_values_digital_table_for_the_rs)
            result= {
                        "salesman_list":{
                        "ans":data_salesman_list,
                        "q_id": 32
                    },
                    "statics":all_values_digital_table_for_the_rs,
                    "stock_list":data_stock_list,
            }
           
    

            return jsonify({
                "message": SUCCESS_MESSAGE_FETCHED_DATA,
                "result":result,
                "statusCode": 200,
                "status": "success"
                }),200
            
    except Exception as e:
        return jsonify({
                "message": ERROR_MESSAGE_FETCHING_DATA,
				"error": str(e),
				"statusCode": 500,
				"status": "error"
            }), 500
        
        
@app.route("/api/get_outlet",methods=["POST"])
@json_required
@key_required("sm_number")
def get_outlet(pk):
    try:
        with engine.connect() as connection:
            sales_hierarchy_table=GetQueryStringReturn(table_name=SALES_HIERARCHY_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns='"outlet_name" as label,"outlet_code" as value',
                                             condition=f"sm_number='{str(pk)}'")
            sales_hierarchy_table_exec_string=sales_hierarchy_table.unique_values_of_given_columns_with_condition()
            customer_list = get_table_data(connection, sales_hierarchy_table_exec_string,
                                                ["label","value"])
            sales_hierarchy_table=GetQueryStringReturn(table_name=SALES_HIERARCHY_TABLE_NAME,
                                             schema=SCHEMA_NAME,
                                             columns='"route_name" as label,"route_name" as value',
                                             condition=f"sm_number='{str(pk)}'")
            sales_hierarchy_table_exec_string=sales_hierarchy_table.unique_values_of_given_columns_with_condition()
            beat_list = get_table_data(connection, sales_hierarchy_table_exec_string,
                                               ["label","value"])
            result= [
                    {
                        "ans":beat_list,
                        "q_id": 36
                    },
                    {
                        "ans":customer_list,
                        "q_id": 37
                    },
                    ]      

            return jsonify({
                "message": SUCCESS_MESSAGE_FETCHED_DATA,
                "result":result,
                "statusCode": 200,
                "status": "success"
                }),200
            
    except Exception as e:
        return jsonify({
                "message": ERROR_MESSAGE_FETCHING_DATA,
				"error": str(e),
				"statusCode": 500,
				"status": "error"
            }), 500


@app.route("/api/all_datae", methods=["POST"])
@json_required
def all_datae():
    data = request.get_json()
    survey_id = data.get('survey_id',None)
    userid = data.get('userid',None)
    rs_code = data.get('rs_code',None)
    asm_code = data.get('asm_code',None)
    sde_code = data.get('sde_code',None)
    sm_number = data.get('sm_number',None)
    survey_submitted_id = uuid_to_unique_int()
    questions_list = data.get('answers', [])
    images_list = data.get('images', [])

    survey_submittedon = datetime.now(kolkata_tz).strftime('%Y-%m-%d %H:%M:%S')
    createdon = survey_submittedon  
    updatedon = survey_submittedon

    response_status = None
    rejection_comments = None
    authorized_by = None
    authorized_date = None
    folder_name =ADMINISTRATIVE_CAPABILITY_IMAGES_FOLDER_IN_AZURE
    try:
        with engine.connect() as connection:
            if len(questions_list)>0:
                for question in questions_list:
                    q_id = question["q_id"]
                    q_name =str(question["q_name"])
                    ans = question["ans"]

                    insert_query_query = text("""
                            INSERT INTO asmkpi.response(survey_id, survey_submitted_id, userid, survey_submittedon, updatedon, q_id, q_name, ans)
                            VALUES (:survey_id,:survey_submitted_id,:userid, :survey_submittedon, :updatedon, :q_id, :q_name, :ans)
                    """)

                    connection.execute(insert_query_query, {
                        "survey_id": survey_id,
                        "survey_submitted_id": survey_submitted_id,
                        "userid": userid,
                        "survey_submittedon": survey_submittedon,
                        "updatedon": updatedon,
                        "q_id": q_id,
                        "q_name": q_name,
                        "ans": str(ans),
                    })

            if len(images_list)>0:
                for image in images_list:
                    q_id = image["q_id"]
                    ans = image["ans"]
                    blob_storage_filename = f"{folder_name}_{userid}_{uuid.uuid4().hex}.jpg"

                    query_str = text("""
                            INSERT INTO asmkpi.response_image(survey_id,
                            survey_submitted_id, userid, survey_submittedon,
                            updatedon,createdon, q_id,blob_storage_filename,folder_name)
                            VALUES (:survey_id,:survey_submitted_id,:userid, :survey_submittedon, :updatedon,:createdon,
                            :q_id, :blob_storage_filename,:folder_name)
                    """)

                    query_data= {
                        "survey_id": survey_id,
                        "survey_submitted_id": survey_submitted_id,
                        "userid": userid,
                        "survey_submittedon": survey_submittedon,
                        "updatedon": updatedon,
                        "createdon": createdon,
                        "q_id": q_id,
                        "blob_storage_filename":blob_storage_filename,
                        "folder_name":folder_name
                        
                    }
                    try:
                        upload_images(ans,blob_storage_filename,folder_name,query_str,query_data)
                    except Exception as e:
                        return jsonify({"status": "error", "message": str(e)}), 500
            insert_query = text("""
                INSERT INTO asmkpi.response_summary (survey_id, survey_submitted_id, userid, rs_code, asm_code, sde_code, sm_number, survey_submittedon, createdon, updatedon, response_status, rejection_comments, authorized_by, authorized_date) 
                VALUES (:survey_id, :survey_submitted_id, :userid, :rs_code, :asm_code, :sde_code, :sm_number, :survey_submittedon, :createdon, :updatedon, :response_status, :rejection_comments, :authorized_by, :authorized_date)
            """)
            tuple_key_list_of_response_summary = {
                "survey_id": survey_id,
                "survey_submitted_id": survey_submitted_id,
                "userid": userid,
                "rs_code": rs_code,
                "asm_code": asm_code,
                "sde_code": sde_code,
                "sm_number": sm_number,
                "survey_submittedon": survey_submittedon,
                "createdon": createdon,
                "updatedon": updatedon,
                "response_status": response_status,
                "rejection_comments": rejection_comments,
                "authorized_by": authorized_by,
                "authorized_date": authorized_date
            }
            connection.execute(insert_query, tuple_key_list_of_response_summary)
            return jsonify({
                "message": "Data saved successfully",
                "result":[],
                "statusCode": 200,
                "status": "success"
                }),200
        
    except Exception as e:
        return jsonify({
            "message": ERROR_MESSAGE_FETCHING_DATA,
            "error": str(e),
            "statusCode": 500,
            "status": "error"
        }), 500

def upload_images(encoded_image, blob_storage_filename,folder_name, query_str, query_data):
    if not encoded_image:
        return
    if upload_to_azure_blob(encoded_image, blob_storage_filename, folder_name):
        add_image_to_database(query_str, query_data)
        
        
def upload_to_azure_blob(blob_data, blob_storage_filename, folder_name):
    try:
        container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER_NAME)
        blob_client = container_client.get_blob_client(f"{folder_name}/{blob_storage_filename}")

        file_data = base64.b64decode(blob_data)

        blob_client.upload_blob(file_data, content_settings=ContentSettings(content_type='image/jpeg'))
        return True
    except Exception as e:
        print(f"Error uploading to Azure Blob Storage: {str(e)}")
        raise 
    
    
def add_image_to_database(querystr,querydata):
    try:
        conn = engine.connect()
        conn.execute(querystr,querydata)
        conn.close()
    except Exception as e:
        print(f"Error adding image to the database: {str(e)}")
        raise
    

if __name__ == "__main__":
    app.run(debug=True)

