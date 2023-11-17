from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash import callback
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
import logging
from pages.utils.graph_utils import get_graph_time_values, color_seq
import io
from pages.utils.job_utils import nodata_graph
from queries.release_query import release_query as rlq
from cache_manager.cache_manager import CacheManager as cm
import time
import numpy as np

PAGE = "chaoss_1"
VIZ_ID = "release-frequency"

gc_release_freq = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Release Frequency",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """The frequency of project software / artifact releases over time. \n
                            This includes the major releases and smaller point releases that might contain bug fixes and security updates. \n
                            For more info, see:
                            https://chaoss.community/kb/metric-release-frequency/"""
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",
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
                                dbc.Label(
                                    "Date Interval:",
                                    html_for=f"date-interval-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id=f"date-interval-{PAGE}-{VIZ_ID}",
                                        options=[
                                            {
                                                "label": "Day",
                                                "value": "D",
                                            },
                                            {
                                                "label": "Week",
                                                "value": "W",
                                            },
                                            {"label": "Month", "value": "M"},
                                            {"label": "Year", "value": "Y"},
                                        ],
                                        value="M",
                                        inline=True,
                                    ),
                                    className="me-2",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "About Graph",
                                        id=f"popover-target-{PAGE}-{VIZ_ID}",
                                        color="secondary",
                                        size="sm",
                                    ),
                                    width="auto",
                                    style={"paddingTop": ".5em"},
                                ),
                            ],
                            align="center",
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


# callback for release freq graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)
def release_freq_graph(
    repolist, interval
):

    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=rlq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=rlq, repos=repolist)

    start = time.perf_counter()
    logging.warning(f"{VIZ_ID}- START")

    # test if there is data
    if df.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return nodata_graph

    # function for all data pre processing
    df_release = process_data(df, interval)

    fig = create_figure(df_release, interval)

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    return fig


def process_data(
    df: pd.DataFrame,
    interval
):

    # convert dates to datetime objects rather than strings
    df["releasedate"] = pd.to_datetime(df["releasedate"], utc=True)

    # order values chronologically by creation date
    df = df.sort_values(by="releasedate", axis=0, ascending=True)

    # variable to slice on to handle weekly period edge case
    period_slice = None
    if interval == "W":
        # this is to slice the extra period information that comes with the weekly case
        period_slice = 10

    # --data frames for PR created, or closed. Detailed description applies for all 3.--

    # get the count of created prs in the desired interval in pandas period format, sort index to order entries
    #created_range = df["created"].dt.to_period(interval).value_counts().sort_index()

    # converts to data frame object and created date column from period values
    #df_created = created_range.to_frame().reset_index().rename(columns={"index": "Date"})
    
    # converts date column to a datetime object, converts to string first to handle period information
    # the period slice is to handle weekly corner case
    #df_created["Date"] = pd.to_datetime(df_created["Date"].astype(str).str[:period_slice])
    release_range = df["releasedate"].dt.to_period(interval).value_counts().sort_index()
    df_release = release_range.to_frame().reset_index().rename(columns={"index": "Date"})
    df_release["Date"] = pd.to_datetime(df_release["Date"].astype(str).str[:period_slice])
    # df for closed prs in time interval
    #closed_range = pd.to_datetime(df["closed"]).dt.to_period(interval).value_counts().sort_index()
    #f_closed = closed_range.to_frame().reset_index().rename(columns={"index": "Date"})
    #df_closed["Date"] = pd.to_datetime(df_closed["Date"].astype(str).str[:period_slice])

    

    # formatting for graph generation
    if interval == "M":
        df_release["Date"] = df_release["Date"].dt.strftime("%Y-%m-01")
    elif interval == "Y":
        df_release["Date"] = df_release["Date"].dt.strftime("%Y-01-01")


    # ----- Open PR processinging starts here ----

    # first and last elements of the dataframe are the
    # earliest and latest events respectively
    #earliest = df["created"].min()
    #latest = max(df["created"].max(), df["closed"].max())

    # beginning to the end of time by the specified interval
    #dates = pd.date_range(start=earliest, end=latest, freq=interval, inclusive="both")

    # df for open prs from time interval
    #df_open = dates.to_frame(index=False, name="Date")

    # aplies function to get the amount of open prs for each day
    #df_open["Open"] = df_open.apply(lambda row: get_open(df, row.Date), axis=1)

    #df_open["Date"] = df_open["Date"].dt.strftime("%Y-%m-%d")

    #df_ratio = dates.to_frame(index=False, name="Date")
    #df_ratio["closed"] = df_closed["closed"]
    #df_ratio["Ratio"] = df_ratio.apply(lambda row: get_ratio(df, row.closed, row.Date), axis=1)
    #df_ratio["Date"] = df_ratio["Date"].dt.strftime("%Y-%m-%d")
    return df_release



def create_figure(
    df_release: pd.DataFrame,
    interval,
):
    # time values for graph
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph generation
    fig = go.Figure()
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )
    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Release",
        bargroupgap=0.1,
        margin_b=40,
        font=dict(size=14),
    )
    fig.add_trace(
        go.Scatter(
            x=df_release["Date"],
            y=np.ones(df_release.shape[0]),
            mode="markers",
            marker=dict(color=color_seq[5]),
            name="Releases",
            hovertemplate="Release Count: %{y}<br>%{x|%b %d, %Y} <extra></extra>",
        )
    )

    return fig

