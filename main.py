from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, world!"

# Do NOT include app.run() for production
# if __name__ == "__main__":
#     app.run(debug=True)
