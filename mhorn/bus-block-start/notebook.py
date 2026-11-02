import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")

with app.setup(hide_code=True):
    import datetime
    import math

    import altair as alt
    import marimo as mo
    import polars as pl

    mo.sql("""
    INSTALL AWS;

    LOAD ICU;

    LOAD AWS;

    CREATE OR REPLACE SECRET secret (TYPE s3, PROVIDER credential_chain);

    ATTACH 's3://mbta-ctd-dataplatform-archive/lamp/catalog.db' AS lamp;
    """, output=False)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Inputs
    """)
    return


@app.cell(hide_code=True)
def _():
    def _():
        today = datetime.date.today()
        this_month_start = today.replace(day=1)
        last_month_end = this_month_start - datetime.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        date_range = mo.ui.date_range(
            start=datetime.date(2023, 12, 19),
            stop=today,
            value=(last_month_start, last_month_end),
            label="Dates to Evaluate",
        )
        return date_range

    date_range = _()
    date_range
    return (date_range,)


@app.cell(hide_code=True)
def _(date_range):
    start_date, _last_date = date_range.value
    assert start_date.year == _last_date.year
    end_date = _last_date + datetime.timedelta(days=1)
    return end_date, start_date


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Abstractions
    """)
    return


@app.cell(hide_code=True)
def _():
    _df = mo.sql(
        f"""
        CREATE OR REPLACE MACRO vehicle_id_is_bus (vehicle_id STRING) AS NOT REGEXP_FULL_MATCH(
            vehicle_id,
            '\d\d\d\d|G-\d+|[ORB]-[0-9A-F]+|[A-Z ]+'
        );
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _():
    _df = mo.sql(
        f"""
        CREATE OR REPLACE MACRO total_seconds (i INTERVAL) AS hour(i) * 60 * 60 + minute(i) * 60 + second(i);
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _():
    _df = mo.sql(
        f"""
        CREATE OR REPLACE MACRO parse_gtfs_time (t TEXT) AS INTERVAL(SUBSTRING(t, 1, 2)) HOURS + INTERVAL(SUBSTRING(t, 4, 2)) MINUTES + INTERVAL(SUBSTRING(t, 7, 2)) SECONDS;
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(end_date, start_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE VIEW vehicle_positions AS
        SELECT
            vehicle_trip_start_date AS trip_start_date,
            vehicle_trip_trip_id AS trip_id,
            vehicle_current_stop_sequence AS stop_sequence,
            vehicle_stop_id AS stop_id,
            vehicle_current_status AS current_status,
            vehicle_vehicle_id AS vehicle_id,
            to_timestamp(vehicle_timestamp) AS vehicle_timestamp,
            to_timestamp(feed_timestamp) AS feed_timestamp
        FROM
            lamp.read_ymd (
                "RT_VEHICLE_POSITIONS",
                DATE '{start_date}',
                DATE '{end_date}'
            )
        WHERE
            vehicle_trip_revenue = True AND vehicle_id_is_bus(vehicle_id);
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(end_date, start_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE VIEW trip_predictions AS
        SELECT
            STRPTIME(trip_update_trip_start_date::TEXT, '%Y%m%d') AS service_date,
            trip_update_trip_trip_id AS trip_id,
            trip_update_vehicle_id AS vehicle_id,
            trip_update_trip_route_id AS route_id,
            trip_update_stop_time_update_stop_sequence AS stop_sequence,
            trip_update_stop_time_update_stop_id AS stop_id,
            to_timestamp(stop_time_update_arrival_time) AS arrival_time,
            to_timestamp(stop_time_update_departure_time) AS departure_time,
            to_timestamp(trip_update_timestamp) AS trip_timestamp,
            to_timestamp(feed_timestamp) AS feed_timestamp
        FROM
            lamp.read_ymd (
                "RT_TRIP_UPDATES",
                DATE '{start_date}',
                DATE '{end_date}'
            )
        WHERE
            trip_update_trip_revenue = True
            AND trip_update_stop_time_update_schedule_relationship IS NULL
            AND route_id NOT LIKE 'CR-%'
            AND route_id NOT LIKE 'Boat-%'
            AND route_id NOT LIKE 'Green-%'
            AND route_id NOT IN ('Red', 'Blue', 'Orange', 'Mattapan');
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(end_date, start_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE routes AS
        SELECT
            *
        FROM
            READ_PARQUET(
                'https://performancedata.mbta.com/lamp/gtfs_archive/{start_date.year}/routes.parquet'
            )
        WHERE
            gtfs_active_date <= STRFTIME('{start_date}'::date, '%Y%m%d')::int
            AND gtfs_end_date >= STRFTIME('{end_date}'::date, '%Y%m%d')::int
            AND route_type = 3
            AND route_id NOT LIKE 'Shuttle%';
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(end_date, routes, start_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE trips AS
        SELECT
            *
        FROM
            READ_PARQUET(
                'https://performancedata.mbta.com/lamp/gtfs_archive/{start_date.year}/trips.parquet'
            )
        WHERE
            gtfs_active_date <= STRFTIME('{start_date}'::date, '%Y%m%d')::int
            AND gtfs_end_date >= STRFTIME('{end_date}'::date, '%Y%m%d')::int
            AND route_id IN (SELECT route_id FROM routes);
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(end_date, start_date, trips):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE stop_times AS
        SELECT
            *
        FROM
            READ_PARQUET(
                'https://performancedata.mbta.com/lamp/gtfs_archive/{start_date.year}/stop_times.parquet'
            )
        WHERE
            gtfs_active_date <= STRFTIME('{start_date}'::date, '%Y%m%d')::int
            AND gtfs_end_date >= STRFTIME('{end_date}'::date, '%Y%m%d')::int
            AND trip_id IN (SELECT trip_id FROM trips);
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(end_date, start_date, trips):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE service_dates AS
        SELECT
            service_id,
            range::DATE AS service_date,
        FROM
            READ_PARQUET(
                'https://performancedata.mbta.com/lamp/gtfs_archive/{start_date.year}/calendar.parquet'
            ) AS calendar
            CROSS JOIN range(
                STRPTIME(start_date::TEXT, '%Y%m%d')::DATE,
                STRPTIME(end_date::TEXT, '%Y%m%d')::DATE,
                INTERVAL '1' DAY
            )
        WHERE
            service_date >= DATE '{start_date}'
            AND service_date < DATE '{end_date}'
            AND STRPTIME(gtfs_active_date::TEXT, '%Y%m%d')::DATE <= service_date
            AND STRPTIME(gtfs_end_date::TEXT, '%Y%m%d')::DATE >= service_date
            AND service_id IN (
                SELECT
                    service_id
                FROM
                    trips
            )
            AND (
                CASE
                    WHEN dayname(range) = 'Sunday' THEN sunday
                    WHEN dayname(range) = 'Monday' THEN monday
                    WHEN dayname(range) = 'Tuesday' THEN tuesday
                    WHEN dayname(range) = 'Wednesday' THEN wednesday
                    WHEN dayname(range) = 'Thursday' THEN thursday
                    WHEN dayname(range) = 'Friday' THEN friday
                    WHEN dayname(range) = 'Saturday' THEN saturday
                END
            ) = 1
        EXCEPT
        SELECT
            service_id,
            STRPTIME(date::TEXT, '%Y%m%d')::DATE AS service_date
        FROM
            'https://performancedata.mbta.com/lamp/gtfs_archive/{start_date.year}/calendar_dates.parquet'
        WHERE
            exception_type = 2
            AND gtfs_active_date <= date
            AND gtfs_end_date >= date
            AND service_date >= DATE '{start_date}'
            AND service_date < DATE '{end_date}'
        UNION
        SELECT
            service_id,
            STRPTIME(date::TEXT, '%Y%m%d')::DATE AS service_date
        FROM
            'https://performancedata.mbta.com/lamp/gtfs_archive/{start_date.year}/calendar_dates.parquet'
        WHERE
            exception_type = 1
            AND gtfs_active_date <= date
            AND gtfs_end_date >= date
            AND service_date >= DATE '{start_date}'
            AND service_date < DATE '{end_date}';
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(service_dates, stop_times, trips):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE block_starts AS
        SELECT
            block_id,
            service_date,
            arg_min(
                stop_times.trip_id,
                coalesce(arrival_time, departure_time)
            ) AS trip_id,
            min(coalesce(arrival_time, departure_time)) AS block_start_time,
            service_date::TIMESTAMP AT TIME ZONE 'America/New_York' + parse_gtfs_time (min(coalesce(arrival_time, departure_time))) AS block_start_datetime,
            arg_min(stop_id, coalesce(arrival_time, departure_time)) AS stop_id,
            arg_min(
                stop_sequence,
                coalesce(arrival_time, departure_time)
            ) AS stop_sequence,
        FROM
            trips
            NATURAL JOIN service_dates
            JOIN stop_times ON trips.trip_id = stop_times.trip_id
        GROUP BY
            block_id,
            service_date;
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(block_starts, trip_predictions):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE block_start_data AS
        SELECT
            block_starts.*,
            MIN(trip_timestamp) FILTER(vehicle_id IS NULL) AS first_prediction_without_vehicle,
            MAX(trip_timestamp) FILTER(vehicle_id IS NULL) AS last_prediction_without_vehicle,
            MIN(trip_timestamp) FILTER(vehicle_id IS NOT NULL) AS first_prediction_with_vehicle
        FROM
            block_starts
            JOIN trip_predictions USING (service_date, trip_id, stop_sequence)
        GROUP BY ALL;
        """,
        output=False
    )
    return


@app.cell(hide_code=True)
def _(block_start_data):
    block_start_analysis_data = mo.sql(
        f"""
        SELECT
            *,
            total_seconds (
                block_start_datetime - last_prediction_without_vehicle
            ) / 60.0 AS last_without_vehicle_minutes_before_block_start,
            total_seconds (
                block_start_datetime - first_prediction_with_vehicle
            ) / 60.0 AS first_with_vehicle_minutes_before_block_start,
            CASE
                WHEN first_prediction_with_vehicle IS NULL THEN total_seconds (
                    last_prediction_without_vehicle - first_prediction_without_vehicle
                ) / 60.0
                ELSE NULL
            END AS minutes_of_predictions_with_no_vehicle_ever_assigned
        FROM
            block_start_data;
        """,
        output=False
    )
    return (block_start_analysis_data,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Outputs
    """)
    return


@app.cell(hide_code=True)
def _(date_range):
    mo.md(rf"""
    Dates Evaluated: {date_range.value[0]} to {date_range.value[1]}
    """)
    return


@app.cell(hide_code=True)
def _(block_start_analysis_data):
    _df = (
        block_start_analysis_data.with_columns(
            ever_gets_vehicle_assigned=pl.col(
                "first_prediction_with_vehicle"
            ).is_null()
        )
        .group_by(
            pl.col("first_prediction_with_vehicle")
            .is_null()
            .not_()
            .alias("Ever gets vehicle assigned")
        )
        .agg(pl.len().alias("Trips"))
    )
    _chart = (
        alt.Chart(_df)
        .mark_arc()
        .encode(
            color=alt.Color(field="Ever gets vehicle assigned", type='nominal'),
            theta=alt.Theta(field="Trips", type="quantitative"),
            tooltip=[
                alt.Tooltip(field="Ever gets vehicle assigned"),
                alt.Tooltip(field="Trips"),
                alt.Tooltip(field="Percent", format=".1%"),
            ],
        )
        .transform_joinaggregate(total="sum(Trips)")
        .transform_calculate(Percent=alt.datum.Trips / alt.datum.total)
        .properties(
            height=400, width="container", config={"axis": {"grid": False}}
        )
    )
    _chart
    return


@app.cell(hide_code=True)
def _(block_start_analysis_data):
    _col = block_start_analysis_data["first_with_vehicle_minutes_before_block_start"]
    _df = _col.hist(bins=[float(x) for x in range(int(_col.floor().min()), int(_col.ceil().max()) + 1, 1)])
    _chart = (
        alt.Chart(_df)
        .mark_bar()
        .encode(
            x=alt.X(
                field="breakpoint",
                type="quantitative",
                title="Minutes before block start that vehicle was assigned"
            ),
            y=alt.Y(field="count", type="quantitative", title="Trips"),
            tooltip=[
                alt.Tooltip(
                    field="category",
                    title="Minutes before block start that vehicle was assigned"
                ),
                alt.Tooltip(field="count", title="Trips"),
            ],
        )
        .properties(
            height=400, width="container", config={"axis": {"grid": False}}
        )
    )
    _chart
    return


@app.cell(hide_code=True)
def _(block_start_analysis_data):
    _col = block_start_analysis_data["minutes_of_predictions_with_no_vehicle_ever_assigned"]
    _df = _col.hist(bins=[float(x) for x in range(int(_col.floor().min()), int(_col.ceil().max()) + 1, 1)])
    _chart = (
        alt.Chart(_df)
        .mark_bar()
        .encode(
            x=alt.X(
                field="breakpoint",
                type="quantitative",
                title="Minutes of predictions where no vehicle was ever later assigned"
            ),
            y=alt.Y(field="count", type="quantitative", title="Trips"),
            tooltip=[
                alt.Tooltip(
                    field="category",
                    title="Minutes of predictions where no vehicle was ever later assigned"
                ),
                alt.Tooltip(field="count", title="Trips"),
            ],
        )
        .properties(
            height=400, width="container", config={"axis": {"grid": True}}
        )
    )
    _chart
    return


if __name__ == "__main__":
    app.run()
