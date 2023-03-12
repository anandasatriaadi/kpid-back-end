from flask import Blueprint

from app.api.moderation.moderation_service import upload_form

moderation = Blueprint('moderation_controller', __name__, url_prefix='/moderation')
