from datetime import timedelta
from flask import Flask, request, jsonify
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

    if current_user["role"] not in ["super_admin", "admin"]:
        return jsonify({"msg": "Permission denied"}), 403

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    user_role = data.get("role")

    if user_role not in ["creator", "reciever"]:
        return jsonify({"msg": "Invalid role specified."}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(
        username=username,
        password=hashed_password,
        user_firstname=data.get("user_firstname"),
        user_lastname=data.get("user_lastname"),
        user_email=email,
        user_role=UserTypes[user_role],
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
            identity={"username": user.username, "role": user.user_role.value},
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


if __name__ == "__main__":
    app.run(debug=True)
