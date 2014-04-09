#IMPORTS
import os
import sqlite3
import calendar
import locale
from datetime import datetime, timedelta
from pygal import Line, Bar, DateY, Gauge
from flask import Flask, request, session, g, redirect,  url_for, abort,\
render_template, flash

locale.setlocale(locale.LC_ALL, 'fr_FR')

#APPLICATION
app = Flask(__name__)
app.config.from_object(__name__)

#CONFIG
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'ok.db'),
    DEBUG=True,
    SECRET_KEY='ok'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

#DATABASE
def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_db():
    """Opens a new database connexion if there is non yet for the current
    application context."""
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db=connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

#FUNCTIONS
@app.route('/', methods=['GET', 'POST'])
def insert_ok():
    db = get_db()
    nbOk = None if db.execute('select count(*) from ok').fetchone()[0] == 0 else db.execute('select count(*) from ok').fetchone()[0]
    if request.method =='POST':
        now = datetime.now()
        if request.form['date']:
            date = [int(i) for i in request.form['date'].split('-')]
        else: 
            date = [now.year, now.month, now.day]
        if request.form['time']:
            time = [int(i) for i in request.form['time'].split(':')]
        else:
            time = [now.hour, now.minute]
        timestamp = datetime(*(date + time)).timestamp()
        cur = db.execute('insert into ok (moment) values(?)', [timestamp])
        db.commit()
        flash('Vous avez inséré un nouveau \'hoquet\'')
        return redirect(url_for('show_ok'))
    return render_template('insert_ok.html', nbOk=nbOk)

@app.route('/view')
@app.route('/view/<date>')
def show_ok(date=None):
    now = datetime.now()
    month = now.strftime('%B')
    cal = calendar.Calendar(firstweekday=0)   
    daysweek = calendar.day_name
    days = cal.itermonthdates(now.year, now.month)
    link = now.strftime('%Y-%m-')

    db = get_db()
    nbOk = db.execute('select max(id) from ok').fetchone()[0]
        
    if date is None:
        return render_template(
            'show_ok.html', days=days, month=month, daysweek=daysweek, link=link)
    date = [int(i) for i in date.split('-')]
    table = datetime(date[0], date[1], date[2])
    frenchDate = table.strftime('%d %B %Y')
    start = datetime(*(date)).timestamp()
    ok_list = db.execute('select moment from ok where moment >= (?) and moment <= (?) order by moment', [start, start+86400])
    ok_list = [datetime.fromtimestamp(ok['moment']).strftime('%H:%M') for ok in ok_list]
    return render_template(
        'show_ok.html', days=days, month=month, daysweek=daysweek, ok_list=ok_list, 
        frenchDate=frenchDate, link=link)

@app.route('/graphics', methods=['GET', 'POST'])
def show_graphics():
    graph = None if request.method == 'GET' else request.form['graphic']
    type = hour if request.form['display'] == hour else day
    return render_template('show_graphics.html', graph=graph, type=type)

@app.route('/graph/<graph>/<type>')
def graph(graph, type):
    db = get_db()
    now = datetime.now()
    timestamp = now.timestamp()
    firstday = datetime(now.year, now.month, 1).timestamp()
    firstminute = datetime(now.year, now.month, now.day, now.hour, 0).timestamp()
    firsthour = datetime(now.year, now.month, now.day, 9).timestamp()
    lasthour = datetime(now.year, now.month, now.day, 19).timestamp()
    cal = calendar.Calendar()
    cal = calendar.monthrange(now.year, now.month)
    lastday = datetime(now.year, now.month, cal[1], 23, 59, 59).timestamp()
    
    if graph in ["ligne", "histogramme"]:
        line_chart = Line() if graph == "ligne" else Bar()
        if type == 'hour':
            line_chart.title = 'Nombre de hoquets maximum par heure ce mois'
            
            requete = db.execute('select strftime(\'%H\', datetime(moment, \'unixepoch\', \'localtime\')) as hour, count(*) from ok where moment between (?) and (?) group by hour', [firstday, lastday])
            hoquet = dict(requete)
            line_chart.x_labels = map(str, range(9, 19))
            line_chart.add('Annabelle', hoquet)
        else:
            hoquet = []
            line_chart.title = 'Nombre de hoquets par jour'
            for day in range (int(firstday), int(timestamp), 86400):
                requete = db.execute('select count(*) from ok where moment >= (?) and moment <= (?)', [day, day+86400]).fetchone()[0]
                hoquet.append(requete)
            line_chart.x_labels = map(str, range(cal[0], cal[1]+1))
            line_chart.add('Annabelle', hoquet)
        return line_chart.render_response()
            
        return gauge_chart.render_response()
        
if __name__ == '__main__':
    app.run()
