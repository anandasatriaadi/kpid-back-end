from app.api.moderation import moderation
from app.api.moderation.moderation_service import upload_form

moderation.route('/moderation-form', methods=['POST'])(upload_form)
