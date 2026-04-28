"""Sample Flask application for testing."""

from flask import Flask, Blueprint, request

app = Flask(__name__)

# API Blueprint with prefix
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Admin Blueprint
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@app.route("/")
def index():
    """Root endpoint."""
    return {"message": "Hello World"}


@app.route("/users/<int:user_id>", methods=["GET", "POST"])
def get_user(user_id):
    """Get or update user by ID."""
    return {"id": user_id}


@app.get("/items")
def list_items():
    """List items."""
    skip = request.args.get("skip", 0)
    limit = request.args.get("limit", 10)
    return {"skip": skip, "limit": limit}


@app.post("/items")
def create_item():
    """Create new item."""
    data = request.json
    return data


@api_bp.route("/products")
def list_products():
    """List products."""
    return {"products": []}


@api_bp.route("/products/<product_id>", methods=["GET", "PUT", "DELETE"])
def product_detail(product_id):
    """Get, update, or delete product."""
    return {"id": product_id}


@api_bp.post("/orders")
def create_order():
    """Create new order."""
    data = request.json
    return data


@admin_bp.route("/dashboard")
def dashboard():
    """Admin dashboard."""
    return {"admin": True}


@admin_bp.route("/users/<string:username>")
def admin_user(username):
    """Admin user management."""
    return {"username": username}


# Register blueprints
app.register_blueprint(api_bp)
app.register_blueprint(admin_bp)
