from flask import request, jsonify
import jwt
from functools import wraps
from config import database, SECRET_KEY

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the request header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
        # return 401 if token is not passed
        if not token:
            return jsonify({'message' : 'Token is missing'}), 401

        try:
            # decoding the payload to fetch the stored details
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = database["users"].find_one({"email": data['email']})
        except Exception as e:
            print("[X] ERROR : " + e)
            return jsonify({
                'message' : 'Token is invalid'
            }), 401
        # returns the current logged in users contex to the routes
        return  f(current_user, *args, **kwargs)

    return decorated