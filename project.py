import streamlit as st
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium
from streamlit_lottie import st_lottie
from haversine import haversine
import requests
import utility
from folium.plugins import HeatMap, PolyLineTextPath


def main():

    st.title(body="Latest M2+ Earthquakes")
    # Dataframe from USGS
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.csv"
    df = get_dataframe(url)
    # sidebar_df is used for sidebar widgets and not affected by filters
    sidebar_df = df.copy()

    # Creating sidebar
    with st.sidebar:
        # Sidebar animation
        lottie_url = "https://assets7.lottiefiles.com/packages/lf20_kc6thomq.json"
        lottie_json = utility.load_lottieurl(lottie_url)
        st_lottie(lottie_json, speed=1, height=200, key="initial", quality="low")

        # General info about dataset (Quakes magnitude 2 or higher)
        st.markdown(
            "<h3 style='text-align: center; color: firebrick;'>Quakes magnitude 2 or higher</h3>",
            unsafe_allow_html=True,
        )

        sidebar_col0, sidebar_col1 = st.columns(2)
        with sidebar_col0:
            st.info("Last 24 hours")
            st.info("Last 7 days")
            st.info("Last 30 days")

        with sidebar_col1:
            st.error(f"{len(utility.set_dataset_size(sidebar_df, 1))} Quakes")
            st.error(f"{len(utility.set_dataset_size(sidebar_df, 7))} Quakes")
            st.error(f"{len(utility.set_dataset_size(sidebar_df, 30))} Quakes")

        # About the project
        with st.expander("About"):
            st.markdown(
                """
                This web app is made for **CS50's Introduction to Programming with Python Final Project**. 
                
                It helps users to filter and visualize latest earthquake data that provided by 
                **USGS** (United States Geological Survey).
                """
            )

    # Dataframe filter UI
    df = utility.data_filter(df)

    # Creating ag-Grid table
    selected = utility.create_data_grid(df)

    # Adjusting position of refresh and download buttons
    button_col1, button_col2, button_col3 = st.columns((1.2, 2, 8))

    # Refresh button
    with button_col1:
        refresh_button = st.button(label="Refresh Dataset", help="Resets dataset cache and reruns the entire page")
        if refresh_button:
            st.experimental_memo.clear()
            st.experimental_rerun()

    # Convert current dataframe to csv and add download button for it
    with button_col2:
        csv = utility.convert_to_csv(df)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="filtered_latest_eartquakes.csv",
            mime="text/csv",
        )


    st.text("")

    # TABS for map, graphs and stats
    tab1, tab2, tab3 = st.tabs(
        [
            "INTERACTIVE EARTHQUAKE MAP",
            "3D OUTLINE EARTHQUAKE MAP AND GRAPHS",
            "ANNUAL EARTHQUAKE STATISTICS",
        ]
    )

    with tab1:
        st.markdown(
            """ 
            * Selected row will be shown on the map as a marker if magnitude value is equal to 4.0 or higher.
            * Magnitude value is limited to avoid longer loading times.
            """
            )
        # map_col1 displays the map, map_col2 displays all the other widgets related to the map
        map_col1, map_col2 = st.columns((5, 1.26))

        # Starting with map_col2 because widget changes will be displayed on the map
        with map_col2:

            tiles = utility.map_layer_panel()
            map = utility.draw_world_map(tiles)
            # Heatmap
            if st.checkbox("Show Heatmap", help="Dataframe filter changes will change results."):

                HeatMap(
                    data=list(
                        zip(df.latitude.values, df.longitude.values, df.mag.values)
                    ),
                    radius=20,
                    min_opacity=0.6,
                    blur=15,
                ).add_to(map)
            # Circle Search
            elif st.checkbox("Perform a circle search", help="Dataframe filter changes will change results."):

                lat, lon, radius = utility.circle_search_panel(map, df)

                st.session_state.location = find_location_by_coordinates(lat, lon)
                # Remove # below to display location information under the circle search panel
                # st.info(f'Center Location: {st.session_state.location}')

                earthquakes_in_radius = []

                # Iterating over rows to check if they are in given radius
                for index, row in df.iterrows():
                    # Calculate the distance between two points on Earth using their latitude and longitude
                    # Distance in kilometers
                    distance = haversine((lat, lon), (row["latitude"], row["longitude"]))

                    if distance <= radius:
                        utility.add_map_marker(
                            map,
                            lat=row["latitude"],
                            lon=row["longitude"],
                            mag=row["mag"],
                            depth=row["depth"],
                            place=row["place"],
                        )

                        earthquakes_in_radius.append(
                            (distance, row["latitude"], row["longitude"])
                        )
                        
                # Adding circle area to the map
                circle_tooltip = f"""<center> <b>{len(earthquakes_in_radius)} earthquakes </b> found in <b> {radius} km </b> radius </center>"""

                folium.Circle(
                    location=[lat, lon],
                    radius=radius * 1000,  # Radius of the circle, in meters by default
                    fill=True,
                    color="firebrick",
                    tooltip=circle_tooltip,
                ).add_to(map)
                # Marking center of circle area
                folium.Marker(
                    location=[lat, lon],
                    popup=f"""<center> <b> Center Location </b> </center> <br> {st.session_state.location}""",
                    icon=folium.Icon(color="red", icon="arrow-down"),
                ).add_to(map)

                if st.checkbox("Show nearest earthquake"):
                    try:
                        min_distance = min(earthquake[0] for earthquake in earthquakes_in_radius)
                    except ValueError:
                        pass

                    for earthquake in earthquakes_in_radius:
                        if earthquake[0] == min_distance:   # comparing distances
                            line = folium.PolyLine(
                                [(lat, lon), (earthquake[1], earthquake[2])],
                                color="firebrick",
                                weight=5,
                                opacity=1,
                            ).add_to(map)

                            attr = {
                                "fill": "firebrick",
                                "font-weight": "bold",
                                "font-size": "15",
                            }

                            PolyLineTextPath(
                                line,
                                text=f"Nearest ⮞ {round(earthquake[0])} km",
                                center=True,
                                offset=15,
                                attributes=attr,
                            ).add_to(map)
                # Nearest and Furthest eartquakes
                if (
                    st.checkbox("Show furthest earthquake")
                    and len(earthquakes_in_radius) > 1
                ):
                    try:
                        max_distance = max(earthquake[0] for earthquake in earthquakes_in_radius)
                    except ValueError:
                        pass

                    for earthquake in earthquakes_in_radius:
                        if earthquake[0] == max_distance:
                            line = folium.PolyLine(
                                [(lat, lon), (earthquake[1], earthquake[2])],
                                color="royalblue",
                                weight=5,
                                opacity=1,
                            ).add_to(map)

                            attr = {
                                "fill": "royalblue",
                                "font-weight": "bold",
                                "font-size": "15",
                            }

                            PolyLineTextPath(
                                line,
                                f"Furthest ⮞ {round(earthquake[0])} km",
                                center=True,
                                offset=15,
                                attributes=attr,
                            ).add_to(map)
            # Showing selected markers if other two options(heatmap and circle search) are not active
            elif len(selected) > 0:

                for i in range(len(selected)):
                    if selected[i]["mag"] >= 4:
                        utility.add_map_marker(
                            map,
                            lat=selected[i]["latitude"],
                            lon=selected[i]["longitude"],
                            mag=selected[i]["mag"],
                            depth=selected[i]["depth"],
                            place=selected[i]["place"],
                        )

        with map_col1:
            # Updating the map on streamlit
            st_folium(map, width=1140, height=640)

    with tab2:

        tab2_col1, tab2_col2 = st.columns(2)
        with tab2_col1:
            st.write("")
            # 3D Outline map
            utility.create_scattergeo_map(
                lat=df["latitude"].tolist(),
                lon=df["longitude"].tolist(),
                hovertext=df["place"].tolist(),
            )

        with tab2_col2:
            st.write("")
            st.markdown(
                "<h6 style='text-align: center; color: firebrick;'>Hourly distribution of the number of earthquakes (Magnitude 2 or higher)</h6>",
                unsafe_allow_html=True,
            )

            if len(df) > 0:
                hours_str = ["%.2d" % i for i in range(24)]
                x_axis_label = [x + ":00 - " + x + ":59" for x in hours_str]
                # Creating a list of the number of earthquakes that occured in each hour
                hourly_eartquake_count = [
                    len(
                        df.loc[
                            df["time (UTC)"].astype("datetime64").dt.hour == hour
                        ].index
                    )
                    for hour in range(24)
                ]

                chart_data1 = pd.DataFrame(
                    {
                        "Time Period": x_axis_label,
                        "Number of Events": hourly_eartquake_count,
                    }
                )

                utility.create_hourly_distribution_bar_chart(
                    df=chart_data1, x_axis="Time Period", y_axis="Number of Events"
                )

            else:
                st.warning("There are no values to show")

            st.markdown(
                "<h6 style='text-align: center; color: firebrick;'>Histogram of all the earthquakes in terms of magnitude (Magnitude 2 or higher)</h6>",
                unsafe_allow_html=True,
            )

            if len(df) > 0:
                magnitudes = sorted(df["mag"].unique())
                # Creating a list of the number of events for each magnitude value
                events = [len(df.loc[df["mag"] == mag]) for mag in magnitudes]

                chart_data2 = pd.DataFrame({"Magnitude": magnitudes, "Number of Events": events})

                utility.create_magnitude_bar_chart(
                    df=chart_data2, x_axis="Magnitude", y_axis="Number of Events"
                )
            else:
                st.warning("There are no values to show")

    with tab3:
        tab3_col1, tab3_col2, tab3_col3 = st.columns((1, 2, 1))

        with tab3_col2:

            st.markdown(
                "<h5 style='text-align: center; color: firebrick;'>Number of Earthquakes per Year</h5>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h6 style='text-align: center; color: firebrick;'>Magnitude 5 or higher</h6>",
                unsafe_allow_html=True,
            )

            year = st.selectbox(
                label="Choose time period",
                options=["2000-2021", "1990-1999"],
            )

            magnitude = st.radio(
                label="Choose magnitude range",
                options=["All", "5–5.9", "6–6.9", "7–7.9", "8.0+"],
                horizontal=True,
            )

            url = "https://www.usgs.gov/programs/earthquake-hazards/lists-maps-and-statistics"
            df_list = get_worldwide_earthquakes_chart_data(url)
            # There are 5 dataframes in df_list. df[0] and df[2] will be used.
            # .drop(4) will drop 'estimated deaths' row
            raw_data = df_list[0 if year == "2000-2021" else 2].drop(4)
            raw_data = raw_data.set_index("Magnitude")
            raw_data = raw_data.astype(int)
            raw_data.loc["All"] = raw_data.sum(axis=0)

            # Using transpose of the array as chart data
            chart_data = raw_data.T
            chart_data.rename(columns={chart_data.columns[0]: "8.0+"}, inplace=True, errors="raise")
            chart_data = pd.DataFrame(
                {
                    "Years": chart_data.index,
                    "Number of Events": chart_data[magnitude].tolist(),
                }
            )

            utility.create_worldwide_earthquakes_bar_chart(
                df=chart_data, x_axis="Years", y_axis="Number of Events"
            )

            with st.expander("Show raw data and source for this graph"):
                st.dataframe(raw_data)

                csv = utility.convert_to_csv(raw_data)
                st.download_button(
                    label="Download raw data as CSV",
                    data=csv,
                    file_name=f"earthquakes_{year}.csv",
                    mime="text/csv",
                )
                # Given data source
                st.write(
                    "**Data Source:** [usgs.gov](https://www.usgs.gov/programs/earthquake-hazards/lists-maps-and-statistics)"
                )


# st.experimental_memo is a function decorator to memoize function executions
# This will improve overall performance (alternative to st.cache)
@st.experimental_memo
def get_dataframe(url: str) -> pd.DataFrame:
    """Read csv file from given url and return dataframe after working on some columns"""
    
    filters = [
        "time",
        "latitude",
        "longitude",
        "depth",
        "mag",
        "magType",
        "place",
        "type",
        "locationSource",
        "magSource",
        "status",
    ]
    
    df = pd.read_csv(url, usecols=filters)
    df = df.dropna().reset_index(drop=True)
    # Ignoring below magnitude 2 rows in dataframe
    df = df.loc[df["mag"] >= 2]
    df["mag"] = df["mag"].round(1)
    df["depth"] = df["depth"].round(4)
    df.rename(columns={"time": "time (UTC)"}, inplace=True, errors="raise")
    # Resetting index after dropping nan and less than magnitude 2 values
    df.index = df.index.factorize()[0]
    return df


@st.experimental_memo
def get_worldwide_earthquakes_chart_data(url: str) -> list[pd.DataFrame]:
    """Returns list of dataframes from given url"""

    html = requests.get(url).content
    df_list = pd.read_html(html)

    return df_list


def find_location_by_coordinates(lat: float, lon: float):
    """Returns location information of given latitude and longitude using Nomatim API."""

    geolocator = Nominatim(user_agent="geoapiExercises")
    location = geolocator.reverse((f"{lat},{lon}"), language="en")
    if location is None:
        location = "Unknown"

    return location


if __name__ == "__main__":

    PROJECT_TITLE = "Latest Earthquakes"
    st.set_page_config(
        page_title=PROJECT_TITLE,
        initial_sidebar_state="expanded",
        layout="wide",
    )

    # Changing expander background color
    st.markdown(
        """
    <style>
    .streamlit-expanderHeader {
    #   font-weight: bold;
        background: #E8DFDF;
        font-size: 15px;
    }
    .streamlit-expanderContent {
    #   font-weight: bold;
        background: #E8DFDF;
        font-size: 15px;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Initiating session state for location information
    if "location" not in st.session_state:
        st.session_state.location = None

    main()
