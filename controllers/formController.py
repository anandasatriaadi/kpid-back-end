from flask import Blueprint
from services.formService import *

fc = Blueprint('form_controller', __name__)

fc.route('/moderation-form', methods=['POST'])(upload_form)