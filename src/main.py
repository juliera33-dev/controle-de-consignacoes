# src/main.py

# 1. CARREGAMENTO DE VARIÁVEIS DE AMBIENTE (DEVE VIR PRIMEIRO!)
from dotenv import load_dotenv
import os
import sys

# Carrega variáveis do .env antes de qualquer outra coisa
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 2. IMPORTS DEPOIS DAS VARIÁVEIS
from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.estoque import estoque_bp

# 3. CONFIGURAÇÃO DO APP
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key')  # Melhor prática

# Habilita CORS para todas as rotas
CORS(app)

# 4. REGISTRO DE BLUEPRINTS
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(estoque_bp, url_prefix='/api/estoque')

# 5. CONFIGURAÇÃO DO BANCO DE DADOS
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

# 6. ROTAS
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# 7. EXECUÇÃO
if __name__ == '__main__':
    # Use a porta de ambiente ou 5000 como fallback
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

