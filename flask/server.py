from flask import Flask, jsonify, request
# from flask_cors import CORS
from model import Token

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)

# enable CORS
#CORS(app, resources={r'/*': {'origins': '*'}})


# sanity check route
@app.route('/ping', methods=['GET', 'POST'])
def ping_pong():
    token = Token(**request.args)
    return jsonify(token.json())


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8000, debug=True)

