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
from queries.pr_response_query  import pr_response_query as prrq
from queries.prs_query          import prs_query    as prsq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time
import datetime as dt

PAGE = "community_health"
VIZ_ID = "change_request_review_count"

change_request_review_count = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Change Request Comment Count",
                    id=f"Change Request Comment Count",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """This metric shows on average how many comments each pull request recieves.\n
                            https://chaoss.community/kb/metric-change-request-reviews/
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
                dbc.Form( [
                    dbc.Row( [
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
                    ])
                ] )
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
    #Input(f"top-k-contributors-{PAGE}-{VIZ_ID}", "value"),
    Input(f"action-type-{PAGE}-{VIZ_ID}", "value"),
)
def graph_title(action_type):
    title = f"Average number of comments to change"
    return title


# callback for contrib-importance graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        # Input(f"action-type-{PAGE}-{VIZ_ID}", "value"),
        # Input(f"top-k-contributors-{PAGE}-{VIZ_ID}", "value"),
        # Input(f"patterns-{PAGE}-{VIZ_ID}", "value"),
        # Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "start_date"),
        # Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "end_date"),
    ],
    background=True,
)
def avg_comments_per_pr(repolist):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df1 = cache.grabm(func=prsq, repos=repolist)
    df2 = cache.grabm(func=prrq, repos=repolist)
    while df1 is None or df2 is None:
        time.sleep(1.0)
        df1 = cache.grabm(func=prsq, repos=repolist)
        df2 = cache.grabm(func=prrq, repos=repolist)

    start = time.perf_counter()
    logging.warning(f"{VIZ_ID}- START")
    # test if there is data
    if df1.empty or df2.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return nodata_graph, False
    # function for all data pre processing
    df = process_data(df1,df2)

    fig = create_figure(df)

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    return fig


def process_data(df1: pd.DataFrame, df2: pd.DataFrame,):

    # # Get the first response
    # df1_sorted = df1.sort_values(by=['msg_timestamp'], ascending=False).groupby('pull_request_id').first().reset_index()

    # # Merge dataframes on 'pull_request_id'
    # merged_df = pd.merge(df1_sorted, df2, how='inner', left_on='pull_request_id', right_on='pull_request')

    # # Calculate the time difference in hours
    # merged_df['time_difference_hours'] = (merged_df['msg_timestamp'] - merged_df['created']).dt.total_seconds() / 3600

    # # Group by the month of creation and calculate the average time difference
    # result_df = merged_df.groupby(merged_df['created'].dt.to_period("M"))['time_difference_hours'].mean().reset_index()

    # # Rename the columns for clarity
    # result_df.columns = ['Month', 'Average_Time_Difference_Hours']
    # result_df['Month'] = result_df['Month'].dt.to_timestamp()
    # result_df = result_df[result_df['Month'].dt.strftime('%Y-%m') != '2013-07']
    df1.rename(columns={'pull_request': 'pull_request_id'}, inplace=True)
    comment_count_per_pr = df2.groupby('pull_request_id')['msg_timestamp'].count().reset_index()
    comment_count_per_pr.rename(columns={'msg_timestamp': 'avg_comments_per_pr'}, inplace=True)
    merged_df = pd.merge(df1, comment_count_per_pr, on='pull_request_id', how='left')

    merged_df['created_month'] = pd.to_datetime(merged_df['created']).dt.to_period('M')
    

    result_df = merged_df.groupby('created_month')['avg_comments_per_pr'].mean().reset_index()
    result_df['created_month'] = result_df['created_month'].dt.to_timestamp()
    
    return result_df


def create_figure(df: pd.DataFrame):
    # create plotly express pie chart
    fig = px.line(
        df,
        x="created_month",
        y="avg_comments_per_pr",
        color_discrete_sequence=color_seq
    )

    fig.add_trace(
        go.Scatter(
            x=df["created_month"],
            y=df["avg_comments_per_pr"],
            mode="lines",
            marker=dict(color=color_seq[4]),
            name="Average number of responses to pull request",
        )
    )
    # add legend title
    fig.update_layout(legend_title_text="Average number of responeses")

    return fig