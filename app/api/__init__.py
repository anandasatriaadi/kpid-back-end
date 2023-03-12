from flask import Blueprint

from app.api import moderation, user

api_bp = Blueprint('api', __name__, url_prefix='/api')
