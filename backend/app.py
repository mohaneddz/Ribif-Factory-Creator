from flask import Flask
from flask_cors import CORS

from routes.common import bp_common
from routes.module1 import bp_module1
from routes.module2 import bp_module2
from routes.module3 import bp_module3
from routes.module4 import bp_module4
from routes.module_5 import bp_module5
from routes.module6 import bp_module6
from routes.module7 import bp_module7
from routes.module9 import bp_module9
from routes.email_service import bp_email_service
from routes.validation import bp_validation

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.register_blueprint(bp_common)
app.register_blueprint(bp_module1)
app.register_blueprint(bp_module2)
app.register_blueprint(bp_module3)
app.register_blueprint(bp_module4)
app.register_blueprint(bp_module5)
app.register_blueprint(bp_module6)
app.register_blueprint(bp_module7)
app.register_blueprint(bp_module9)
app.register_blueprint(bp_email_service)
app.register_blueprint(bp_validation)

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
