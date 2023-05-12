from flask import Flask, jsonify, request
# from flask_cors import CORS
from model import NextflowRunToken, NextflowUser
from pymongo import MongoClient

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)
client = MongoClient(host='0.0.0.0', port=8005)
db = client.flask_db

tokens = db.nextflowruntokens

# enable CORS
#CORS(app, resources={r'/*': {'origins': '*'}})



# sanity check route
@app.route('/ping', methods=['GET', 'POST'])
def ping_pong():
    token = NextflowRunToken(**request.args)
    tokens.insert_one(token.to_bson())

    all_tokens = tokens.find()
    return jsonify(all_tokens)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
