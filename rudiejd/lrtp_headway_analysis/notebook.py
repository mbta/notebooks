import marimo

__generated_with = "0.23.15"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        INSTALL AWS;

        LOAD ICU;

        LOAD aws;

        CREATE OR REPLACE SECRET secret (TYPE s3, PROVIDER credential_chain);

        ATTACH 's3://mbta-ctd-dataplatform-archive/lamp/catalog.db' AS lamp;
        """
    )
    return


@app.cell
def _(mo):
    gap_df = mo.sql(
        f"""
        CREATE TABLE gaps_every_second AS SELECT
            (
                MIN(
                    tu."trip_update.stop_time_update.departure.time",
                    3
                ) [2] - MIN(
                    tu."trip_update.stop_time_update.departure.time",
                    3
                ) [1]
            ) / 60 AS first_to_second_headway_gap_minutes,
            COUNT(*),
            TO_TIMESTAMP(feed_timestamp) AS feed_timestamp_dt,
            feed_timestamp,
            "trip_update.stop_time_update.stop_id" stop_id
        FROM
            lamp.main.read_ymd (
                'DEV_GREEN_RT_TRIP_UPDATES',
                make_date(2026, 7, 27),
                make_date(2026, 8, 1)
            ) tu
        WHERE
            tu."trip_update.stop_time_update.stop_id" IN ('70503', '70512')
            AND "trip_update.trip.direction_id" = 0
        GROUP BY
            TO_TIMESTAMP(feed_timestamp), feed_timestamp,
            "trip_update.stop_time_update.stop_id"
        """
    )
    return


@app.cell
def _(gaps_every_second, mo):
    _df = mo.sql(
        f"""
        SELECT
            AVG(first_to_second_headway_gap_minutes),
            MAX(first_to_second_headway_gap_minutes),
            MIN(first_to_second_headway_gap_minutes),
            stop_id,
            STRFTIME(feed_timestamp_dt, '%Y-%m-%d %H') AS year_month_day_hour_min
        FROM
            gaps_every_second
        WHERE DAY(feed_timestamp_dt) = 31
        GROUP BY
            year_month_day_hour_min, stop_id
        ORDER BY year_month_day_hour_min
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE TABLE headways_by_time AS
        SELECT
             (MIN(
                tu."trip_update.stop_time_update.departure.time",
                2
            )[1] - feed_timestamp) / 60 AS first_headway,
             (MIN(
                tu."trip_update.stop_time_update.departure.time",
                2
            )[2] - feed_timestamp) / 60 AS second_headway,
            STRFTIME(TO_TIMESTAMP(feed_timestamp), '%Y-%m-%d %H') dt_minutes,
            "trip_update.stop_time_update.stop_id" stop_id
        FROM
            lamp.main.read_ymd (
                'DEV_GREEN_RT_TRIP_UPDATES',
                make_date(2026, 7, 30),
                make_date(2026, 8, 1)
            ) tu
        WHERE
            tu."trip_update.stop_time_update.stop_id" IN ('70503', '70512')
            AND "trip_update.trip.direction_id" = 0
        GROUP BY
            dt_minutes,
            feed_timestamp,
            "trip_update.stop_time_update.stop_id"
        """
    )
    return


@app.cell
def _(headways_by_time, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM headways_by_time
        """
    )
    return


if __name__ == "__main__":
    app.run()
