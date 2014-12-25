# encoding=utf8
from bottle import route, run, error
from bottle import request, response
from bottle import redirect, template
from bottle import validate

import sqlite3
import datetime
import calendar
import json

def init_db():
    """
        CREATE TABLE IF NOT EXISTS mymoney (
            id INTEGER PRIMARY KEY,
            uid INTEGER,
            type TINYINT,
            cost NUMERIC,
            description VARCHAR(100),
            time TIMESTAMP);
        CREATE TABLE NOT EXISTS user (
            id INTEGER PRIMARY KEY,
            username VARCHAR(30),
            password VARCHAR(30));
    """
    # use .schema table to show.
    pass

def get_week_range(date):
    start_day = date + datetime.timedelta(days=-date.weekday())
    end_day = date + datetime.timedelta(days=6-date.weekday())
    date_from = datetime.datetime(start_day.year, start_day.month, start_day.day, 0, 0, 0)
    date_to = datetime.datetime(end_day.year, end_day.month, end_day.day, 23, 59, 59)
    return [date_from, date_to]


def get_week_dayname_lst():
    return [calendar.day_name[i] for i in xrange(7)]


def get_type_name_lst():
    return [u'吃', u'穿', u'住', u'行']


def get_week_cost_details(userid, start_time, end_time):
    sql = """select type,cost,description,time from mymoney where time >='{start_time}' and time <='{end_time}' and uid = {uid} and type = {type} order by time"""
    con = sqlite3.connect('money.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cur = con.cursor()
    lst = get_type_name_lst()
    query_param_map = {'start_time': start_time, 'end_time': end_time, 'uid': userid, 'type': 0}
    print sql.format(**query_param_map)
    result = []
    for _type in xrange(len(lst)):
        item = {}
        query_param_map.update({'type': _type})
        cur.execute(sql.format(**query_param_map))
        for _, cost, desc, times in cur.fetchall():
            weekday = times.weekday()
            item[weekday] = item.get(weekday, 0) + cost
        result.append(item)
    cur.close()
    con.close()
    # TODO:只提供数据，不把hicharts的配置放这里
    return make_series(*_getlst(result))


def _getlst(result):
    lst = []
    new_result = []
    total_cost = []
    everyday_cost = []
    for item in result:
        lst = []
        for weekday in xrange(7):
            cost = item.get(weekday, 0)
            lst.append(cost)
        new_result.append(lst)
        total_cost.append(sum(lst))
    everyday_cost = map(sum, zip(*new_result))
    return new_result, total_cost, everyday_cost


def make_series(result, total, everyday):
    name_list = get_type_name_lst()
    json_lst = []
    for idx, item in enumerate(result):
        maps = {
            'type': 'column',
            'name': name_list[idx],
            'data': item
        }
        json_lst.append(maps)
    maps = {
        'type': 'spline',
        'name': u'当日合计',
        'data': everyday,
        'marker': {
            'lineWidth': 3,
        }

    }
    json_lst.append(maps)
    maps = {
        'type': 'pie',
        'name': u'汇总',
        'data': [{'name': name_list[idx], 'y': item} for idx, item in enumerate(total)],
        'center': [100, 0],
        'size': 100,
        'showInLegend': 0,
        'dataLabels': {
            'enabled': 0
        }
    }
    json_lst.append(maps)
    return json_lst


def auth_fn(fn):
    def _check_logined_wrapp(**kwargs):
        if request.get_cookie('username'):
            return fn(**kwargs)
        else:
            redirect('/login', 302)
    return _check_logined_wrapp


def clear_cookie():
    for key in request.cookies:
        response.delete_cookie(key)


def check_login(username, password):
    sql = """select * from user where username = '{0}' and password = '{1}' """
    con = sqlite3.connect('money.db')
    cur = con.cursor()
    cur.execute(sql.format(username, password))
    result = cur.fetchone()
    cur.close()
    con.close()
    return result


def insert_item(uid, types, cost, desc, times):
    con = sqlite3.connect('money.db', detect_types=sqlite3.PARSE_DECLTYPES)
    con.text_factory = str
    con.execute("INSERT INTO mymoney(uid,type,cost,description,time) values (?,?,?,?,?)",
                (uid, types, cost, desc, times))
    con.commit()
    con.close()


@route('/page/:date', apply=auth_fn)
@validate(date=str)
@route('/', apply=auth_fn)
def money_list(date=None):
    username = request.get_cookie('username')
    uid = request.get_cookie('uid', secret='somekey')
    _format = '%Y%m%d'
    today = datetime.datetime.today()
    if date is None:
        date = today
    else:
        date = datetime.datetime.strptime(date, _format)
    start_time, end_time = get_week_range(date)
    result = get_week_cost_details(uid, start_time, end_time)
    prev = date + datetime.timedelta(-7)
    _next = date + datetime.timedelta(7)
    config_map = {
        'start_time': start_time.strftime('%Y年%m月%d日'),
        'end_time': end_time.strftime('%Y年%m月%d日'),
        'prev': prev.strftime(_format),
        'next': _next.strftime(_format),
        'username': username,
        'config': json.dumps(result, ensure_ascii=False),
        'categories': get_week_dayname_lst(),
    }
    return template('index.tpl', **config_map)


@route('/add', apply=auth_fn)
def add_item():
    if request.GET.get('save', '').strip():
        types = request.GET.get('types', 0)
        desc = request.GET.get('desc', '')
        cost = request.GET.get('cost', 0)
        times = request.GET.get('times')
        if not times:
            times = datetime.datetime.now()
        uid = request.get_cookie('uid', secret='somekey')
        # _validate_data()
        insert_item(uid, types, cost, desc, times)
        return '<p> Add ok,click<a href="/">here</a>to goto index and <a href="/add">here</a> to add a new record</p>' + str(times)
    else:
        option = u''
        for idx, item in enumerate(get_type_name_lst()):
            option += u'<option value={0}>{1}</option>'.format(idx, item)
        msg = u"""
        <p>添加记录:</p>
        <form action="/add" method="GET">
            types:<select name="types">
                {0}
            </select>
            <br>
            desc:<input type="text" name="desc">
            <br>
            cost:<input type="text" name="cost" >
            <br>
            times:<input type="datetime" name="times" >
            <br>
            <input type="submit" name="save" value="save">

        </form>
        """.format(option)
        return msg


@error(404)
def error404(error):
    return '<p style="text-align:center;font-size:40px;color:red;">Page not found</p>'


@route('/login')
def login():
    template_file_content = """
    <form action='/login' method='post'>
    username:<input type='text' name='username'/>
    passowrd:<input type='password' name='password' />
    <input type='submit'/>
    </form>
    """
    if request.cookies:
        template_file_content = '<p>Login error,try again!</p>' + template_file_content
        clear_cookie()
    return template_file_content


@route('/login', method='POST')
def do_login():
    username = request.forms.get('username')
    password = request.forms.get('password')
    result = check_login(username, password)
    if result:
        response.set_cookie('uid', result[0], secret='somekey')
        response.set_cookie('username', username)
        redirect('/', 302)
    else:
        response.set_cookie('logined', 'false')
        redirect('/login', 302)


@route('/logout')
def do_logout():
    clear_cookie()
    redirect('/login')


if __name__ == '__main__':
    run(debug=True, port=8080)
