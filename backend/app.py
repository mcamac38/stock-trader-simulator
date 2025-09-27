from flask import Flask
app = Flask(__name__)

@app.get("/health")
def health():
    return {"status": "ok"}, 200

if __name__== "__main__":
    app.run()