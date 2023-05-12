from flask import Flask, jsonify, request
# from flask_cors import CORS
from model import NextflowRunToken, NextflowUser, NextflowRun
from pymongo import MongoClient

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)
client = MongoClient(host='mongodb://localhost', port=27017, username="root", password="example")
db = client.flask_db

tokens = db.database


# enable CORS
#CORS(app, resources={r'/*': {'origins': '*'}})



# sanity check route
@app.route('/ping', methods=['GET', 'POST'])
def ping_pong():
    token = NextflowRunToken(**request.args)
    tokens.insert_one(token.to_bson())

    all_tokens = tokens.find()
    for tkn in all_tokens:
        print(tkn)
    return jsonify("hi")

@app.route('/create', methods=['GET'])
def create_test():
    testuser = NextflowUser(**{"identifier_token": "testtoken123", "run_tokens": [{"run_identifier_token": "run1"}, {"run_identifier_token": "run2"}]})
    tokens.insert_one(testuser.to_bson())
    testrun1 = NextflowRun(**{"run_token": {"run_identifier_token": "run1"}, "name": "firsttestrun"})
    tokens.insert_one(testrun1.to_bson())
    return jsonify("yep")

@app.route('/test', methods=['GET', 'POST'])
def testtokens():
    user_token = request.args["usertoken"]
    users = tokens.find({"identifier_token": user_token})
    for user in users:
        print(user)
    return jsonify("users")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)





