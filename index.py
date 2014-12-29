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
        CREATE TABLE IF NOT EXISTS user (
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


def get_type_name_map():
    return {
        0: u'吃',
        1: u'穿',
        2: u'住',
        3: u'行'
    }


def get_week_cost_details(date):
    _format = '%Y%m%d'
    username = request.get_cookie('username')
    uid = request.get_cookie('uid', secret='somekey')
    start_time, end_time = get_week_range(date)
    prev = date + datetime.timedelta(-7)
    _next = date + datetime.timedelta(7)
    columns_charts_data = get_columns_chart_data(uid, start_time, end_time)
    line_charts_data, line_charts_url = get_line_chart_data(uid, start_time, end_time)
    pie_charts_data, pie_charts_name = get_pie_chart_data(uid, start_time, end_time)
    config_map = {
        'start_time': start_time.strftime('%Y年%m月%d日'),
        'end_time': end_time.strftime('%Y年%m月%d日'),
        'prev': prev.strftime(_format),
        'next': _next.strftime(_format),
        'username': username,
        'categories': get_week_dayname_lst(),
        'lineChartsName': u"'当日合计'",
        'lineChartsData': line_charts_data,
        'pieChartsName': pie_charts_name,
        'pieChartsData': pie_charts_data,
        'columnChartsData': columns_charts_data,
        'lineChartsDataUrl': line_charts_url,
        'columnChartsNames': get_type_name_map(),
    }
    return template('index.tpl', **config_map)


def get_columns_chart_data(uid, start_time, end_time):
    sql = """select type,cost,description,time from mymoney where time >='{start_time}' and time <='{end_time}' and uid = {uid} order by time"""
    con = sqlite3.connect('money.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cur = con.cursor()
    query_param_map = {'start_time': start_time, 'end_time': end_time, 'uid': uid}
    cur.execute(sql.format(**query_param_map))
    result_map = {}
    date_format = '%Y%m%d'
    for _type, cost, desc, times in cur.fetchall():
        date_str = times.strftime(date_format)
        result_map[_type] = result_map.get(_type, {})
        result_map[_type][date_str] = result_map[_type].get(date_str, 0) + cost
    columns_charts_data = {}
    for _type in result_map:
        columns_charts_data[_type] = []
        date_from, date_end = start_time, end_time
        while date_from <= date_end:
            date_str = date_from.strftime(date_format)
            columns_charts_data[_type].append(result_map[_type].get(date_str, 0))
            date_from += datetime.timedelta(1)
    for i in get_type_name_map():
        columns_charts_data[i] = columns_charts_data.get(i, [])
    cur.close()
    con.close()
    return columns_charts_data


def get_line_chart_data(uid, start_time, end_time):
    everyday_cost_sql = "select sum(cost) from mymoney where time >= '{start_time}' and time < '{end_time}' and uid = {uid}"
    con = sqlite3.connect('money.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cur = con.cursor()
    line_charts_url = []
    line_charts_data = []
    date_format = '%Y%m%d'
    date_from, date_end = start_time, end_time
    while date_from <= date_end:
        date_str = date_from.strftime(date_format)
        query_param_map = {'uid': uid, 'start_time': date_from}
        date_from += datetime.timedelta(1)
        query_param_map.update({'end_time': date_from})
        cur.execute(everyday_cost_sql.format(**query_param_map))
        cost = cur.fetchone()[0]
        if cost is None:
            cost = 0
        line_charts_data.append(cost)
        line_charts_url.append('/details/{0}'.format(date_str))
    cur.close()
    con.close()
    return line_charts_data, line_charts_url


def get_pie_chart_data(uid, start_time, end_time):
    everytype_cost_sql = "select type,sum(cost) from mymoney where time >= '{start_time}' and time <= '{end_time}' and uid = {uid} group by type"
    con = sqlite3.connect('money.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cur = con.cursor()
    pie_charts_data = []
    pie_charts_name = []
    query_param_map = {'uid': uid, 'start_time': start_time, 'end_time': end_time}
    type_name_map = get_type_name_map()
    cur.execute(everytype_cost_sql.format(**query_param_map))
    for _type, cost in cur.fetchall():
        pie_charts_data.append(cost)
        pie_charts_name.append(type_name_map.get(_type))
    cur.close()
    con.close()
    return pie_charts_data, pie_charts_name


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
    _format = '%Y%m%d'
    today = datetime.datetime.today()
    if date is None:
        date = today
    else:
        date = datetime.datetime.strptime(date, _format)
    return get_week_cost_details(date)


@route('/details/:date', apply=auth_fn)
@validate(date=str)
def show_details_day(date):
    _format = '%Y%m%d'
    date = datetime.datetime.strptime(date, _format)
    uid = request.get_cookie('uid', secret='somekey')
    sql = "select type,cost,description,time from mymoney where time >= '{start_time}' and time < '{end_time}' and uid = {uid} order by time"
    con = sqlite3.connect('money.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cur = con.cursor()
    query_param_map = {'uid': uid, 'start_time': date, 'end_time': date+datetime.timedelta(1)}
    cur.execute(sql.format(**query_param_map))
    msg = u''
    maps = get_type_name_map()
    for _type, cost, desc, times in cur.fetchall():
        msg += u"<p>type:{0} cost: {1} 元 desc: {2}  times:{3}</p>".format(maps[_type], cost, desc, times.strftime('%H:%M:%S'))
    if not msg:
        msg += u'<p>no data</p>'
    return u'<p>你在<b>{0}</b>的消费情况如下</p><ul>{1}</ul>'.format(date.strftime('%Y-%m-%d'), msg)


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
        type_name_map = get_type_name_map()
        for idx, item in type_name_map.iteritems():
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
