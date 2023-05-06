from http import HTTPStatus

from flask import Blueprint

from app.api.moderation import moderation_bp
from app.api.station import station_bp
from app.api.user import user_bp
from app.dto import BaseResponse

# Creating a new Blueprint instance
api_bp = Blueprint('api', __name__)

# Registering the moderation_bp and user_bp blueprints with the api_bp blueprint
api_bp.register_blueprint(moderation_bp)
api_bp.register_blueprint(user_bp)
api_bp.register_blueprint(station_bp)

@api_bp.route("/ping", methods=["GET"])
def ping():
    response = BaseResponse("ping", HTTPStatus.OK)
    return response.get_response()
