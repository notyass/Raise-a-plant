"""Point d'entrée du backend : python main.py"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)
