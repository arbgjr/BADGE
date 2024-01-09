from flask import Flask, request, jsonify
from flask_restx import Resource, Api

application = Flask(__name__)
api = Api(application, doc='/doc/')


@api.route("/hello")
class Hello(Resource):
    @api.doc(
        params={'user' : 'an user identifier'},
        responses={
            200: 'Success',
            400: 'Validation Error'
        }
    )
    def get(self, user: str):
        user = request.args.get('user')
        return jsonify({
            f"Hello Azure Function {user}"
        })

api.add_resource(Hello, "/hello") 
