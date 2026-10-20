import os
from flask import Flask
from flask_login import LoginManager
from models import db, User, Career, Subject
from routes import init_routes

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'clave_secreta_ipet1308_modular'
    
    # URL con soporte psycopg2
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:fernando04777zp@localhost:5432/gestion_archivos'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    db.init_app(app)
    
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    init_routes(app)

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Cargar Carrera y Materias completas de la captura si la base de datos está vacía
        if not Career.query.filter_by(name="Analista en Sistemas").first():
            career = Career(name="Analista en Sistemas")
            db.session.add(career)
            db.session.commit()

            # Lista tabla
            materias = [
                # 1.er Año
                (1, "PROGRAMACION LOGICA"),
                (1, "SISTEMAS DE PROCESAMIENTO DE DATOS I"),
                (1, "MATEMATICA I"),
                (1, "FILOSOFIA DE LA CIENCIA Y DE LA TECNICA"),
                (1, "INGLES TECNICO I"),
                (1, "TALLER DE INFORMATICA"),
                (1, "PROGRAMACION I"),
                (1, "SISTEMAS DE PROCESAMIENTO DE DATOS II"),
                (1, "TALLER DE COMUNICACION ORAL Y ESCRITA"),
                
                # 2.º Año
                (2, "PROGRAMACION II"),
                (2, "LENGUAJES GENERADORES DE INFORMES"),
                (2, "SISTEMAS DE PROCESAMIENTO DE DATOS III"),
                (2, "MATEMATICA II"),
                (2, "PROGRAMACION CIENTIFICA"),
                (2, "SISTEMAS DE INFORMACION CONTABLE"),
                (2, "INGLES TECNICO II"),
                (2, "PRACTICA PROFESIONAL"),
                (2, "TECNICAS DE PROGRAMACION"),
                (2, "ETICA Y DEONTOLOGIA PROFESIONAL"),

                # 3.er Año
                (3, "ANALISIS DE SISTEMAS"),
                (3, "MATEMATICA FINANCIERA"),
                (3, "REDES DE COMPUTADORAS"),
                (3, "ESTADISTICA"),
                (3, "SEMINARIO"),
                (3, "PRACTICA PROFESIONAL II")
            ]

            for year, name in materias:
                s = Subject(name=name, year=year, career_id=career.id)
                db.session.add(s)
            
            db.session.commit()
            print("¡Materias cargadas con éxito!")

    app.run(debug=True)      