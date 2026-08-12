import marimo

__generated_with = "0.23.16"
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

        LOAD AWS;

        CREATE OR REPLACE SECRET secret (TYPE s3, PROVIDER credential_chain);

        ATTACH 's3://mbta-ctd-dataplatform-archive/lamp/catalog.db' AS lamp;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- This query shows all of the values that pull-out inspectors have entered for a trip
        CREATE TABLE car_trips AS (
            SELECT
                gtu."data.tripUpdates.cars" cars,
                gtu."data.tripUpdates.tripKey.tripId" trip_id
            FROM
                lamp.main.trip_updates gtu
            WHERE
                gtu."data.tripUpdates.cars" LIKE '%3869%'
                AND gtu."data.tripUpdates.tripKey.serviceDate" = '2026-08-04'
        );

        CREATE TABLE all_consist_values AS SELECT
            trip_id,
            (
                SELECT
                    GROUP_CONCAT("data.tripUpdates.cars"),
                FROM
                    lamp.main.trip_updates
                WHERE
                    "data.tripUpdates.tripKey.serviceDate" = '2026-08-04'
                    AND "data.tripUpdates.tripKey.tripId" = trip_id
                GROUP BY
                    "data.tripUpdates.tripKey.tripId"
            ) cars
        FROM
            car_trips
        GROUP BY
            trip_id
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Get the number of 1 car, 2 car, and 3 car consists on the Green Line
        CREATE TABLE consist_types_by_day_1_year AS SELECT
            COUNT(*),
            LENGTH("vehicle.multi_carriage_details"),
            MAKE_DATE(year, month, day)
        FROM
            lamp.main.read_ymd (
                'RT_VEHICLE_POSITIONS',
                make_date(2025, 8, 11),
                make_date(2026, 8, 11)
            )
        WHERE
            "vehicle.multi_carriage_details" IS NOT NULL
            AND "vehicle.trip.route_id" LIKE 'Green-%'
        GROUP BY
            make_date(year, month, day),
            LENGTH("vehicle.multi_carriage_details")
        """
    )
    return


@app.cell
def _(consist_types_by_day_1_year, mo):
    _df = mo.sql(
        f"""
        COPY consist_types_by_day_1_year TO '~/Documents/consist_types_by_day_1_year.csv';
        """
    )
    return


@app.cell
def _(consist_types_by_day_1_year, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM consist_types_by_day_1_year
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Get the number of 1 car, 2 car, and 3 car consists on the Green Line
        SELECT
            TO_TIMESTAMP(feed_timestamp),
            *
        FROM
            lamp.main.read_ymd (
                'RT_TRIP_UPDATES',
                make_date(2025, 9, 2),
                make_date(2025, 9, 5)
            )
        WHERE
            "trip_update.trip.trip_id" = 'ADDED-1583064016'
        """
    )
    return


if __name__ == "__main__":
    app.run()
