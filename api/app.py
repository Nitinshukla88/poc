from flask import Flask 

app = Flask(__name__)

@app.get('/tasks')
def get_tasks():
    return tasks

@app.post('/tasks')
def post_tasks():
    return 'tasks are posted'

if __name__ == '__main__':
    app.run(debug=False)
