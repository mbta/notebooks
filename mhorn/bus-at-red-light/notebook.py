import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")

with app.setup(hide_code=True):
    import datetime

    import altair as alt
    import marimo as mo
    import polars as pl

    mo.sql("""
    INSTALL AWS;

    LOAD ICU;

    LOAD AWS;

    CREATE OR REPLACE SECRET secret (TYPE s3, PROVIDER credential_chain);

    ATTACH 's3://mbta-ctd-dataplatform-archive/lamp/catalog.db' AS lamp;
    """)


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

        date_range = mo.ui.date_range(
            start=datetime.date(2023, 12, 19),
            stop=today,
            value=(today - datetime.timedelta(days=1), today),
            label="Dates to Evaluate",
        )
        return date_range

    date_range = _()
    date_range
    return (date_range,)


@app.cell(hide_code=True)
def _(date_range):
    start_date, _last_date = date_range.value
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
        """
    )
    return


@app.cell(hide_code=True)
def _():
    _df = mo.sql(
        f"""
        CREATE OR REPLACE MACRO total_seconds (i INTERVAL) AS hour(i) * 60 * 60 + minute(i) * 60 + second(i);
        """
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
        """
    )
    return


@app.cell(hide_code=True)
def _(vehicle_positions):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE VIEW first_vehicle_positions AS
        SELECT
            vehicle_positions.*
        FROM
            vehicle_positions
            NATURAL JOIN (
                SELECT
                    trip_start_date,
                    trip_id,
                    stop_sequence,
                    stop_id,
                    min(feed_timestamp) AS feed_timestamp
                FROM
                    vehicle_positions
                GROUP BY ALL
            );
        """
    )
    return


@app.cell(hide_code=True)
def _(end_date, start_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE VIEW trip_predictions AS
        SELECT
            trip_update_trip_start_date AS trip_start_date,
            trip_update_trip_trip_id AS trip_id,
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
            AND trip_update_stop_time_update_schedule_relationship IS NULL;
        """
    )
    return


@app.cell(hide_code=True)
def _(trip_predictions):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE VIEW last_trip_predictions AS
        SELECT
            trip_predictions.*
        FROM
            trip_predictions
            NATURAL JOIN (
                SELECT
                    trip_start_date,
                    trip_id,
                    stop_sequence,
                    stop_id,
                    max(feed_timestamp) AS feed_timestamp
                FROM
                    trip_predictions
                GROUP BY ALL
            );;
        """
    )
    return


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
def _():
    mo.md(r"""
    How long after the predicted departure time does the vehicle status change to in transit to a different stop?
    """)
    return


@app.cell(hide_code=True)
def _(first_vehicle_positions, last_trip_predictions):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE VIEW predicted_departure_vs_actual_time_past_stop AS
        SELECT
            last_trip_predictions.trip_start_date,
            last_trip_predictions.trip_id,
            last_trip_predictions.stop_sequence AS prediction_stop_sequence,
            last_trip_predictions.stop_id AS prediction_stop_id,
            last_trip_predictions.departure_time AS predicted_departure_time,
            first_vehicle_positions.vehicle_id,
            first_vehicle_positions.stop_sequence AS vehicle_next_stop_sequence,
            first_vehicle_positions.stop_id AS vehicle_next_stop_id,
            first_vehicle_positions.vehicle_timestamp AS actual_time_past_stop,
        FROM
            last_trip_predictions
            ASOF LEFT JOIN first_vehicle_positions ON last_trip_predictions.trip_start_date == first_vehicle_positions.trip_start_date
            AND last_trip_predictions.trip_id == first_vehicle_positions.trip_id
            AND last_trip_predictions.stop_sequence < first_vehicle_positions.stop_sequence
        WHERE
            predicted_departure_time IS NOT NULL;
        """
    )
    return


@app.cell(hide_code=True)
def _(predicted_departure_vs_actual_time_past_stop):
    dwell_seconds_past_prediction = mo.sql(
        f"""
        SELECT
            total_seconds (actual_time_past_stop - predicted_departure_time) AS dwell_seconds_past_prediction
        FROM
            predicted_departure_vs_actual_time_past_stop;
        """,
        output=False,
    )
    return (dwell_seconds_past_prediction,)


@app.cell(hide_code=True)
def _(dwell_seconds_past_prediction):
    def _():
        data = dwell_seconds_past_prediction["dwell_seconds_past_prediction"]
        min, q1, q3, max = data.quantile([0, 0.25, 0.75, 1])
        # https://en.wikipedia.org/wiki/Outlier#Tukey's_fences
        k = 3
        outlier_distance = k * (q3 - q1)
        low_outlier = round(q1 - outlier_distance)
        high_outlier = round(q3 + outlier_distance)
        # we want to flatten the outliers into their least extreme values’ bins
        non_outlier_hist_bins = [
            float(x) + 0.5 for x in range(low_outlier - 1, high_outlier + 1)
        ]
        all_hist_bins = [min, *non_outlier_hist_bins, max]
        hist = data.hist(bins=all_hist_bins)
        # actual value is breakpoint - 0.5
        hist = hist.with_columns(value=pl.col("breakpoint") - 0.5)
        # rewrite the (high_outlier + 0.5, max] bin to point to high_outlier + 1 instead of max
        hist[-1, "value"] = high_outlier + 1
        return hist

    alt.Chart(_()).mark_bar().encode(
        x=alt.X(field="value", type="quantitative").title(
            "Seconds (outliers clamped)"
        ),
        y=alt.Y(field="count", type="quantitative").title("Count"),
        tooltip=[
            alt.Tooltip(field="value", format=",.0f").title("Seconds"),
            alt.Tooltip(field="count", format=",.0f").title("Count"),
        ],
    ).properties(
        height=290, width="container", config={"axis": {"grid": False}}
    )
    return


@app.cell(hide_code=True)
def _(dwell_seconds_past_prediction):
    def _():
        data = dwell_seconds_past_prediction["dwell_seconds_past_prediction"]
        min, q1, q3, max = data.quantile([0, 0.25, 0.75, 1])
        # https://en.wikipedia.org/wiki/Outlier#Tukey's_fences
        k = 3
        outlier_distance = k * (q3 - q1)
        low_outlier = round(q1 - outlier_distance)
        high_outlier = round(q3 + outlier_distance)
        # we want to flatten the outliers into their least extreme values’ bins
        non_outlier_hist_bins = [
            float(x) + 0.5 for x in range(low_outlier - 1, high_outlier + 1)
        ]
        all_hist_bins = [min, *non_outlier_hist_bins, max]
        hist = data.hist(bins=all_hist_bins)
        # actual value is breakpoint - 0.5
        hist = hist.with_columns(value=pl.col("breakpoint") - 0.5)
        # rewrite the (high_outlier + 0.5, max] bin to point to high_outlier + 1 instead of max
        hist[-1, "value"] = high_outlier + 1
        return hist

    alt.Chart(_()).transform_window(
        cumulative_count="sum(count)"
    ).transform_joinaggregate(total_qty="sum(count)").transform_calculate(
        Proportion="datum.cumulative_count/datum.total_qty"
    ).mark_area().encode(
        x=alt.X(field="value", type="quantitative").title("Seconds"),
        y=alt.Y(field="Proportion", type="quantitative").axis(format=".0%"),
        tooltip=[
            alt.Tooltip(field="value", format=",.0f").title("Seconds"),
            alt.Tooltip(field="Proportion", format=".1%"),
        ],
    ).properties(
        height=290,
        width="container",
        config={"axis": {"grid": False}},
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    How often do vehicles ever reach "stopped at" status for their predicted stop?
    """)
    return


@app.cell(hide_code=True)
def _(last_trip_predictions, vehicle_positions):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE VIEW prediction_ever_stopped_at AS
        SELECT
            last_trip_predictions.trip_start_date,
            last_trip_predictions.trip_id,
            last_trip_predictions.stop_sequence,
            vehicle_timestamp IS NOT NULL AS had_stopped_at
        FROM
            last_trip_predictions
            LEFT JOIN vehicle_positions ON last_trip_predictions.trip_start_date = vehicle_positions.trip_start_date
            AND last_trip_predictions.trip_id = vehicle_positions.trip_id
            AND last_trip_predictions.stop_sequence = vehicle_positions.stop_sequence
            AND vehicle_positions.current_status = 'STOPPED_AT';
        """
    )
    return


@app.cell(hide_code=True)
def _(prediction_ever_stopped_at):
    _df = mo.sql(
        f"""
        WITH total AS (SELECT COUNT(*) AS total FROM prediction_ever_stopped_at)
        SELECT
            had_stopped_at,
            COUNT(*) AS count,
            ROUND(COUNT(*) / any_value(total.total) * 100, 1) AS percent
        FROM
            prediction_ever_stopped_at
            CROSS JOIN total
        GROUP BY ALL
            ORDER BY had_stopped_at DESC;
        """
    )
    return


if __name__ == "__main__":
    app.run()
