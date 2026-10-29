
from flask import Flask, jsonify, request, Response, g
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from time import perf_counter

app = Flask(__name__)

# Create a dedicated registry for this application
registry = CollectorRegistry()

# Count HTTP requests by endpoint, method, and response status
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

# Measure HTTP request duration in seconds
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
)


@app.before_request
def start_timer():
    # Don't include Prometheus scrapes in application request metrics
    if request.path != "/metrics":
        g.start_time = perf_counter()


@app.after_request
def record_metrics(response):
    # Record application requests, excluding /metrics
    if request.path != "/metrics":
        duration = perf_counter() - g.start_time
        endpoint = request.endpoint or "not_found"

        REQUEST_COUNT.labels(
            request.method, endpoint, str(response.status_code)
        ).inc()

        REQUEST_LATENCY.labels(
            request.method, endpoint
        ).observe(duration)

    return response


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(registry),
        mimetype=CONTENT_TYPE_LATEST,
    )


@app.get("/version")
def get_version():
    return jsonify({
        "message": (
            "Hi everyone, this is the version endpoint. "
            "Use it to check the version. Also with this we're "
            "going to test the canary deployment"
            "This is the start of testing the canary deployment" 
        ),
        "version": "v10",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)

