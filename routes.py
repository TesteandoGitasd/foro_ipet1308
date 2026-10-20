import os
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, send_from_directory, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func
from models import db, User, Career, Subject, FileModel, Rating

def init_routes(app):
    
    @app.route('/')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('careers_list'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            identifier = request.form.get('identifier')
            password = request.form.get('password')
            
            user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()
            if user and check_password_hash(user.password, password):
                if not user.is_active_user:
                    flash('Tu cuenta ha sido bloqueada por un administrador.', 'danger')
                    return redirect(url_for('login'))
                login_user(user)
                return redirect(url_for('careers_list'))
            flash('Correo/Usuario o contraseña incorrectos.', 'danger')
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        careers = Career.query.all()
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            career_id = request.form.get('career_id')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if password != confirm_password:
                flash('Las contraseñas no coinciden.', 'danger')
                return redirect(url_for('register'))
            
            if User.query.filter_by(email=email).first():
                flash('El correo electrónico ya está registrado.', 'danger')
                return redirect(url_for('register'))
            
            if User.query.filter_by(username=username).first():
                flash('El nombre de usuario ya está en uso.', 'danger')
                return redirect(url_for('register'))
            
            # Asignar rol admin si el correo coincide, de lo contrario alumno por defecto
            role = 'admin' if email.strip().lower() == 'josearmandovlud@gmail.com' else 'alumno'
            
            hashed_pw = generate_password_hash(password, method='scrypt')
            new_user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                career_id=career_id,
                password=hashed_pw,
                role=role
            )
            db.session.add(new_user)
            db.session.commit()
            flash('¡Registro exitoso! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
            
        return render_template('register.html', careers=careers)

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if request.method == 'POST':
            email = request.form.get('email')
            user = User.query.filter_by(email=email).first()
            if user:
                flash('Se ha enviado un enlace seguro de recuperación a tu correo institucional.', 'success')
            else:
                flash('No se encontró una cuenta asociada a ese correo.', 'warning')
            return redirect(url_for('login'))
        return render_template('forgot_password.html')

    # PANEL DE GESTIÓN DEL ADMINISTRADOR
    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if current_user.role != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('careers_list'))
        
        sort_by = request.args.get('sort', 'date')
        
        if sort_by == 'rating':
            files = db.session.query(FileModel).\
                outerjoin(Rating).\
                group_by(FileModel.id).\
                order_by(func.coalesce(func.avg(Rating.score), 0).desc()).all()
        else:
            files = FileModel.query.order_by(FileModel.created_at.desc()).all()
            
        users = User.query.all()
        return render_template('admin_dashboard.html', files=files, users=users, current_sort=sort_by)

    # CAMBIAR RANGO (PROFESOR O ALUMNO)
    @app.route('/admin/set-role/<int:user_id>/<string:new_role>')
    @login_required
    def set_user_role(user_id, new_role):
        if current_user.role != 'admin':
            flash('Acceso denegado.', 'danger')
            return redirect(url_for('careers_list'))
            
        user = User.query.get_or_404(user_id)
        if user.role == 'admin':
            flash('No se pueden modificar los permisos de un administrador.', 'danger')
            return redirect(url_for('admin_dashboard'))
            
        if new_role in ['alumno', 'profesor']:
            user.role = new_role
            db.session.commit()
            flash(f'El usuario {user.username} ahora es {new_role}.', 'success')
            
        return redirect(url_for('admin_dashboard'))

    # BORRAR TODOS LOS POSTS DE UN USUARIO
    @app.route('/admin/delete-user-files/<int:user_id>')
    @login_required
    def delete_user_files(user_id):
        if current_user.role != 'admin':
            flash('Acceso denegado.', 'danger')
            return redirect(url_for('careers_list'))
            
        user = User.query.get_or_404(user_id)
        for file_record in user.files:
            try:
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass
            db.session.delete(file_record)
            
        db.session.commit()
        flash(f'Se han eliminado todos los apuntes subidos por {user.username}.', 'success')
        return redirect(url_for('admin_dashboard', sort=request.args.get('sort', 'date')))

    # BORRAR UN ARCHIVO / POST INDIVIDUALMENTE
    @app.route('/admin/delete-file/<int:file_id>')
    @login_required
    def delete_file(file_id):
        file_record = FileModel.query.get_or_404(file_id)
        
        # Solo el administrador o el creador del archivo pueden borrarlo
        if current_user.role != 'admin' and file_record.user_id != current_user.id:
            flash('No tienes permisos para eliminar este archivo.', 'danger')
            return redirect(url_for('careers_list'))
            
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
            
        db.session.delete(file_record)
        db.session.commit()
        
        flash('El apunte ha sido eliminado correctamente.', 'success')
        return redirect(request.referrer or url_for('careers_list'))

    # BLOQUEAR / DESBLOQUEAR USUARIO
    @app.route('/admin/toggle-block-user/<int:user_id>')
    @login_required
    def toggle_block_user(user_id):
        if current_user.role != 'admin':
            flash('Acceso denegado.', 'danger')
            return redirect(url_for('careers_list'))
            
        user = User.query.get_or_404(user_id)
        if user.role == 'admin':
            flash('No se puede bloquear a un usuario administrador.', 'danger')
            return redirect(url_for('admin_dashboard'))
            
        user.is_active_user = not user.is_active_user
        db.session.commit()
        
        status = "bloqueado" if not user.is_active_user else "desbloqueado"
        flash(f'El usuario {user.username} ha sido {status} exitosamente.', 'success')
        return redirect(url_for('admin_dashboard'))

    @app.route('/careers')
    @login_required
    def careers_list():
        careers = Career.query.all()
        return render_template('careers.html', careers=careers)

    @app.route('/career/<int:career_id>')
    @login_required
    def career_detail(career_id):
        career = Career.query.get_or_404(career_id)
        years = sorted(list(set([s.year for s in career.subjects])))
        if not years:
            years = [1, 2, 3]
        return render_template('career_detail.html', career=career, years=years)

    @app.route('/career/<int:career_id>/year/<int:year_num>')
    @login_required
    def year_subjects(career_id, year_num):
        career = Career.query.get_or_404(career_id)
        subjects = Subject.query.filter_by(career_id=career.id, year=year_num).all()
        return render_template('year_subjects.html', career=career, year_num=year_num, subjects=subjects)

    @app.route('/subject/<int:subject_id>', methods=['GET', 'POST'])
    @login_required
    def subject_detail(subject_id):
        subject = Subject.query.get_or_404(subject_id)
        if request.method == 'POST':
            # Validación de Cooldown de 5 segundos
            now = datetime.utcnow()
            if current_user.last_upload_time:
                time_diff = (now - current_user.last_upload_time).total_seconds()
                if time_diff < 5:
                    wait_time = int(5 - time_diff) + 1
                    flash(f'Por favor espera {wait_time} segundo(s) antes de volver a subir otro archivo.', 'warning')
                    return redirect(request.url)

            title = request.form.get('title')
            description = request.form.get('description')
            file = request.files.get('file')

            if not file or file.filename == '':
                flash('Debe seleccionar un archivo válido.', 'danger')
                return redirect(request.url)

            allowed_extensions = ['.pdf', '.doc', '.docx']
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in allowed_extensions:
                flash('Formato no válido. Solo se admiten archivos PDF o Word.', 'danger')
                return redirect(request.url)

            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            new_file = FileModel(
                title=title, description=description, filename=filename,
                original_name=file.filename, user_id=current_user.id, subject_id=subject.id
            )
            
            current_user.last_upload_time = now
            
            db.session.add(new_file)
            db.session.commit()
            flash('Apunte subido con éxito.', 'success')
            return redirect(url_for('subject_detail', subject_id=subject.id))

        return render_template('subject_detail.html', subject=subject)

    @app.route('/rate/<int:file_id>/<int:score>')
    @login_required
    def rate_file(file_id, score):
        if 1 <= score <= 5:
            existing = Rating.query.filter_by(user_id=current_user.id, file_id=file_id).first()
            if existing:
                existing.score = score
            else:
                db.session.add(Rating(score=score, user_id=current_user.id, file_id=file_id))
            db.session.commit()
            flash('¡Calificación guardada!', 'success')
        return redirect(request.referrer)

    @app.route('/download/<int:file_id>')
    @login_required
    def download(file_id):
        file_record = FileModel.query.get_or_404(file_id)
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], file_record.filename, as_attachment=True)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))