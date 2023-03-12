from http import HTTPStatus

from flask import Blueprint

from app.api.moderation import moderation_bp
from app.api.user import user_bp
from app.dto import BaseResponse

api_bp = Blueprint('api', __name__)
api_bp.register_blueprint(moderation_bp)
api_bp.register_blueprint(user_bp)


@api_bp.route("/ping", methods=["GET"])
def ping():
    response = BaseResponse("ping", HTTPStatus.OK)
    return response.__dict__, response.status
