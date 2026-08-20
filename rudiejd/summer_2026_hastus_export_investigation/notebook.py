import marimo

__generated_with = "0.24.0"
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
        CREATE TABLE hastus_trips AS SELECT * FROM READ_CSV('~/hack/2026-Fall-vehicle-v1/all_trips.txt');
        CREATE TABLE hastus_stop_times AS SELECT * FROM READ_CSV('~/hack/2026-Fall-vehicle-v1/all_stop_times.txt', sample_size=-1);
        """
    )
    return


@app.cell
def _():
    return


@app.cell
def _(hastus_stop_times, hastus_trips, mo):
    _df = mo.sql(
        f"""
        SELECT
            t.trip_id, shape_id, via_variant
        FROM
            hastus_trips t
        INNER JOIN hastus_stop_times stu ON stu.trip_id = t.trip_id
        WHERE
            route_id LIKE '714%' AND stu.stop_id = 12000;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE TABLE hastus_calendar AS SELECT * FROM read_csv('~/hack/2026-Fall-vehicle-v1/all_calendar.txt')
        """
    )
    return


@app.cell
def _(hastus_calendar, hastus_trips, mo):
    _df = mo.sql(
        f"""
        SELECT
            t.*
        from
            hastus_calendar c
            join hastus_trips t ON t.service_id = c.service_id
        WHERE
            c.service_id like 'BUS20264-sbc46w16%';
        """
    )
    return


if __name__ == "__main__":
    app.run()
