from dash import html, dcc, callback
import dash
from dash import dcc
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from dateutil.relativedelta import *  # type: ignore
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from queries.contributors_query import contributors_query as ctq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time
import datetime as dt

PAGE = "community_health"
VIZ_ID = "contributor_count"

gc_contributor_count = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Contributor Count",
                    id=f"Contributor Count",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """Determine how many active commit authors, review participants, \n
                            issue authors, and issue comments participants there are in the past 90 days\n
                            https://chaoss.community/kb/metrics-model-community-activity/
                            """ 
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",  # needs to be the same as dbc.Button id
                    placement="top",
                    is_open=False,
                ),
                dcc.Loading(
                    dcc.Graph(id=f"{PAGE}-{VIZ_ID}"),
                ),
                dbc.Form(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dcc.DatePickerRange(
                                            id=f"date-picker-range-{PAGE}-{VIZ_ID}",
                                            min_date_allowed=dt.date(2005, 1, 1),
                                            max_date_allowed=dt.date.today(),
                                            initial_visible_month=dt.date(dt.date.today().year, 1, 1),
                                            clearable=True,
                                        ),
                                    ],
                                ),
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            "About Graph",
                                            id=f"popover-target-{PAGE}-{VIZ_ID}",
                                            color="secondary",
                                            size="sm",
                                        ),
                                    ],
                                    width="auto",
                                    style={"paddingTop": ".5em"},
                                ),
                            ],
                            align="center",
                            justify="between",
                        ),
                    ]
                ),
            ]
        )
    ],
)

# callback for graph info popover
@callback(
    Output(f"popover-{PAGE}-{VIZ_ID}", "is_open"),
    [Input(f"popover-target-{PAGE}-{VIZ_ID}", "n_clicks")],
    [State(f"popover-{PAGE}-{VIZ_ID}", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open


# callback for dynamically changing the graph title
@callback(
    Output(f"graph-title-{PAGE}-{VIZ_ID}", "children"),
    Input(f"top-k-contributors-{PAGE}-{VIZ_ID}", "value"),
)
def graph_title(k):
    title = f"Contributor Count"
    return title


# callback for contrib-importance graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "start_date"),
        Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "end_date"),
    ],
    background=True,
)
def contributor_count_graph(repolist, start_date, end_date):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=ctq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=ctq, repos=repolist)

    start = time.perf_counter()
    logging.warning(f"{VIZ_ID}- START")

    # test if there is data
    if df.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return nodata_graph, False

    # function for all data pre processing
    df = process_data(df, start_date, end_date)

    fig = create_figure(df)

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    
    return fig


def process_data(df: pd.DataFrame, start_date, end_date):

    # convert to datetime objects rather than strings
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)

    # order values chronologically by created_at date
    df = df.sort_values(by="created_at", ascending=True)

    # filter values based on date picker
    if start_date is not None:
        df = df[df.created_at >= start_date]
    if end_date is not None:
        df = df[df.created_at <= end_date]

    # Extract month from the 'date' column
    df['month'] = df['created_at'].dt.to_period('M')
    
    
     # contributor_count : Determine how many active commit authors, review participants, issue authors, and issue comments participants there are in the past 90 days.

    # Create a Dataframe for the count of contributions per month 
    result_df = df.groupby('month')['cntrb_id'].nunique().reset_index(name='num_contributors')
    
    # Convert month column to datetime

    result_df['month'] = result_df['month'].dt.to_timestamp()


    return result_df


def create_figure(df: pd.DataFrame):
    # create plotly express pie chart
    fig = px.line(
        df,
        x="month",
        y="num_contributors",
        color_discrete_sequence=color_seq
    )

    fig.add_trace(
        go.Scatter(
            x=df["month"],
            y=df["num_contributors"],
            mode="lines",
            marker=dict(color=color_seq[4]),
            name="contributor_count",
        )
    )

    # add legend title
    fig.update_layout(legend_title_text="Contribution Count")

    return fig