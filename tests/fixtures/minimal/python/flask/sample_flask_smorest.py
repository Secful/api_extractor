"""Sample flask-smorest API for testing."""

from flask import Flask
from flask.views import MethodView
from flask_smorest import Api, Blueprint
from marshmallow import Schema, fields


class PetQuerySchema(Schema):
    """Query parameters for listing pets."""

    name = fields.Str()
    limit = fields.Int()
    status = fields.Str()


class PetSchema(Schema):
    """Pet resource schema."""

    id = fields.Int()
    name = fields.Str()
    status = fields.Str()
    category = fields.Str()


class ErrorSchema(Schema):
    """Error response schema."""

    message = fields.Str()
    code = fields.Int()


app = Flask(__name__)
app.config["API_TITLE"] = "Pet Store API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.2"

api = Api(app)
blp = Blueprint("pets", "pets", url_prefix="/api/v1/pets", description="Pet operations")


@blp.route("/")
class Pets(MethodView):
    """Pet collection resource."""

    @blp.arguments(PetQuerySchema, location="query")
    @blp.response(200, PetSchema(many=True))
    def get(self, args):
        """List all pets with optional filtering."""
        pass

    @blp.arguments(PetSchema)
    @blp.response(201, PetSchema)
    def post(self, data):
        """Create a new pet."""
        pass


@blp.route("/<int:pet_id>")
class PetById(MethodView):
    """Individual pet resource."""

    @blp.response(200, PetSchema)
    def get(self, pet_id):
        """Get a pet by ID."""
        pass

    @blp.arguments(PetSchema)
    @blp.response(200, PetSchema)
    def put(self, data, pet_id):
        """Update a pet by ID."""
        pass

    @blp.response(204)
    def delete(self, pet_id):
        """Delete a pet by ID."""
        pass


@blp.route("/<int:pet_id>/status")
class PetStatus(MethodView):
    """Pet status resource."""

    @blp.response(200, PetSchema)
    def get(self, pet_id):
        """Get pet status."""
        pass


api.register_blueprint(blp)


if __name__ == "__main__":
    app.run(debug=True)
