import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="SF EV Charging Station Optimization", layout="wide")

@st.cache_data
def load_data():
    E = pd.read_csv("existing_stations.csv")
    P = pd.read_csv("demand_points.csv")
    C = pd.read_csv("candidate_points.csv")
    R = pd.read_csv("results_curve.csv")
    ILP_sel = pd.read_csv("ilp_selection.csv")
    GREEDY_sel = pd.read_csv("greedy_selection.csv")
    return E, P, C, R, ILP_sel, GREEDY_sel

E_df, P_df, C_df, df_res, ilp_sel, greedy_sel = load_data()
ilp_sel["type"] = "Recommended (ILP)"
greedy_sel["type"] = "Recommended (Greedy)"
df_res["method"] = df_res["method"].astype(str).str.strip().str.upper()

st.title("EV Charging Station Location Optimization (SF)")

# Sidebar controls
k = st.sidebar.slider("K (# new stations)", min_value=1, max_value=int(df_res["k"].max()), value=5)
method = st.sidebar.selectbox("Method", ["ILP", "GREEDY"])
weight_col = "B01003_001E" if "B01003_001E" in P_df.columns else None
show_reco = st.sidebar.toggle("Show recommended sites (K=5)", value=True)

# KPIs for chosen k/method
sub = df_res[(df_res["k"] == k) & (df_res["method"] == method)]

# Debug: show what's going on (you can remove later)
#st.sidebar.write("Available methods in results:", sorted(df_res["method"].unique()))
#st.sidebar.write("Rows matched:", len(sub))

if sub.empty:
    st.error(f"No results found for k={k}, method={method}. Check results_curve.csv values.")
    st.stop()

row = sub.iloc[0]
st.metric("Added covered population", f'{row["added_pop"]:,.0f}')
st.metric("Added covered demand points", f'{row["added_pts"]:,.0f}')

# Curve table + simple line chart
import matplotlib.pyplot as plt
import streamlit as st

fig, ax = plt.subplots(figsize=(7,5))

for m in ["GREEDY", "ILP"]:
    sub = df_res[df_res["method"] == m]
    ax.plot(
        sub["k"],
        sub["added_pts"],
        marker="o",
        label=m
    )

ax.set_xlabel("Number of new facilities (k)")
ax.set_ylabel("Added covered demand points")
ax.set_title("Greedy vs ILP: Added Demand Points")
ax.legend()
ax.grid(True)

fig1, ax = plt.subplots(figsize=(7,5))
for m in ["GREEDY", "ILP"]:
    sub = df_res[df_res["method"] == m]
    plt.plot(sub["k"], sub["added_pop"], marker="o", label=m)

ax.set_xlabel("Number of new facilities (k)")
ax.set_ylabel("Added covered population")
plt.title("Greedy vs ILP: Added Population Coverage")
ax.legend()
ax.grid(True)


st.subheader("Performance vs K")

col1, col2, col3= st.columns([1, 1, 1])

with col1:
    st.dataframe(df_res, use_container_width=True)

with col2:
    st.pyplot(fig)
    
with col3:
    st.pyplot(fig1)

# Map layers
def make_layer(df, color, radius, name):
    return pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_radius=radius,
        get_fill_color=color,
        pickable=True,
        auto_highlight=True,
    )

# center at SF
view_state = pdk.ViewState(latitude=37.775, longitude=-122.44, zoom=11)

# Base layers (always)
layers = [
    make_layer(E_df[["lon","lat"]].dropna(), [0, 0, 0, 160], 50, "Existing"),
    make_layer(P_df[["lon","lat"]].dropna(), [0, 0, 255, 80], 60, "Demand"),
    make_layer(C_df[["lon","lat"]].dropna(), [255, 0, 0, 140], 80, "Candidates"),
]

# Recommended sites (overlay)
if show_reco and k == 5:
    sel_df = ilp_sel if method == "ILP" else greedy_sel

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=sel_df,
            get_position='[lon, lat]',
            get_radius=500,
            get_fill_color=[255, 140, 0, 255],
            pickable=True,
            auto_highlight=True,
        )
    )
elif show_reco and k != 5:
    st.info("Recommended sites are currently available for K=5 only. Set K=5 to view selected locations.")

st.subheader("Map: Existing / Demand / Candidate Points")
deck = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    tooltip={"text":"{type}\nlon: {lon}\nlat: {lat}"}

)
st.markdown(
    """
    **Legend**
    - ⚫ **Existing stations**: current public charging stations
    - 🔵 **Demand points**: population tract centroids (proxy for charging demand)
    - 🔴 **Candidate points**: uncovered demand points used as candidate locations
    - 🟠 **Recommend points**: recommended next location to build
    """
)

st.pydeck_chart(deck)

