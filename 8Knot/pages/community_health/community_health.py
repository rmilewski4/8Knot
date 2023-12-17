from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

# import visualization cards
from .visualizations.change_request_review_count import change_request_review_count

from .visualizations.issues_closed import gc_issues_closed
from .visualizations.contributor_count import gc_contributor_count
from .visualizations.issue_assignments import gc_issue_assignments

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/community_health")

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(gc_issues_closed, width=6),
                dbc.Col(gc_issue_assignments, width=6),
                dbc.Col(change_request_review_count, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_contributor_count, width=6),
                #dbc.Col(change_request_review_count, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        )
    ],
    fluid=True,
)
