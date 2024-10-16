from datetime import timedelta
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import select
from models import User, UserTypes, Base
from models import Brief
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

CORS(app, resources={r"/*": {"origins": "*"}})

app.config["JWT_SECRET_KEY"] = "brief_app"  # Change this to a more secure key
jwt = JWTManager(app)

# Initialize DB
with app.app_context():
    Base.metadata.create_all(db.engine)


@app.route("/create_superadmin", methods=["POST"])
def create_superadmin():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    user_firstname = data.get("user_firstname")
    user_lastname = data.get("user_lastname")
    user_email = data.get("user_email")

    existing_user = db.session.execute(
        select(User).filter_by(user_role="super_admin")
    ).scalar_one_or_none()
    if existing_user:
        return jsonify({"msg": "SuperAdmin already exists"}), 400
    hashed_password = generate_password_hash(password)

    new_user = User(
        username=username,
        password=hashed_password,
        user_firstname=user_firstname,
        user_lastname=user_lastname,
        user_email=user_email,
        user_role="super_admin",
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "SuperAdmin created successfully"}), 201


@app.route("/register", methods=["POST"])
@jwt_required()
def register():
    current_user = get_jwt_identity()
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    user_role = data.get("role")

    print(current_user)
    
    current_user_id = current_user['id']

    # Role validation for SuperAdmin and Admin
    if current_user["role"] == "super_admin":
        if user_role != "admin":
            return jsonify({"msg": "SuperAdmin can only create Admin users"}), 403
    elif current_user["role"] == "admin":
        if user_role not in ["creator", "receiver"]:
            return (
                jsonify({"msg": "Admins can only create Creator or Receiver users"}),
                403,
            )
    else:
        return jsonify({"msg": "Permission denied"}), 403

    # Check if the username or email already exists
    existing_user = db.session.execute(
        select(User).filter((User.username == username) | (User.user_email == email))
    ).scalar_one_or_none()

    if existing_user:
        # Check if it's the username or email that's already taken
        if existing_user.username == username:
            return jsonify({"msg": "Username already exists"}), 400
        elif existing_user.user_email == email:
            return jsonify({"msg": "Email already exists"}), 400

    # Hash the password and create the new user
    hashed_password = generate_password_hash(password)
    new_user = User(
        username=username,
        password=hashed_password,
        user_firstname=data.get("user_firstname"),
        user_lastname=data.get("user_lastname"),
        user_email=email,
        user_role=UserTypes[user_role],
        created_by=current_user_id,
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": f"{user_role.capitalize()} user created successfully"}), 201


# Login
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = db.session.execute(
        select(User).filter_by(username=username)
    ).scalar_one_or_none()

    if user and check_password_hash(user.password, password):
        access_token = create_access_token(
            identity={"username": user.username, "role": user.user_role.value, "id": user.id},
            expires_delta=timedelta(hours=1),
        )
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "Invalid username or password"}), 401


# Protected route example
@app.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

# BRIEFS


@app.route("/briefs", methods=["POST"])
@jwt_required()
def create_brief():
    current_user = get_jwt_identity()
    data = request.get_json()

    # Ensure all required fields are present
    required_fields = [
        "category",
        "priority",
        "brand",
        "study_type",
        "market_objective",
        "research_objective",
        "deadline",
        "key_information_area",
        "city",
        "stimulus_dispatch_date",
        "additional_information",
    ]

    for field in required_fields:
        if field not in data or data[field] is None:
            return jsonify({"msg": f"{field.capitalize()} is required."}), 400

    # Parse and convert fields as needed
    try:
        brief = Brief(
            category=data.get("category"),
            priority=data.get("priority"),
            brand=data.get("brand"),
            study_type=data.get("study_type"),
            comments=data.get("comments"),
            previous_research=data.get("previous_research"),
            market_objective=data.get("market_objective"),
            research_objective=data.get("research_objective"),
            research_tg=data.get("research_tg"),
            research_design=data.get("research_design"),
            key_information_area=data.get("key_information_area"),
            deadline=datetime.strptime(
                data.get("deadline"), "%Y-%m-%d"
            ).date(),  # Ensure this is parsed correctly
            additional_information=data.get("additional_information"),
            city=data.get("city"),
            stimulus_dispatch_date=(
                datetime.strptime(data.get("stimulus_dispatch_date"), "%Y-%m-%d").date()
                if data.get("stimulus_dispatch_date")
                else None
            ),
            status=data.get("status", "waiting_for_approval"),
            attachments=data.get("attachments"),
            brief_creator_id=current_user[
                "id"
            ],  # Assuming you are storing user ID in JWT
        )

        db.session.add(brief)
        db.session.commit()

        return jsonify({"msg": "Brief created successfully."}), 201

    except Exception as e:
        db.session.rollback()  # Rollback if any error occurs
        return jsonify({"msg": str(e)}), 400


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login2")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/create_brief")
def create_brief_page():
    return render_template("create_brief.html")


@app.route("/briefs_page")
def briefs_page():
    return render_template("briefs.html")


@app.route("/briefs", methods=["GET"])
@jwt_required()  # Ensure that only authenticated users can access this route
def get_briefs():
    current_user = get_jwt_identity()
    
    # Fetch briefs based on user role
    if current_user["role"] == "creator":
        # If the current user is a creator, show only briefs they created
        briefs = db.session.query(Brief).filter_by(brief_creator_id=current_user["id"]).all()
    elif current_user["role"] == "receiver":
        # If the current user is a receiver, show all briefs that are waiting for approval
        briefs = db.session.query(Brief).filter_by(status="waiting_for_approval").all()
    else:
        # For admin or super_admin roles, show all briefs
        briefs = db.session.query(Brief).all()

    # Convert the briefs into a dictionary format to return as JSON
    brief_list = [
        {
            "id": brief.id,
            "category": brief.category,
            "priority": brief.priority,
            "brand": brief.brand,
            "study_type": brief.study_type,
            "comments": brief.comments,
            "previous_research": brief.previous_research,
            "market_objective": brief.market_objective,
            "research_objective": brief.research_objective,
            "research_tg": brief.research_tg,
            "research_design": brief.research_design,
            "key_information_area": brief.key_information_area,
            "deadline": brief.deadline.strftime("%Y-%m-%d"),
            "additional_information": brief.additional_information,
            "city": brief.city,
            "stimulus_dispatch_date": brief.stimulus_dispatch_date.strftime("%Y-%m-%d") if brief.stimulus_dispatch_date else None,
            "status": brief.status,
            "attachments": brief.attachments,
            "approved": brief.approved,
            "approved_by": brief.approved_by,
            "rejection_reason": brief.rejection_reason,
            "rejection_date": brief.rejection_date,
            "budget": brief.budget,
            "total_cost": brief.total_cost,
            "brief_creator_id": brief.brief_creator_id
        }
        for brief in briefs
    ]

    return jsonify(brief_list), 200


if __name__ == "__main__":
    app.run(debug=True)
