import dash
from dash import Dash
import dash_html_components as html
import dash_core_components as dcc
import dash_table
import plotly.graph_objs as go
import urllib
import json

import logger
import workers.worker as hworker
import numpy as np
import pandas as pd

dash_histograms = None
def init_dash(app):
    global dash_histograms

    dash_histograms = Dash(__name__, server=app, url_base_pathname='/dash_histograms/')
    dash_histograms.layout = html.Div( [
            dcc.Location(id="id-location", refresh=False), # to potrzebuję aby wyciągnąć z URLa identyfikator zadania
            html.Div(id="my-debug-before", children=f"proszę czekać...!"),
            dcc.Store(id="my-store", data={'task_id':'none'}), # tutaj będę przechowywać zmienne
            dcc.Interval(id='my-interval',interval=1*1000),    # in milliseconds - co jaki czas odświeżamy w celu sprawdzenia, czy zadanie obliczeniowe się skończyło
            html.Div(id="my-debug-after", children=f"Proszę czekać...!"),
        ])
    dash_histograms.config.suppress_callback_exceptions = True


    @dash_histograms.callback([
                    dash.dependencies.Output('my-debug-before', 'children'),
                    dash.dependencies.Output('my-store', 'data')
                ],
                [dash.dependencies.Input('id-location', 'pathname'),
                dash.dependencies.Input('id-location', 'search')],
                state = [dash.dependencies.State('my-store', 'data')])
    def display_page(pathname, search, data):
        logger.debug(f"pathname: {pathname} search: {search} my-store.data before: {data}" )

        # obcinam '/' z początku
        search = search[1:] if search.startswith("?") else search       

        # Data are returned as a dictionary. The dictionary keys are the unique query 
        # variable names and the values are lists of values for each name. 
        args = urllib.parse.parse_qs(search)    
            
        if "task_id" in args:
            print(f'Otrzymałem task_id: {args["task_id"][0]}')
        else:
            print(f'pusto....')

        data['task_id'] = args["task_id"][0]
        print(f'data after: {data}')
        return f"Witaj świecie {args['task_id']}", data


    def buildLog(taskLog):
        return html.Div(children=[
                            f"Postęp obliczeń: {taskLog['progress_percent']}",
                            html.Ul(
                                children = list(map( lambda msg: html.Li(children=[msg]), taskLog['messages']))
                            )
                        ]
                    )


    @dash_histograms.callback(
                    [dash.dependencies.Output('my-debug-after', 'children')],
                    [dash.dependencies.Input('my-interval', 'n_intervals')],          
                    state = [dash.dependencies.State('my-store','data')])
    def display_interval(value, data):
        msg = ""
        if data['task_id'] != 'none':
            #logger.debug(f"Szukam joba: {data['task_id']}")

            ############ Pytam się o joba... ########
            job = hworker.get_job(data['task_id'])
            #########################################
            print(f"Oto job: {job['args']}")

            if job is not None:             
                print(job['taskLogs'])
                if job['status'] == 'finished':
                    with open(f"{job['args'][0]}/histogram.json") as f:
                        histogram = json.load(f)
                    plots = []
                    sc = histogram['scale']
                    df = pd.DataFrame([], columns=['ROI', 'D_min', 'D_avg', 'D_max'])
                    for k in histogram["original"].keys():
                        h = histogram["original"][k]
                        hdata = np.array(h[0])
                        plots.append( 
                            go.Scatter(x=hdata[:,0], y=hdata[:,1], name=k, mode='lines+markers')
                        )
                        df = df.append([ {'ROI': k, 'D_min': h[1]*sc, 'D_avg': h[2]*sc, 'D_max': h[3]*sc} ])
                    fig = go.Figure(data=plots)
                    plot = dcc.Graph(
                            id='histogram-graph',
                            figure=fig
                        )
                    table = dash_table.DataTable(
                       id='table',
                        columns=[{"name": i, "id": i} for i in df.columns],
                        data=df.to_dict('records'),
                    )
                    msg = html.Div(children=[
                                plot,
                                table
                            ]
                        )
                else:
                    msg = html.Div(children=[
                                html.Div(children=[
                                    f"Status zadania o identyfikatorze {data['task_id']} to ", 
                                    html.Span(job['status'], style={"color": "red"}),
                                    f", zwrócona wartość zadania: {job['job']}"
                                ]),
                                buildLog(job['taskLogs'])
                            ]
                        )
            else:
                msg = f"Nie mogę odnaleźć zadania o identyfikatorze {data['task_id']}"
        else:
            return f"Czekam na rozpoczęcie zadania. (Brak parametru 'task_id' w lokalnym stanie.)", 

        return msg, 


    