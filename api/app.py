from flask import Flask, request, jsonify
import redis
import json, os

app = Flask(__name__)
r = redis.Redis(os.environ.get("REDIS_HOST", "localhost"), port = 6379, decode_responses = True)

@app.get('/tasks')
def get_tasks():
    tasks = r.lrange("tasks", 0, -1)
    return jsonify([json.loads(t) for t in tasks])
@app.post('/tasks')
def post_tasks():
    task = request.json["title"]
    r.rpush("tasks", json.dumps({"title" : task, "status" : "queued"}))
    return jsonify({ "status" : "queued", "task" : task}), 201

if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug=False)
