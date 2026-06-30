import redis
import time, json, os
r = redis.Redis(os.environ.get("REDIS_HOST", "localhost"), port = 6379, decode_responses = True, socket_connect_timeout=10, socket_keepalive=True, socket_timeout=None)

while True:
    try:
        r.ping()
        print("Redis connected successfully")
        break
    except redis.exceptions.ConnectionError:
        print("Redis is not ready yet.... Retrying!")
        time.sleep(1)

while True:
    item = r.blpop("tasks", timeout=0)
    try:
        task = json.loads(item[1])
        print(f"Processing task: {task['title']}", flush=True)
        time.sleep(2)
        r.rpush("completed", json.dumps({"title": task["title"], "status": "done"}))
        print(f"Task done: {task['title']}", flush=True)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Skipping malformed task: {item[1]} — error: {e}", flush=True)

