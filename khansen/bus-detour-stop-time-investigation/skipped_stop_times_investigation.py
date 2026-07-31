import marimo

__generated_with = "0.23.15"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb

    return duckdb, mo


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        INSTALL AWS;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        LOAD ICU;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        LOAD aws;

        CREATE OR REPLACE SECRET secret (TYPE s3, PROVIDER credential_chain);

        ATTACH 's3://mbta-ctd-dataplatform-archive/lamp/catalog.db' AS lamp;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE MACRO TO_HUMAN_TIME(unix_timestamp) AS
                	TO_TIMESTAMP(unix_timestamp)::TIMESTAMPTZ AT TIME ZONE 'US/Eastern'
        """
    )
    return


@app.cell
def _(status_code):
    import requests

    routes_response = requests.get("https://api-v3.mbta.com/routes")
    if routes_response.status_code != 200:
        raise f"Received HTTP {status_code} from V3 API when fetching routes"
    json = routes_response.json()
    routes = []
    for route in json["data"]:
        routes.append(route["id"])
    routes
    return (routes,)


@app.cell
def _(mo, routes):
    from datetime import datetime, timezone, timedelta
    yesterday = datetime.now() - timedelta(days=1)
    date_ui = mo.ui.date(label="Service Date", value="2026-07-31")
    range = mo.ui.date_range(start="2026-07-31", stop="2026-07-31")
    route_id_ui = mo.ui.dropdown([''] + routes, label="Route", value="11")
    vehicle_id_ui = mo.ui.text(label="Vehicle ID (blank for any)", value="")
    environment_ui = mo.ui.dropdown(['prod', 'dev-green'], label="LAMP Environment (bus / CR are prod only)", value="prod")
    direction_id_ui = mo.ui.dropdown(['', '0', '1'], label="Direction ID", value="")

    environment_info = {"prod": {"trip_updates": "RT_TRIP_UPDATES", "vehicle_positions": "RT_VEHICLE_POSITIONS"}, "dev-green": {"trip_updates": "DEV_GREEN_RT_TRIP_UPDATES", "vehicle_positions": "RT_VEHICLE_POSITIONS"}}
    return (
        date_ui,
        datetime,
        direction_id_ui,
        environment_info,
        environment_ui,
        route_id_ui,
        timedelta,
        vehicle_id_ui,
    )


@app.cell
def _(date_ui, datetime, mo):
    start_time_ui = mo.ui.datetime(label="Start Time", value=datetime(day=date_ui.value.day, month=date_ui.value.month, year=date_ui.value.year, hour=10))
    end_time_ui = mo.ui.datetime(label="End Time", value=datetime(day=date_ui.value.day, month=date_ui.value.month, year=date_ui.value.year, hour=12))
    return end_time_ui, start_time_ui


@app.cell
def _(
    date_ui,
    datetime,
    end_time_ui,
    environment_info,
    environment_ui,
    mo,
    route_id_ui,
    start_time_ui,
    timedelta,
    vehicle_id_ui,
):
    tu_df = mo.sql(
        f"""
        SELECT
            *,
            TO_HUMAN_TIME(feed_timestamp) as est_time
        FROM
              lamp.read_ymd("{environment_info[environment_ui.value]['trip_updates']}", DATE('{datetime.strftime(date_ui.value, "%Y-%m-%d")}'), DATE('{datetime.strftime(date_ui.value + timedelta(days=1), "%Y-%m-%d")}')) tu
        WHERE
               (LENGTH('{vehicle_id_ui.value}') == 0 OR tu."trip_update.vehicle.id" = '{vehicle_id_ui.value}')
                AND (LENGTH('{route_id_ui.value}') == 0 OR tu."trip_update.trip.route_id" = '{route_id_ui.value}')
                AND HOUR(est_time) >= {start_time_ui.value.hour}
                AND HOUR(est_time) <= {end_time_ui.value.hour}
                AND MINUTE(est_time) >= {start_time_ui.value.minute}
                AND MINUTE(est_time) <= {end_time_ui.value.minute}
        ORDER BY est_time, "trip_update.trip.trip_id", tu."trip_update.stop_time_update.stop_sequence"
        """
    )
    return (tu_df,)


@app.cell
def _(
    date_ui,
    datetime,
    direction_id_ui,
    duckdb,
    end_time_ui,
    environment_info,
    environment_ui,
    route_id_ui,
    start_time_ui,
    timedelta,
    vehicle_id_ui,
):
    vp_df = duckdb.sql(
        f"""
        SELECT
            *,
            TO_HUMAN_TIME(feed_timestamp) AS est_time,
            'est_time - {end_time_ui.value}' < '0 minutes' AS age
        FROM
        lamp.read_ymd("{environment_info[environment_ui.value]['vehicle_positions']}", DATE('{datetime.strftime(date_ui.value, "%Y-%m-%d")}'), DATE('{datetime.strftime(date_ui.value + timedelta(days=1), "%Y-%m-%d")}')) vp
        WHERE
            (LENGTH('{vehicle_id_ui.value}') == 0 OR vp."vehicle.vehicle.id" = '{vehicle_id_ui.value}')
            AND (LENGTH('{route_id_ui.value}') == 0 OR vp."vehicle.trip.route_id" = '{route_id_ui.value}')
            AND (LENGTH('{direction_id_ui.value}') == 0 OR vp."vehicle.trip.direction_id" = '{direction_id_ui.value}')
            AND est_time BETWEEN '{start_time_ui.value}' AND '{end_time_ui.value}'
         ORDER BY est_time
        """
    ).df()
    #vp_df = vp_df.merge(tu_df, how='left', left_on=['vehicle.vehicle.id', "vehicle.stop_id", 'feed_timestamp'], right_on=["trip_update.vehicle.id", "trip_update.stop_time_update.stop_id", "feed_timestamp"])
    vp_df
    return (vp_df,)


@app.cell
def _(
    date_ui,
    direction_id_ui,
    end_time_ui,
    environment_ui,
    mo,
    route_id_ui,
    start_time_ui,
    tu_df,
    vehicle_id_ui,
    vp_df,
):
    import leafmap
    import geopandas as gpd
    import pandas as pd

    plot_df = pd.DataFrame({'vehicle_id': vp_df['vehicle.vehicle.id'], 'direction_id': vp_df["vehicle.trip.direction_id"], 'trip': vp_df['vehicle.trip.trip_id'], 'next_stop_id': vp_df['vehicle.stop_id'], 'time': vp_df['est_time'], 'consist': vp_df["vehicle.vehicle.label"] })

    plot_df = plot_df.astype({'time': 'str'})

    gdf = gpd.GeoDataFrame(plot_df, geometry=gpd.points_from_xy(x=vp_df['vehicle.position.longitude'], y=vp_df['vehicle.position.latitude'], crs="EPSG:4326"))


    m = leafmap.Map(center=(42.361145, -71.057083), zoom=12, height="400px")
    m.add_tile_layer(url="https://cdn.mbta.com/osm_tiles/{z}/{x}/{y}.png", name="MassDOT", attribution="MassDOT")
    if gdf.size != 0:    
        m.add_gdf(gdf, layer_name="vps", )
    mo.vstack([environment_ui, vehicle_id_ui, route_id_ui, direction_id_ui, date_ui, start_time_ui, end_time_ui, m, tu_df])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Problem description

    For skipped stops on bus routes with an active detour in Skate, some stop times in the future are displayed as scheduled instead of skipped. Usually, the first 1-2 stop times are correctly shown as skipped and stop times further out in the future are also correctly skipped.

    ![alt](public/detour_stop_times.png)
    Route 11 bus detoured on 7/31 at 11:07 am at W 6th St @ F St (stop ID: `288`)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Investigation

    Dotcom is displaying these stop times based on the response from the `/predictions` endpoint on the API. For the trip scheduled to stop at stop `288` at 11:51 am (trip ID: `76572754`), the API returns a set of predictions showing stop `288` as skipped:

    ```json
       {
          "attributes": {
            "arrival_time": null,
            "arrival_uncertainty": null,
            "departure_time": null,
            "departure_uncertainty": null,
            "direction_id": 1,
            "last_trip": false,
            "revenue": "REVENUE",
            "schedule_relationship": "SKIPPED",
            "status": null,
            "stop_sequence": 20,
            "trip_headsign": null,
            "update_type": null
          },
          "id": "prediction-76572754-288-20-11",
          "relationships": {
            "route": {
              "data": {
                "id": "11",
                "type": "route"
              }
            },
            "stop": {
              "data": {
                "id": "288",
                "type": "stop"
              }
            },
            "trip": {
              "data": {
                "id": "76572754",
                "type": "trip"
              }
            },
            "vehicle": {
              "data": null
            }
          },
          "type": "prediction"
        }
    ```

    For the trip scheduled to stop at `288` at 12:31 pm (trip id: `76572755`), the `/predictions` endpoint returns an empty response for the entire trip:

    ```json
    {"data":[],"jsonapi":{"version":"1.0"}}
    ```

    I also observedthat once a vehicle is assigned to the trip, the `/predictions` endpoint begins to show the stop as`SKIPPED` for that trip.

    Going one step upstream, the `concentrate` feed, the correctly displayed trip (id: `76572754`) has the following stop time update at 11:07 am indicating a `SKIPPED` stop:

    ```json
      {
        "schedule_relationship": "SKIPPED",
        "stop_sequence": 20,
        "stop_id": "288"
      }
    ```

    Meanwhile, the incorrectly displayed trip (id: `76572755`) had an empty feed at the same time:

    ```json
    {
      "header": {
        "timestamp": "2026-07-31 11:06:59 AM",
        "gtfs_realtime_version": "2.0",
        "incrementality": "FULL_DATASET"
      },
      "entity": []
    }
    ```

    Taking a look at the `bus` feed that comes from Swiftly, both trips have stop time updates for all stops on the trip. The only difference between the two feeds is the assigned vehicle. Trip `76572754` (which is correctly displayed on dotcom) is assigned vehicle id `block_C11-128_schedBasedVehicle` while trip `76572755` is assigned vehicle id `y1781`. For trips further in the future that are displayed as having stop times correctly `SKIPPED`, the vehicle assignment is not present in the `bus` feed.

    **Trip 76572754**
    ```json
    {
      "header": {
        "gtfs_realtime_version": "2.0",
        "incrementality": 0,
        "timestamp": "2026-07-31 11:07:04 AM"
      },
      "entity": [
        {
          "id": "76572754_block_C11-128_schedBasedVehicle_42000",
          "trip_update": {
            "trip": {
              "trip_id": "76572754",
              "start_time": "11:40:00",
              "start_date": "20260731",
              "schedule_relationship": 0,
              "route_id": "11",
              "direction_id": 1
            },
            "stop_time_update": [
              {
                "stop_sequence": 1,
                "arrival": {
                  "time": "2026-07-31 11:40:00 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:40:00 AM",
                  "uncertainty": 300
                },
                "stop_id": "33",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 2,
                "arrival": {
                  "time": "2026-07-31 11:46:37 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:46:37 AM",
                  "uncertainty": 300
                },
                "stop_id": "10033",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 3,
                "arrival": {
                  "time": "2026-07-31 11:47:24 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:47:24 AM",
                  "uncertainty": 300
                },
                "stop_id": "34",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 4,
                "arrival": {
                  "time": "2026-07-31 11:48:01 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:48:01 AM",
                  "uncertainty": 300
                },
                "stop_id": "35",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 5,
                "arrival": {
                  "time": "2026-07-31 11:48:58 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:48:58 AM",
                  "uncertainty": 300
                },
                "stop_id": "295",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 6,
                "arrival": {
                  "time": "2026-07-31 11:49:32 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:49:32 AM",
                  "uncertainty": 300
                },
                "stop_id": "296",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 7,
                "arrival": {
                  "time": "2026-07-31 11:51:02 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:51:02 AM",
                  "uncertainty": 300
                },
                "stop_id": "275",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 8,
                "arrival": {
                  "time": "2026-07-31 11:51:31 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:51:31 AM",
                  "uncertainty": 300
                },
                "stop_id": "277",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 9,
                "arrival": {
                  "time": "2026-07-31 11:51:58 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:51:58 AM",
                  "uncertainty": 300
                },
                "stop_id": "278",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 10,
                "arrival": {
                  "time": "2026-07-31 11:52:50 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:52:50 AM",
                  "uncertainty": 300
                },
                "stop_id": "279",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 11,
                "arrival": {
                  "time": "2026-07-31 11:53:23 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:53:23 AM",
                  "uncertainty": 300
                },
                "stop_id": "280",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 12,
                "arrival": {
                  "time": "2026-07-31 11:53:45 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:53:45 AM",
                  "uncertainty": 300
                },
                "stop_id": "281",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 13,
                "arrival": {
                  "time": "2026-07-31 11:54:41 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:54:41 AM",
                  "uncertainty": 300
                },
                "stop_id": "282",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 14,
                "arrival": {
                  "time": "2026-07-31 11:55:19 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:55:19 AM",
                  "uncertainty": 300
                },
                "stop_id": "283",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 15,
                "arrival": {
                  "time": "2026-07-31 11:55:35 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:55:35 AM",
                  "uncertainty": 300
                },
                "stop_id": "284",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 16,
                "arrival": {
                  "time": "2026-07-31 11:56:13 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:56:13 AM",
                  "uncertainty": 300
                },
                "stop_id": "285",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 17,
                "arrival": {
                  "time": "2026-07-31 11:57:02 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:57:02 AM",
                  "uncertainty": 300
                },
                "stop_id": "286",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 18,
                "arrival": {
                  "time": "2026-07-31 11:58:00 AM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 11:58:00 AM",
                  "uncertainty": 300
                },
                "stop_id": "18",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 19,
                "stop_id": "30287",
                "schedule_relationship": 1
              },
              {
                "stop_sequence": 20,
                "stop_id": "288",
                "schedule_relationship": 1
              },
              {
                "stop_sequence": 21,
                "stop_id": "289",
                "schedule_relationship": 1
              },
              {
                "stop_sequence": 22,
                "stop_id": "290",
                "schedule_relationship": 1
              },
              {
                "stop_sequence": 23,
                "arrival": {
                  "time": "2026-07-31 12:00:27 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:00:27 PM",
                  "uncertainty": 300
                },
                "stop_id": "291",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 24,
                "arrival": {
                  "time": "2026-07-31 12:01:07 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:01:07 PM",
                  "uncertainty": 300
                },
                "stop_id": "292",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 25,
                "arrival": {
                  "time": "2026-07-31 12:01:34 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:01:34 PM",
                  "uncertainty": 300
                },
                "stop_id": "293",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 26,
                "arrival": {
                  "time": "2026-07-31 12:02:23 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:02:23 PM",
                  "uncertainty": 300
                },
                "stop_id": "30294",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 27,
                "arrival": {
                  "time": "2026-07-31 12:03:18 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:03:18 PM",
                  "uncertainty": 300
                },
                "stop_id": "150",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 28,
                "arrival": {
                  "time": "2026-07-31 12:09:59 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:09:59 PM",
                  "uncertainty": 300
                },
                "stop_id": "36538",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 29,
                "arrival": {
                  "time": "2026-07-31 12:11:09 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:11:09 PM",
                  "uncertainty": 300
                },
                "stop_id": "36541",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 30,
                "arrival": {
                  "time": "2026-07-31 12:12:42 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:12:42 PM",
                  "uncertainty": 300
                },
                "stop_id": "15095",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 31,
                "arrival": {
                  "time": "2026-07-31 12:14:54 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:14:54 PM",
                  "uncertainty": 300
                },
                "stop_id": "6565",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 32,
                "arrival": {
                  "time": "2026-07-31 12:17:15 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:17:15 PM",
                  "uncertainty": 300
                },
                "stop_id": "6537",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 33,
                "arrival": {
                  "time": "2026-07-31 12:20:30 PM",
                  "uncertainty": 300
                },
                "departure": {
                  "time": "2026-07-31 12:20:30 PM",
                  "uncertainty": 300
                },
                "stop_id": "16538",
                "schedule_relationship": 0
              }
            ],
            "vehicle": {
              "id": "block_C11-128_schedBasedVehicle"
            },
            "timestamp": "2026-07-31 11:07:04 AM"
          }
        }
      ]
    }
    ```

    **Trip 76572755**
    ```json
    {
      "header": {
        "gtfs_realtime_version": "2.0",
        "incrementality": 0,
        "timestamp": "2026-07-31 11:07:04 AM"
      },
      "entity": [
        {
          "id": "76572755_y1781_44400",
          "trip_update": {
            "trip": {
              "trip_id": "76572755",
              "start_time": "12:20:00",
              "start_date": "20260731",
              "schedule_relationship": 0,
              "route_id": "11",
              "direction_id": 1
            },
            "stop_time_update": [
              {
                "stop_sequence": 1,
                "arrival": {
                  "time": "2026-07-31 12:20:00 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:20:00 PM"
                },
                "stop_id": "33",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 2,
                "arrival": {
                  "time": "2026-07-31 12:20:44 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:20:44 PM"
                },
                "stop_id": "10033",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 3,
                "arrival": {
                  "time": "2026-07-31 12:21:32 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:21:32 PM"
                },
                "stop_id": "34",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 4,
                "arrival": {
                  "time": "2026-07-31 12:22:03 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:22:03 PM"
                },
                "stop_id": "35",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 5,
                "arrival": {
                  "time": "2026-07-31 12:23:08 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:23:08 PM"
                },
                "stop_id": "295",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 6,
                "arrival": {
                  "time": "2026-07-31 12:23:47 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:23:47 PM"
                },
                "stop_id": "296",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 7,
                "arrival": {
                  "time": "2026-07-31 12:25:23 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:25:23 PM"
                },
                "stop_id": "275",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 8,
                "arrival": {
                  "time": "2026-07-31 12:26:03 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:26:03 PM"
                },
                "stop_id": "277",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 9,
                "arrival": {
                  "time": "2026-07-31 12:27:01 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:27:01 PM"
                },
                "stop_id": "278",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 10,
                "arrival": {
                  "time": "2026-07-31 12:28:01 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:28:01 PM"
                },
                "stop_id": "279",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 11,
                "arrival": {
                  "time": "2026-07-31 12:28:37 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:28:37 PM"
                },
                "stop_id": "280",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 12,
                "arrival": {
                  "time": "2026-07-31 12:29:08 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:29:08 PM"
                },
                "stop_id": "281",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 13,
                "arrival": {
                  "time": "2026-07-31 12:30:07 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:30:07 PM"
                },
                "stop_id": "282",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 14,
                "arrival": {
                  "time": "2026-07-31 12:30:29 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:30:29 PM"
                },
                "stop_id": "283",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 15,
                "arrival": {
                  "time": "2026-07-31 12:30:40 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:30:40 PM"
                },
                "stop_id": "284",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 16,
                "arrival": {
                  "time": "2026-07-31 12:31:17 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:31:17 PM"
                },
                "stop_id": "285",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 17,
                "arrival": {
                  "time": "2026-07-31 12:32:22 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:32:22 PM"
                },
                "stop_id": "286",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 18,
                "arrival": {
                  "time": "2026-07-31 12:33:49 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:33:49 PM"
                },
                "stop_id": "18",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 19,
                "stop_id": "30287",
                "schedule_relationship": 1
              },
              {
                "stop_sequence": 20,
                "stop_id": "288",
                "schedule_relationship": 1
              },
              {
                "stop_sequence": 21,
                "stop_id": "289",
                "schedule_relationship": 1
              },
              {
                "stop_sequence": 22,
                "stop_id": "290",
                "schedule_relationship": 1
              },
              {
                "stop_sequence": 23,
                "arrival": {
                  "time": "2026-07-31 12:36:16 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:36:16 PM"
                },
                "stop_id": "291",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 24,
                "arrival": {
                  "time": "2026-07-31 12:36:48 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:36:48 PM"
                },
                "stop_id": "292",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 25,
                "arrival": {
                  "time": "2026-07-31 12:37:15 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:37:15 PM"
                },
                "stop_id": "293",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 26,
                "arrival": {
                  "time": "2026-07-31 12:37:46 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:37:46 PM"
                },
                "stop_id": "30294",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 27,
                "arrival": {
                  "time": "2026-07-31 12:38:44 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:38:44 PM"
                },
                "stop_id": "150",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 28,
                "arrival": {
                  "time": "2026-07-31 12:45:10 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:45:10 PM"
                },
                "stop_id": "36538",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 29,
                "arrival": {
                  "time": "2026-07-31 12:45:58 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:45:58 PM"
                },
                "stop_id": "36541",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 30,
                "arrival": {
                  "time": "2026-07-31 12:46:56 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:46:56 PM"
                },
                "stop_id": "15095",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 31,
                "arrival": {
                  "time": "2026-07-31 12:49:43 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:49:43 PM"
                },
                "stop_id": "6565",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 32,
                "arrival": {
                  "time": "2026-07-31 12:51:59 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:51:59 PM"
                },
                "stop_id": "6537",
                "schedule_relationship": 0
              },
              {
                "stop_sequence": 33,
                "arrival": {
                  "time": "2026-07-31 12:54:33 PM"
                },
                "departure": {
                  "time": "2026-07-31 12:54:33 PM"
                },
                "stop_id": "16538",
                "schedule_relationship": 0
              }
            ],
            "vehicle": {
              "id": "y1781"
            },
            "timestamp": "2026-07-31 11:06:52 AM"
          }
        }
      ]
    }
    ```

    When looking at the trip updates in LAMP for the time period around this example, it seemed strange to me that there are only trip updates each hour and not in between, although all of these trip updates show the stop as `SKIPPED`. Only a handful of them have a vehicle assigned to them. It's possible that because `concentrate` is filtering out stop time updates
    """)
    return


@app.cell
def _(tu_df):
    tu_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Next steps

    I spent a lot of time looking through each filter and group filter in `concentrate` but none of them seem to match the shape of the stop time updates that come in from the bus feed in these scenarios. One theory was that the stop times were getting dropped due to the logic in the `cancelled_trip.ex` group filter that handles bus block waivers, but this doesn't seem to match because the trip isn't being cancelled and there is a test case that has a similar pattern that doesn't trigger the bus block waiver cancellation.

    The only noticeable difference between the two trips' input feeds to concentrate is the vehicle assignment, so it's likely that the issue is related to which vehicle (if any) is being assigned to the trip. In that case, is it possible that this is an issue with how vehicles are being assigned to detoured routes somewhere else, for example in Skate?
    """)
    return


if __name__ == "__main__":
    app.run()
