from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash import callback
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from pages.utils.graph_utils import get_graph_time_values, color_seq
from pages.utils.job_utils import nodata_graph
from queries.issue_assignee_query import issue_assignee_query as iq
from cache_manager.cache_manager import CacheManager as cm
import io
import time

PAGE = "community_health"
VIZ_ID = "issue-assignments"

gc_issue_assignments = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Issue Assignments",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Displays how many issues are assigned reviewers during a given period.
                            """
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
        ),
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


# callback for issue assignments graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)
def issues_over_time_graph(repolist, interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=iq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=iq, repos=repolist)

    # data ready.
    start = time.perf_counter()
    logging.warning("ISSUE ASSIGNMENTS - START")

    # test if there is data
    if df.empty:
        logging.warning("ISSUE ASSIGNMENTS - NO DATA AVAILABLE")
        return nodata_graph

    # function for all data pre processing
    df_updated = process_data(df, interval)
    fig = create_figure(df_updated, interval)

    logging.warning(f"ISSUE_ASSIGNMENTS_VIZ - END - {time.perf_counter() - start}")

    return fig


def process_data(df: pd.DataFrame, interval):
    print(list(df.head()))
    # convert to datetime objects rather than strings
    df["assign_date"] = pd.to_datetime(df["assign_date"], utc=True)

    # order values chronologically by creation date
    df = df.sort_values(by="created", axis=0, ascending=True)

    # variable to slice on to handle weekly period edge case
    period_slice = None
    if interval == "W":
        # this is to slice the extra period information that comes with the weekly case
        period_slice = 10


    # df for closed issues in time interval
    closed_range = pd.to_datetime(df["assign_date"]).dt.to_period(interval).value_counts().sort_index()
    df_updated = closed_range.to_frame().reset_index().rename(columns={"index": "Date"})
    df_updated["Date"] = pd.to_datetime(df_updated["Date"].astype(str).str[:period_slice])

    # formatting for graph generation
    if interval == "M":
        df_updated["Date"] = df_updated["Date"].dt.strftime("%Y-%m-01")
    elif interval == "Y":
        df_updated["Date"] = df_updated["Date"].dt.strftime("%Y-01-01")



    return  df_updated


def create_figure(df_updated: pd.DataFrame, interval):
    # time values for graph
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph generation
    fig = go.Figure()
    fig.add_bar(
        x=df_updated["Date"],
        y=df_updated["assign_date"],
        opacity=0.9,
        hovertemplate=hover + "<br>Assigned: %{y}<br>" + "<extra></extra>",
        offsetgroup=1,
        marker=dict(color=color_seq[4]),
        name="Assigned",
    )
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )
    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Number of Issues",
        bargroupgap=0.1,
        margin_b=40,
        font=dict(size=14),
    )

    return fig

