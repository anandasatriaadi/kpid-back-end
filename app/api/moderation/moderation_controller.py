from flask import Blueprint
from app.api.moderation.moderation_service import upload_form

moderation_bp = Blueprint('moderation', __name__)

moderation_bp.route('/moderation-form', methods=['POST'])(upload_form)
