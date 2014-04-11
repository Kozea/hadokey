import os
import sqlite3
import calendar
import locale
from datetime import datetime, timedelta
from pygal import Line, Bar, DateY, Gauge
from flask import (
    Flask, request, session, g, redirect,  url_for, abort, render_template,
    flash)


locale.setlocale(locale.LC_ALL, 'fr_FR')


app = Flask(__name__)
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'ok.db'), DEBUG=True,
    SECRET_KEY='ok'))


def connect_db():
    """Connect to the specific database."""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    """Open a new database connexion.
    
    If the connection already exists, this connection is returned.
    
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Close the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/', methods=['GET', 'POST'])
def insert_ok():
    """Allow to insert hickup in the database.
    
    If the date is not past, the insertion is impossible
    and an error message is returned.
    
    """
    db = get_db()
    nb_ok = None if db.execute(
        'select count(*) from ok').fetchone()[0] == 0 else db.execute(
        'select count(*) from ok').fetchone()[0]
    message = (
        "Cette date n'est pas encore passée. On ne sait toujours pas si "
        "Annabelle aura le hoquet à ce moment là...")
    
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
        if timestamp >= now.timestamp():
            return render_template(
                'insert_ok.html', nb_ok=nb_ok, message=message)            
        cur = db.execute('insert into ok (moment) values(?)', [timestamp])
        db.commit()
        flash('Vous avez inséré un nouveau \'hoquet\'')
        return redirect(url_for('show_ok'))
    return render_template('insert_ok.html', nb_ok=nb_ok)


@app.route('/view')
@app.route('/view/<int:year>-<int:month>')
@app.route('/view/<int:year>-<int:month>-<int:day>')
def show_ok(year=None, month=None, day=None):
    """Allow to view hickup by hour for a specific day.
        
        It's possible to navigate between the months by entering a specific 
        date or on click.            
                
    """
    def create_calendar(year, month):
        """Allow to view hickup by hour for a specific day."""
        title = calendar.month_name[month]
        cal = calendar.Calendar(firstweekday=0)   
        days_week = calendar.day_name
        days = cal.itermonthdates(year, month)
        return (title, days_week, days)
     
    if not year and not month:
        year = datetime.now().year
        month = datetime.now().month
        title, days_week, days = create_calendar(year, month)
        return render_template(
            'show_ok.html', days=days, title=title, days_week=days_week,
            month=month, year=year, day=day)
               
    title, days_week, days = create_calendar(year, month)

    if day:
        french_date = datetime(year, month, day).strftime('%d %B %Y')
        start = datetime(year, month, day).timestamp()
        db = get_db()
        ok_list = db.execute(
            'select moment from ok where moment >= (?) and moment <= (?) '
            'order by moment', [start, start+86400])
        ok_list = [datetime.fromtimestamp(
            ok['moment']).strftime('%H:%M') for ok in ok_list]
        return render_template(
            'show_ok.html', days=days, title=title, days_week=days_week, 
            ok_list=ok_list, french_date=french_date, month=month, 
            year=year, day=day)
            
    return render_template(
            'show_ok.html', days=days, title=title, days_week=days_week,
            month=month, year=year)
            
                 
@app.route('/graphics', methods=['GET', 'POST'])
def show_graphics():
    """Allow to view graphics per month of hickup.
        
       You can see them par day or per hour.
                
    """
    if request.method == 'POST':
        graph = request.form['graphic']
        type = 'hour' if request.form['display'] == 'hour' else 'day'
        year, month, day = [int(i) for i in request.form['month'].split('-')]
        return render_template(
            'show_graphics.html', graph=graph, type=type, month=month, 
            year=year)
    return render_template('show_graphics.html')


@app.route('/graph/<graph>/<type>/<int:year>/<int:month>')
def graph(graph, type, year, month):
    """Create graphs with the parameters passed."""
    db = get_db()
    now = datetime.now()
    timestamp = now.timestamp()
    first_day = datetime(year, month, 1).timestamp()
    cal = calendar.monthrange(year, month)
    last_day = datetime(year, month, cal[1], 23, 59, 59).timestamp()
    
    if graph in ['ligne', 'histogramme']:
        line_chart = Line() if graph == 'ligne' else Bar()
        if type == 'hour':
            line_chart.title = (
                'Somme des hoquets par heure en %s' % 
                calendar.month_name[month])
            requete = db.execute(
                'select CAST(strftime(\'%H\', datetime(moment, \'unixepoch\','
                ' \'localtime\')) as integer) as hour, count(*) from ok '
                'where moment between (?) and (?) group by hour', 
                [first_day, last_day])
            hoquet = dict(requete)
            line_chart.x_labels = [
               str(hour) for hour, val in sorted(hoquet.items())]
            line_chart.add('Annabelle', [
                val for hour, val in sorted(hoquet.items())])
        else:
            hoquet = []
            line_chart.title = (
                'Nombre de hoquets par jour en %s' % 
                calendar.month_name[month])
            for day in range (int(first_day), int(timestamp), 86400):
                requete = db.execute(
                    'select count(*) from ok where moment >= (?) '
                    'and moment <= (?)', [day, day+86400]).fetchone()[0]
                hoquet.append(requete)
            line_chart.x_labels = map(str, range(cal[0], cal[1]+1))
            line_chart.add('Annabelle', hoquet)
        return line_chart.render_response()
            
        return gauge_chart.render_response()


if __name__ == '__main__':
    app.run()
