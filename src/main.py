from flask import Flask, jsonify, request, send_file

import debugpy
import os
import json
from io import BytesIO
from flasgger import Swagger
from controllers import register_blueprints


app = Flask(__name__)

# service name from docker-compose



@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


    
# The translate and cache endpoints were moved into the `controllers` package to keep
# this file small and make it easier to add more controllers in the future.
# Initialize Swagger and register controller blueprints here.

# Initialize Flasgger Swagger UI (exposed at /apidocs)
Swagger(app)

# Register all controller blueprints
register_blueprints(app)


if __name__ == "__main__":
    debug = os.getenv("DEBUG", False)
    print(f"Starting app with debug={debug}")

    if debug:
        debugpy.listen(("0.0.0.0", 5678))
        print("Waiting for debugger to attach...")
        debugpy.wait_for_client()

    app.run(host="0.0.0.0", debug=debug, use_reloader= not debug)