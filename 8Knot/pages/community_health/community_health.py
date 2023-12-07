from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

# import visualization cards
from .visualizations.project_velocity import gc_project_velocity
from .visualizations.change_request_review_count import change_request_review_count
from .visualizations.bus_factor             import gc_bus_factor_pie
from .visualizations.change_req_close_ratio import gc_change_req_closure_ratio
from .visualizations.release_freq import gc_release_freq
from .visualizations.issues_closed import gc_issues_closed

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/community_health")

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(gc_issues_closed, width=6),
                dbc.Col(change_request_review_count, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                #dbc.Col(gc_bus_factor_pie, width=6),
                #dbc.Col(change_request_review_count, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        )
    ],
    fluid=True,
)
