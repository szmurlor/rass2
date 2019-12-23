import dash
from dash import Dash
import dash_html_components as html
import dash_core_components as dcc
import urllib

import database
import modules.histograms.worker as hworker

dash_histograms = None
def init_dash(app):
    global dash_histograms

    dash_histograms = Dash(__name__, server=app, url_base_pathname='/dash_histograms/')
    dash_histograms.layout = html.Div( [
            dcc.Location(id="id-location", refresh=False),
            html.Div(id="my-out", children=f"Witaj świecie ...!"),
            dcc.Store(id="my-store", data={'task_id':'none'}),
            dcc.Interval(
            id='my-interval',
            interval=1*1000 # in milliseconds
            ),
            html.Div(id="my-out-2", children=f"Task status...!"),
        ])
    dash_histograms.config.suppress_callback_exceptions = True


    @dash_histograms.callback([
                    dash.dependencies.Output('my-out', 'children'),
                    dash.dependencies.Output('my-store', 'data')
                ],
                [dash.dependencies.Input('id-location', 'pathname'),
                dash.dependencies.Input('id-location', 'search')],
                state = [dash.dependencies.State('my-store', 'data')])
    def display_page(pathname, search, data):
        print(pathname)
        print(search)
        print(f'data before: {data}')
        search = search[1:] if search.startswith("?") else search
        print(urllib.parse.parse_qs(search))
        args = urllib.parse.parse_qs(search)    
        firstname = args['firstname'][0] if 'firstname' in args else "brak danych"
            
        res = None
        if "beamlets_token" in args:
            btoken = args["beamlets_token"][0]
            stored_file = database.StoredFile.query.filter_by(token=btoken).one_or_none()
            #firstname = stored_file.name
            res = hworker.calculate_histogram(stored_file.uid)
            data['task_id'] = res['data']['task_id']

        print(f'data after: {data}')
        return f"Witaj świecie {firstname} {res}", data


    @dash_histograms.callback(
                    [dash.dependencies.Output('my-out-2', 'children')],
                    [dash.dependencies.Input('my-interval', 'n_intervals')],          
                    state = [dash.dependencies.State('my-store','data')])
    def display_interval(value, data):
        job = hworker.get_job(data['task_id'])
        return f"Witaj świecie {data} {job['status']}", 

    