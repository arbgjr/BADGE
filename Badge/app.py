from flask import Flask, request, jsonify
from flask_restx import Resource, Api

application = Flask(__name__)
api = Api(application, doc='/doc/')


@api.route("/hello")
class Hello(Resource):
    @api.doc(
        params={},
        responses={
            200: 'Success',
            400: 'Validation Error'
        }
    )
    def get(self):
        req_body = request.get_json()
        user = req_body.get('owner_name')
        return jsonify({"message": f"Hello Azure Function {user}"})
        })

@api.route("/ping")
class Ping(Resource):
    def get(self):
        return jsonify({
            "message": "back"
        })

        
api.add_resource(Hello, "/hello")
api.add_resource(Ping, "/ping")  
