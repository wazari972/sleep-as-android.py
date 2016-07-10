#! /usr/bin/python3

from collections import OrderedDict
import dateutil.parser
import datetime
import time

INIT_IDEAL_SLEEP = 8.2

src_f = open("data/sleep-export.csv")

records = []

keys = None
values = None
for line in src_f.readlines():
    if keys is None:
        keys = line[:-1].split(",")
        if not keys[0]:
            #print("skip")
            keys = None
        continue
    
    records.append(OrderedDict(zip(keys, line[:-1].replace('"', "").split(","))))
    keys = None

def dt_to_hm(dt):
    t = dt.rpartition(" ")[-1]
    hr, mn = map(int, t.split(":"))

    return hr, mn

def dt_to_float(dt):
    hr, mn = dt_to_hm(dt)

    return hr + mn/60

def fromTo_to_length(from_dt, to_dt):
    #print("{} -- {}".format(start_dt, stop_dt))
    ffrom = dt_to_float(from_dt)
    to = dt_to_float(to_dt)

    if ffrom > to:
        ffrom -= 24

    return to - ffrom

avgs = {"length": [], "start": [], "stop":[]}
stats = {"length": 0, "start": 0, "stop":0}

def do_stat(i, name, value):
    if value is None: return
    
    avgs[name].append(value)
    stats[name] = sum(avgs[name])/len(avgs[name])
    
for i, rec in enumerate(records):
    do_stat(i, "length", fromTo_to_length(rec["From"], rec["To"]))

    start = dt_to_float(rec["From"])
    if start < 4:
        start += 24
    elif start < 18:
        print("skip start {}".format(start))
        start = None # skip
    do_stat(i, "start", start)
    
    stop = dt_to_float(rec["To"])
    if stop > 18:
        print("skip stop {}".format(start))
        stop = None # skip
    do_stat(i, "stop", stop)

    
##################
#Id,Tz,From,To,Sched,Hours,Rating,Comment,
#Framerate,Snore,Noise,Cycles,DeepSleep,LenAdjust,Geo
##################


to_plot = {}
to_plot["date"] = []
to_plot["sleep_time"] = []
to_plot["wakeup_time"] = []

sleep_length = {"date": [],
                "length": [],
                "deficit": [],
                "total_deficit": []}

prev_deficit = 0
for i, rec in enumerate(records):
    date = "-".join(reversed(rec["From"].rpartition(" ")[0].replace(".", "").split(" ")))
    hr, mn = dt_to_hm(rec["From"])

    date = dateutil.parser.parse(date)

    if hr < 12: # start sleeping in the morning
        # add it to previous day
        one_day = datetime.timedelta(days=-1)
        date += one_day
        
    to_plot["date"].append(date)

    #to_plot["date"].append(i)
    
    sleep_time = dt_to_float(rec["From"])
    if sleep_time < 12: sleep_time += 24

    from_time = dateutil.parser.parse(rec["From"])
    sleep_time = datetime.datetime.now().replace(hour=from_time.hour, minute=from_time.minute)
    
    to_time = dateutil.parser.parse(rec["To"])
    wakeup_time = datetime.datetime.now().replace(hour=to_time.hour, minute=to_time.minute)
    if wakeup_time < sleep_time:
        sleep_time += datetime.timedelta(days=-1)

    to_plot["sleep_time"].append(sleep_time + datetime.timedelta(hours=2))
    to_plot["wakeup_time"].append(wakeup_time + datetime.timedelta(hours=2))

    length = fromTo_to_length(rec["From"], rec["To"])

    sleep_length["date"].append(date)
    sleep_length["length"].append(length)


################################
################################
################################
    
from bokeh.io import curdoc
from bokeh.layouts import row, widgetbox, gridplot
from bokeh.models import ColumnDataSource, BoxAnnotation
from bokeh.models.widgets import Slider, TextInput, RadioButtonGroup, Panel, Tabs
from bokeh.plotting import figure
from bokeh.charts import Bar, Area, Histogram, Scatter, output_file, show, Step
from bokeh.charts.attributes import cat, color
from bokeh.models import Span
import pandas

################################

class MyPlot():
    def __init__(self, plot):
        self.plot = plot

    def add_date(self, date, color):
        test_date = datetime_to_location(date)
        test_span = Span(location=test_date,
                         dimension='height',
                         line_color=color,
                         line_dash='dashed', line_width=1)
        self.plot.add_layout(test_span)
            
    def add_box(self, bottom, top):
        mid_box = BoxAnnotation(bottom=bottom, top=top, fill_alpha=0.1, fill_color='green')
        self.plot.add_layout(mid_box)
        
    def add_line(self, x, hr, name, color):
        source = ColumnDataSource(data=dict(x=x, y=[hr]*len(x)))
        
        self.plot.line('x', 'y', source=source, color=color, line_width=3, line_alpha=0.6, legend=name)
        
def datetime_to_location(date):
    return time.mktime(date.timetuple())*1000

def plot_sleep_time():
    def do_plot(name, color):
        # Set up plot
        x = to_plot["date"]
        y = to_plot[name]

        source = ColumnDataSource(data=dict(x=x, y=y))

        plot.line('x', 'y', source=source, color=color, line_width=3, line_alpha=0.6, legend=name)

    def do_patch():
        x = to_plot["date"]
        y1 = to_plot["sleep_time"]
        y2 = to_plot["wakeup_time"]

        
        plot.patch(x+list(reversed(x)), y1+list(reversed(y2)),
                   color="lightblue", alpha=0.5, line_width=2)


    def add_key_times():
        x = to_plot["date"][0],  to_plot["date"][-1]

        myplot.add_line(x, datetime.datetime.now().replace(hour=2, minute=0), "midnight", "black")
        myplot.add_line(x, datetime.datetime.now().replace(hour=8, minute=30), "alarm", "red")

    def add_night():
        eight_pm = datetime_to_location(datetime.datetime.now().replace(hour=0, minute=30))
        eight_am = datetime_to_location(datetime.datetime.now().replace(hour=10, minute=0))
        
        myplot.add_box(eight_am, eight_pm)
        
    def add_boundaries():
        myplot.add_date(to_plot["date"][0], color="red")
        myplot.add_date(to_plot["date"][-1], color="red")

        # martinique

        myplot.add_date(datetime.datetime(year=2016, month=4, day=10), color="blue")
        myplot.add_date(datetime.datetime(year=2016, month=4, day=22), color="blue")
        
    dates = to_plot["date"]

    plot = figure(plot_height=600, plot_width=1300, title="sleep time",
                  x_axis_type="datetime", y_axis_type="datetime",
                  y_range=[max(to_plot["wakeup_time"]), min(to_plot["sleep_time"])]
                  )
    
    myplot = MyPlot(plot)
    
    do_patch()

    add_key_times()
    
    do_plot("sleep_time", "firebrick")
    do_plot("wakeup_time", "green")
    
    
    add_boundaries()
    add_night()
    
    return plot

################################

deficit_plot = None
deficit_source = None
ideal_sleep = None
deficit_above_source = None
deficit_below_source = None
deficit_above = None
deficit_below = None
def update_deficit(attrname, old, new):
    total_deficit = []     
    deficit = []
    
    cur_total_deficit = 0

    for i, length in enumerate(reversed(sleep_length["length"])):
        cur_deficit = length - ideal_sleep.value

        deficit.insert(0, cur_deficit)
        cur_total_deficit += cur_deficit
        total_deficit.insert(0, cur_total_deficit)

    sleep_length["deficit"] = deficit
    sleep_length["total_deficit"] = total_deficit


    x = sleep_length["date"]

    global deficit_above, deficit_below
    deficit_above = [d if d > 0 else 0 for d in sleep_length["total_deficit"]]
    deficit_below = [d if d < 0 else 0 for d in sleep_length["total_deficit"]]
    
    deficit_below[0] = 0
    deficit_below[-1] = 0
    
    deficit_above[0] = 0
    deficit_above[-1] = 0
    
    if attrname is not None:
        deficit_source.data.update(dict(x=sleep_length["date"], y=sleep_length["total_deficit"]))
        deficit_above_source.data.update(dict(x=sleep_length["date"], y=deficit_above))
        deficit_below_source.data.update(dict(x=sleep_length["date"], y=deficit_below))
        
        deficit_plot.y_range.start = min(sleep_length["total_deficit"])
        deficit_plot.y_range.end = max(sleep_length["total_deficit"])

    print("Updated with {}".format(ideal_sleep.value))

def plot_deficit_overlay(deficit_plot):
    global deficit_above_source, deficit_below_source
    
    deficit_above_source = ColumnDataSource(data=dict(x=sleep_length["date"], y=deficit_above))
    deficit_below_source = ColumnDataSource(data=dict(x=sleep_length["date"], y=deficit_below))
    
    deficit_plot.patch('x', 'y', source=deficit_above_source, color="lightgreen", alpha=0.5, line_width=2)
    deficit_plot.line('x', 'y', source=deficit_above_source, color="lightgreen", alpha=0.5, line_width=2)
    deficit_plot.patch('x', 'y', source=deficit_below_source, color="red", alpha=0.5, line_width=2)
    deficit_plot.line('x', 'y', source=deficit_below_source, color="red", alpha=0.5, line_width=2)
    
def plot_deficit():
    global deficit_source, deficit_plot
    
    deficit_source = ColumnDataSource(data=dict(x=sleep_length["date"], y=sleep_length["total_deficit"]))

    deficit_plot = figure(plot_height=500, plot_width=1000, title="deficit",
                          tools="crosshair,pan,reset,save,wheel_zoom",
                          x_axis_type="datetime",
                          y_range=[min(sleep_length["total_deficit"]), max(sleep_length["total_deficit"])])

    plot_deficit_overlay(deficit_plot)
    
    deficit_plot.line('x', 'y', source=deficit_source, line_width=3, line_alpha=0.6)
    
    myplot = MyPlot(deficit_plot)

    myplot.add_line(sleep_length["date"], 0, "", "red")
    
    return deficit_plot
    
def draw_deficit():
    global ideal_sleep
    ideal_sleep = Slider(title="Ideal sleep time", value=INIT_IDEAL_SLEEP, start=5.0, end=15.0, step=0.1)
    ideal_sleep.on_change('value', update_deficit)

    inputs = widgetbox(ideal_sleep)
    
    update_deficit(None, None, None) # must be before setting the source

    plot = plot_deficit()
    
    return gridplot([[plot], [inputs]], plot_width=1300, plot_height=800)

################################
################################
    
def draw_app():
    sleep_time_pan = plot_sleep_time()
    deficit_pan = draw_deficit()
    
    tabs = Tabs(tabs=[
        Panel(child=deficit_pan, title="deficit"),
        Panel(child=sleep_time_pan, title="sleep time")
        ])

    curdoc().add_root(tabs)
    curdoc().title = "sleep"
    
draw_app()
