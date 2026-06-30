from flask import Flask, request, jsonify
import redis
import json, os

app = Flask(__name__)
r = redis.Redis(os.environ.get("REDIS_HOST", "localhost"), port = 6379, decode_responses = True)

@app.get('/tasks')
def get_tasks():
    pending_tasks = r.lrange("tasks", 0, -1)
    completed_tasks = r.lrange("completed", 0, -1)
    return jsonify({"pending" : [json.loads(t) for t in pending_tasks], "completed" : [json.loads(t) for t in completed_tasks]})

@app.post('/tasks')
def post_tasks():
    print("Received POST request!", flush=True)
    task = request.json["title"]
    print(f"Task title: {task}", flush=True)
    r.rpush("tasks", json.dumps({"title" : task, "status" : "queued"}))
    print("Pushed to Redis", flush=True)
    return jsonify({ "status" : "queued", "task" : task}), 201

if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug=False)
