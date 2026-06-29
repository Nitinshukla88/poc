import redis
import time, json, os
r = redis.Redis(os.environ.get("REDIS_HOST", "localhost"), port = 6379, decode_responses = True)
while True:
    item = r.blpop("tasks", timeout = 0)
    task = json.loads(item[1])
    print(f"Processing task: {task['title']}")
    time.sleep(2)
    r.rpush("completed", json.dumps({ "title" : task["title"], "status" : "done" }))
    print(f"Task done: {task['title']}")

