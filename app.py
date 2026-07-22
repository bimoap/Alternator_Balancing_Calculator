import streamlit as st
import numpy as np
import itertools
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Alternator Balancing Calculator", layout="wide")

SETTINGS_FILE = "fastener_settings.csv"

# --- Default Data ---
DEFAULT_FASTENERS = pd.DataFrame([
    {"Name": "M6 x 16 Cap Screw", "Weight (g)": 5.44, "Is Standard": False},
    {"Name": "M6 x 12 Cap Screw", "Weight (g)": 4.74, "Is Standard": False},
    {"Name": "M6 x 10 Cap Screw", "Weight (g)": 4.37, "Is Standard": False},
    {"Name": "M6 x 10 Button Head (4.0)", "Weight (g)": 4.0, "Is Standard": False},
    {"Name": "M6 x 12 Torx", "Weight (g)": 3.3, "Is Standard": True},
    {"Name": "M6 x 10 Button Head (3.0)", "Weight (g)": 3.0, "Is Standard": False}
])

# --- Helper Functions ---
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        return pd.read_csv(SETTINGS_FILE)
    return DEFAULT_FASTENERS.copy()

def save_settings(df):
    df.to_csv(SETTINGS_FILE, index=False)

def get_standard_fastener(df):
    std_row = df[df["Is Standard"] == True]
    if not std_row.empty:
        return std_row.iloc[0]["Name"], std_row.iloc[0]["Weight (g)"]
    # Fallback to the first item if none is checked
    return df.iloc[0]["Name"], df.iloc[0]["Weight (g)"]

def calculate_best_pattern(cma, target_angle, options_df, current_holes):
    """Finds the best combination of fasteners based on the CURRENT state of the holes."""
    target_rad = np.radians(target_angle)
    target_x = cma * np.cos(target_rad)
    target_y = cma * np.sin(target_rad)
    
    hole_angles = [i * 15 for i in range(24)]
    nearest_idx = round(target_angle / 15) % 24
    search_indices = [(nearest_idx + offset) % 24 for offset in [-2, -1, 0, 1, 2]]
    
    fastener_names = options_df["Name"].tolist()
    weight_dict = dict(zip(options_df["Name"], options_df["Weight (g)"]))
    
    best_error = float('inf')
    best_combo = None
    best_vector = (0, 0)
    
    for combo in itertools.product(fastener_names, repeat=len(search_indices)):
        sum_x = 0
        sum_y = 0
        
        for idx_in_search, new_f_name in enumerate(combo):
            actual_hole_idx = search_indices[idx_in_search]
            current_f_name = current_holes[actual_hole_idx]
            
            # Delta mass is the difference between the proposed fastener and the CURRENT one installed
            net_mass = weight_dict[new_f_name] - weight_dict[current_f_name]
            
            if net_mass != 0:
                angle_rad = np.radians(hole_angles[actual_hole_idx])
                sum_x += net_mass * np.cos(angle_rad)
                sum_y += net_mass * np.sin(angle_rad)
                
        error = np.sqrt((target_x - sum_x)**2 + (target_y - sum_y)**2)
        
        if error < best_error:
            best_error = error
            best_combo = combo
            best_vector = (sum_x, sum_y)
            
    return search_indices, best_combo, best_error, best_vector

def plot_polar_balancing(cma, target_angle, indices, combo, current_holes, options_df, best_vector, std_name):
    fig = go.Figure()
    
    applied_r = np.sqrt(best_vector[0]**2 + best_vector[1]**2)
    applied_theta = np.degrees(np.arctan2(best_vector[1], best_vector[0])) % 360
    
    rim_radius = max(cma, applied_r) * 1.4
    if rim_radius == 0: rim_radius = 5
    
    angles = np.arange(0, 360, 15)
    
    # Map proposed changes
    proposed_changes = {}
    if combo:
        for idx_in_search, new_f_name in enumerate(combo):
            actual_hole_idx = indices[idx_in_search]
            if new_f_name != current_holes[actual_hole_idx]:
                proposed_changes[actual_hole_idx * 15] = new_f_name

    std_angles, prev_mod_angles, prev_mod_texts, new_angles, new_texts = [], [], [], [], []
    
    for idx, angle in enumerate(angles):
        current_f = current_holes[idx]
        
        if angle in proposed_changes:
            new_angles.append(angle)
            new_texts.append(f"<b>{angle}°</b><br>CHANGE TO:<br>{proposed_changes[angle]}")
        elif current_f != std_name:
            prev_mod_angles.append(angle)
            prev_mod_texts.append(f"<b>{angle}°</b><br>Prev Mod:<br>{current_f}")
        else:
            std_angles.append(angle)

    # 1. Standard holes (Grey)
    fig.add_trace(go.Scatterpolar(
        r=[rim_radius]*len(std_angles), theta=std_angles, mode='markers',
        marker=dict(color='lightgrey', size=10, line=dict(color='black', width=1)),
        name='Standard Fastener', hoverinfo='theta', text=[f"{a}°" for a in std_angles]
    ))

    # 2. Previously Modified holes (Blue)
    if prev_mod_angles:
        fig.add_trace(go.Scatterpolar(
            r=[rim_radius]*len(prev_mod_angles), theta=prev_mod_angles, mode='markers+text',
            text=prev_mod_texts, textposition='top center', textfont=dict(size=9, color='blue'),
            marker=dict(color='lightblue', size=12, line=dict(color='black', width=1)),
            name='Previously Modified', hoverinfo='text'
        ))

    # 3. New Proposed Changes (Gold)
    if new_angles:
        fig.add_trace(go.Scatterpolar(
            r=[rim_radius]*len(new_angles), theta=new_angles, mode='markers+text',
            text=new_texts, textposition='top center', textfont=dict(size=10, color='darkorange'),
            marker=dict(color='gold', size=14, line=dict(color='black', width=2)),
            name='Proposed Change', hoverinfo='text'
        ))

    # 4. Measured Vector (Red)
    fig.add_trace(go.Scatterpolar(
        r=[0, cma], theta=[0, target_angle], mode='lines+markers',
        marker=dict(size=[0, 8], color='red'), line=dict(color='red', width=3, dash='solid'),
        name=f'Target (CMA: {cma}g @ {target_angle}°)'
    ))

    # 5. Applied Mass Vector (Green)
    fig.add_trace(go.Scatterpolar(
        r=[0, applied_r], theta=[0, applied_theta], mode='lines+markers',
        marker=dict(size=[0, 8], color='green'), line=dict(color='green', width=3, dash='dot'),
        name=f'Applied ({applied_r:.2f}g @ {applied_theta:.1f}°)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, rim_radius + (rim_radius*0.2)]),
            # CHANGED: direction remains "clockwise", rotation is now 270 (bottom)
            angularaxis=dict(direction="clockwise", rotation=270, tickmode='array', tickvals=angles)
        ),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=40, b=40, l=40, r=40), height=600
    )
    return fig

# --- Init Session State ---
inventory_df = load_settings()
std_name, std_weight = get_standard_fastener(inventory_df)

if 'pass_num' not in st.session_state:
    st.session_state.pass_num = 1
if 'holes' not in st.session_state:
    st.session_state.holes = [std_name] * 24
if 'history' not in st.session_state:
    st.session_state.history = []
if 'proposed_update' not in st.session_state:
    st.session_state.proposed_update = None

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Fastener Settings")
    st.caption("Edit names, weights, and toggle the standard fastener. Add or delete rows as needed.")
    
    edited_df = st.data_editor(
        inventory_df, 
        num_rows="dynamic",
        column_config={
            "Name": st.column_config.TextColumn("Fastener Name", required=True),
            "Weight (g)": st.column_config.NumberColumn("Weight (g)", required=True, format="%.2f"),
            "Is Standard": st.column_config.CheckboxColumn("Standard?", default=False)
        },
        use_container_width=True
    )
    
    if st.button("Save Settings", type="secondary"):
        save_settings(edited_df)
        st.success("Settings saved! App will reload.")
        st.rerun()
        
    st.divider()
    
    st.header("🔄 Balancing Progress")
    st.metric("Current Pass", f"{st.session_state.pass_num} / 4")
    
    if st.button("Reset / Start New Alternator"):
        st.session_state.pass_num = 1
        st.session_state.holes = [std_name] * 24
        st.session_state.history = []
        st.session_state.proposed_update = None
        st.rerun()

    st.markdown("---")
    st.markdown("App developed & maintained by: **Bimo**")

# --- Main App ---
st.title("Alternator Balancing - Multi-Pass")

if st.session_state.pass_num > 4:
    st.success("🏁 4 Passes Completed! Balancing procedure finished. Reset the app in the sidebar to start a new alternator.")
    st.stop()

st.header(f"Vibrotest Inputs (Pass {st.session_state.pass_num})")
input_col1, input_col2, input_col3 = st.columns([1, 1, 2])

with input_col1:
    cma_input = st.number_input("CMA (grams)", min_value=0.0, value=0.0, step=0.1)
with input_col2:
    angle_input = st.number_input("Location (Degrees)", min_value=0.0, max_value=360.0, value=0.0, step=1.0)

if st.button("Calculate Plan", type="primary"):
    indices, combo, error, best_vec = calculate_best_pattern(cma_input, angle_input, edited_df, st.session_state.holes)
    
    # Store the proposed state update so it can be applied later
    new_holes = list(st.session_state.holes)
    action_data = []
    weight_dict = dict(zip(edited_df["Name"], edited_df["Weight (g)"]))
    
    for idx_in_search, new_f_name in enumerate(combo):
        actual_hole_idx = indices[idx_in_search]
        current_f_name = new_holes[actual_hole_idx]
        
        if new_f_name != current_f_name:
            net_addition = weight_dict[new_f_name] - weight_dict[current_f_name]
            action_data.append({
                "Pos": f"{actual_hole_idx * 15}°",
                "Remove": current_f_name,
                "Install": new_f_name,
                "Net Mass": f"{'+' if net_addition > 0 else ''}{net_addition:.2f}g"
            })
            new_holes[actual_hole_idx] = new_f_name
            
    st.session_state.proposed_update = {
        "new_holes": new_holes,
        "action_data": action_data,
        "indices": indices,
        "combo": combo,
        "error": error,
        "best_vec": best_vec,
        "cma": cma_input,
        "angle": angle_input
    }

# Display results if calculation has been run
if st.session_state.proposed_update:
    data = st.session_state.proposed_update
    st.divider()
    
    res_col1, res_col2 = st.columns([1, 2])
    
    with res_col1:
        st.subheader("Action Plan")
        if not data["action_data"]:
            st.info("No fastener changes required based on this CMA reading.")
        else:
            df_action = pd.DataFrame(data["action_data"])
            st.dataframe(df_action, hide_index=True)
            st.metric(label="Residual Unbalance (Error)", value=f"{data['error']:.2f} g")
            
            st.warning("⚠️ Apply these physical changes to the alternator, then click the button below to proceed.")
            
            if st.button(f"Confirm Changes & Proceed to Pass {st.session_state.pass_num + 1}", type="secondary"):
                # Apply changes to state
                st.session_state.holes = data["new_holes"]
                st.session_state.history.append(data["action_data"])
                st.session_state.pass_num += 1
                st.session_state.proposed_update = None
                st.rerun()
                
    with res_col2:
        st.subheader("Balancing Vector Map")
        fig = plot_polar_balancing(
            data["cma"], data["angle"], 
            data["indices"], data["combo"], 
            st.session_state.holes, edited_df, 
            data["best_vec"], std_name
        )
        st.plotly_chart(fig, use_container_width=True)
