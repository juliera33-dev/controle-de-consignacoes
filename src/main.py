import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS

# 1. Carregar variáveis de ambiente PRIMEIRO
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# 2. Configurar caminhos do sistema
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 3. Agora importar os componentes do projeto
from src.models.user import db
from src.routes.user import user_bp
from src.routes.estoque import estoque_bp

# 4. Inicializar aplicação Flask
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key')

# 5. Health Check - ESSENCIAL PARA DEPLOY
@app.route('/api/health')
def health_check():
    return {'status': 'ok', 'message': 'API funcionando'}, 200

# 6. Configurar CORS
CORS(app)

# 7. Registrar Blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(estoque_bp, url_prefix='/api/estoque')

# 8. Configurar Banco de Dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 9. Criar tabelas se não existirem
with app.app_context():
    db.create_all()

# 10. Rota para servir o frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# 11. Inicialização do Servidor
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Mude debug=False para produção!
    app.run(debug=True, host='0.0.0.0', port=port)

