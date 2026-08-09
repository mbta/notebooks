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


if __name__ == "__main__":
    app.run()
