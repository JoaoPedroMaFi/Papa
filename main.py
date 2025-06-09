import os
from datetime import datetime
from flask import Flask, render_template, request, url_for, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.file import FileAllowed
from sqlalchemy import select, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.utils import secure_filename
from wtforms import validators
from wtforms.fields.choices import RadioField
from wtforms.fields.simple import StringField, SubmitField, TextAreaField, FileField
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm, RecaptchaField
from flask_uploads import UploadSet, IMAGES, configure_uploads
import locale


class Base(DeclarativeBase):
    pass


db = SQLAlchemy()
# instance of flask application
app = Flask(__name__)
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///advertises.db"
app.config['SECRET_KEY'] = 'any secret string'
app.config['RECAPTCHA_PUBLIC_KEY'] = '++++'
app.config['RECAPTCHA_PRIVATE_KEY'] = '+++++'
app.config['RECAPTCHA_OPTIONS'] = {'theme': 'black'}
# File size
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
MEGABYTE = (2 ** 10) ** 2
app.config['MAX_CONTENT_LENGTH'] = None
# Max number of fields in a multi part form (I don't send more than one file)
# app.config['MAX_FORM_PARTS'] = ...
app.config['MAX_FORM_MEMORY_SIZE'] = 50 * MEGABYTE
# initialize the app with the extension
db.init_app(app)
bootstrap = Bootstrap5(app)

app.config['UPLOADED_IMAGES_DEST'] = os.path.join(app.root_path, 'static', 'uploads')  # Set destination
images = UploadSet('images', IMAGES)  # Define the UploadSet
configure_uploads(app, images)


class AdForm(FlaskForm):
    city = StringField('Região:', [validators.Length(min=4, max=25), validators.DataRequired()], description="Cidade")
    gender = RadioField(label="Sou Homem ou Mulher:", choices=[(1, 'Homem'), (0, 'Mulher')],
                        validators=[validators.DataRequired()])

    title = StringField('Título:',
                        [validators.Length(min=6, max=30), validators.DataRequired()])  # Aumentei o max para 100
    location = StringField('Local:', [validators.Length(min=3, max=100), validators.DataRequired()],  # Ajustei min/max
                           description="(Cidade, Vila, Bairro) - apenas texto, não coloque números!")

    # DESCOMENTAR e AUMENTAR o max para um valor alto como 5000 ou 10000 para permitir texto longo
    advertise = TextAreaField('Texto do Anúncio ', [validators.Length(min=6, max=5000), validators.DataRequired()],
                              render_kw={'rows': 10})

    email = StringField('Email:', [validators.Length(min=6, max=350), validators.DataRequired(), validators.Email()])

    upload = FileField('Imagem_1:', validators=[FileAllowed(images, 'Images only!')])
    upload1 = FileField('Imagem_2:', validators=[FileAllowed(images, 'Images only!')])
    upload2 = FileField('Imagem_3:', validators=[FileAllowed(images, 'Images only!')])
    upload3 = FileField('Imagem_4:', validators=[FileAllowed(images, 'Images only!')])

    # DESCOMENTAR o recaptcha se quiser usá-lo
    # recaptcha = RecaptchaField()
    submit = SubmitField("Adicionar Anúncio")


class Advertise(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(nullable=False)  # Removi unique=True, pois cidades podem repetir
    gender: Mapped[int] = mapped_column(nullable=False)
    date: Mapped[str] = mapped_column(nullable=False)  # Use Mapped[str] para a data se for string
    title: Mapped[str] = mapped_column(nullable=False)
    location: Mapped[str] = mapped_column(nullable=False)
    advertise: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(nullable=False)

    # uploadX também devem ser Text para guardar o caminho (string)
    upload: Mapped[str] = mapped_column(Text, nullable=True)
    upload1: Mapped[str] = mapped_column(Text, nullable=True)
    upload2: Mapped[str] = mapped_column(Text, nullable=True)
    upload3: Mapped[str] = mapped_column(Text, nullable=True)
    views: Mapped[int] = mapped_column(default=0, nullable=False)

    def __init__(self, city=None, gender=None, date=None, title=None, location=None, advertise=None, email=None,
                 upload=None, upload1=None, upload2=None, upload3=None):
        self.city = city
        self.gender = gender
        self.date = date
        self.title = title
        self.location = location
        self.advertise = advertise
        self.email = email
        self.upload = upload
        self.upload1 = upload1
        self.upload2 = upload2
        self.upload3 = upload3


# Create the database tables if they don't exist
# You need to run this once before your application can interact with the database
with app.app_context():
    db.create_all()


# home route that returns below text when root url is accessed
@app.route('/')
@app.route('/index')
def index():
    category = None
    category = request.args.get('category')
    error_message = request.args.get('error')
    page = request.args.get('page', 1, type=int)

    if category:
        query = db.session.query(Advertise).where(Advertise.gender == category).order_by(Advertise.date.desc())
    else:
        query = db.session.query(Advertise).order_by(Advertise.date.desc())
    advertises = query.paginate(page=page, per_page=20, error_out=False)

    # pagination
    next_url = url_for('index', page=advertises.next_num) \
        if advertises.has_next else None
    prev_url = url_for('index', page=advertises.prev_num) \
        if advertises.has_prev else None

    return render_template("index.html", advertises=advertises, next_url=next_url,
                           prev_url=prev_url, error=error_message)


@app.route("/ad/<advertise_id>", methods=["GET"])
def advertise_ad(advertise_id):
    locale.setlocale(locale.LC_TIME, 'pt_PT')
    advertise_ad_obj = db.session.execute(
        select(Advertise).where(Advertise.id == advertise_id)
    ).scalar_one_or_none()
    date = advertise_ad_obj.date

    data_format = datetime.strptime(date, '%d/%m/%Y %H:%M:%S %A')
    correct_data = str.title(data_format.strftime("%A, %d de %B de %Y - %H:%M"))
    # Incrementar views apenas se ainda não foi visto nesta sessão
    view_key = f'viewed_{advertise_id}'
    if not session.get(view_key):
        advertise_ad_obj.views += 1
        db.session.commit()
        session[view_key] = True  # Marca como visto na sessão do navegador

    return render_template("advertise.html", advertise_ad=advertise_ad_obj, date_obj=correct_data)


"""
@app.route("/new_advertise", methods=['GET', 'POST'])
def new_advertise():
    print("i am in")
    locale.setlocale(locale.LC_TIME, 'pt_PT')
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S %A")
    form = AdForm()
    total = db.session.execute(func.max(Advertise.id)).scalar()
    localfolder = str(total + 1)
    if request.method == 'POST' and form.validate():
        uploaded_url = None
        if form.upload.data and form.upload.data.filename:
            filename = images.save(form.upload.data)  # Saves the file and returns its *filename*
            uploaded_url = url_for('static',
                                   filename=f'uploads/{localfolder}/{filename}')  # Generates the public URL (e.g., /static/uploads/image.jpg)
            print(f"DEBUG: Saved {filename}, Generated URL: {uploaded_url}")  # Adicione este print para depurar

        uploaded1_url = None
        if form.upload1.data and form.upload1.data.filename:
            filename1 = images.save(form.upload1.data)
            uploaded1_url = url_for('static', filename=f'uploads/{filename}')
            print(f"DEBUG: Saved {filename1}, Generated URL: {uploaded1_url}")

        uploaded2_url = None
        if form.upload2.data and form.upload2.data.filename:
            filename2 = images.save(form.upload2.data)
            uploaded2_url = url_for('static', filename=f'uploads/{filename}')
            print(f"DEBUG: Saved {filename2}, Generated URL: {uploaded2_url}")

        uploaded3_url = None
        if form.upload3.data and form.upload3.data.filename:
            filename3 = images.save(form.upload3.data)
            uploaded3_url = url_for('static', filename=f'uploads/{filename}')
            print(f"DEBUG: Saved {filename3}, Generated URL: {uploaded3_url}")

        new_ad = Advertise(
            city=form.city.data,
            gender=form.gender.data,
            date=dt_string,
            title=form.title.data,
            location=form.location.data,
            advertise=form.advertise.data,
            email=form.email.data,
            upload=uploaded_url,  # THIS IS WHAT'S STORED IN DB
            upload1=uploaded1_url,
            upload2=uploaded2_url,
            upload3=uploaded3_url
        )
        db.session.add(new_ad)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template("add_advertise.html", form=form)"""


@app.route("/new_advertise", methods=['GET', 'POST'])
def new_advertise():
    print("i am in")
    locale.setlocale(locale.LC_TIME, 'pt_PT')
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S %A")

    form = AdForm()
    total = db.session.execute(func.max(Advertise.id)).scalar() or 0
    localfolder = str(total + 1)

    # Cria a subpasta para esse anúncio
    upload_folder = os.path.join(app.config['UPLOADED_IMAGES_DEST'], localfolder)
    os.makedirs(upload_folder, exist_ok=True)

    uploaded_url = uploaded1_url = uploaded2_url = uploaded3_url = None

    if request.method == 'POST' and form.validate():
        def save_file(file_field):
            if file_field.data and file_field.data.filename:
                filename = secure_filename(file_field.data.filename)
                file_path = os.path.join(upload_folder, filename)
                file_field.data.save(file_path)
                return url_for('static', filename=f'uploads/{localfolder}/{filename}')
            return None

        uploaded_url = save_file(form.upload)
        uploaded1_url = save_file(form.upload1)
        uploaded2_url = save_file(form.upload2)
        uploaded3_url = save_file(form.upload3)

        new_ad = Advertise(
            city=form.city.data,
            gender=form.gender.data,
            date=dt_string,
            title=form.title.data,
            location=form.location.data,
            advertise=form.advertise.data,
            email=form.email.data,
            upload=uploaded_url,
            upload1=uploaded1_url,
            upload2=uploaded2_url,
            upload3=uploaded3_url
        )
        db.session.add(new_ad)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template("add_advertise.html", form=form)


if __name__ == '__main__':
    app.run(debug=True)
