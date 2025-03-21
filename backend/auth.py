import uuid
import secrets
from datetime import timedelta
from flask import Blueprint, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models.user import User

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

def init_auth(app):
    # Generate secure random key
    app.config['SECRET_KEY'] = secrets.token_hex(16)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = None  # Allow cross-site cookies for development
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)
    
    # Add unauthorized handler to return proper JSON response
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'success': False, 'message': 'Unauthorized access. Please login again.'}), 401
    
    app.register_blueprint(auth_bp)
    
    # Create admin user if not exists
    admin = User.get_by_username('admin')
    if not admin:
        password_hash = bcrypt.generate_password_hash('admin').decode('utf-8')
        User.save_user(str(uuid.uuid4()), 'admin', password_hash)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')  # Fix: Extract password from request data
    
    print(f"Login attempt for user: {username}")
    
    user = User.get_by_username(username)
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        print(f"Login failed for user: {username}")
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    
    # Use remember=True to keep the user logged in
    login_user(user, remember=True)
    print(f"Login successful for user: {username}")
    print(f"Session: {session}")
    return jsonify({'success': True, 'username': user.username})

# Add a debug route to inspect session
@auth_bp.route('/api/debug_session')
def debug_session():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user_id': current_user.id,
            'username': current_user.username,
            'session': {k: str(v) for k, v in session.items()},
            'remember': hasattr(current_user, 'remember') and current_user.remember
        })
    return jsonify({
        'authenticated': False,
        'session': {k: str(v) for k, v in session.items()}
    })

@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if User.get_by_username(username):
        return jsonify({'success': False, 'message': 'Username already exists'}), 400
    
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    User.save_user(str(uuid.uuid4()), username, password_hash)
    
    return jsonify({'success': True, 'message': 'User registered successfully'})

@auth_bp.route('/api/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'success': True})

@auth_bp.route('/api/user')
@login_required
def get_user():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username
    })

# Add a proper login check endpoint that doesn't require login_required
@auth_bp.route('/api/check_auth', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        print(f"User authenticated: {current_user.username}")
        return jsonify({
            'authenticated': True,
            'username': current_user.username
        })
    else:
        print("User not authenticated")
        return jsonify({
            'authenticated': False
        }), 200  # Return 200 even when not authenticated
