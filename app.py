import streamlit as st
import numpy as np
import itertools
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Alternator Balancing Calculator", layout="wide")

def get_net_weights(fastener_options, std_weight):
    """Calculates the net added mass for each fastener option."""
    options = {"Standard": 0.0}
    for name, weight in fastener_options.items():
        if weight > std_weight:
            options[name] = weight - std_weight
    return options

def calculate_best_pattern(cma, target_angle, options_dict):
    """Finds the best combination of fasteners to match the target vector."""
    target_rad = np.radians(target_angle)
    target_x = cma * np.cos(target_rad)
    target_y = cma * np.sin(target_rad)
    
    hole_angles = [i * 15 for i in range(24)]
    nearest_idx = round(target_angle / 15) % 24
    search_indices = [(nearest_idx + offset) % 24 for offset in [-2, -1, 0, 1, 2]]
    
    fastener_names = list(options_dict.keys())
    best_error = float('inf')
    best_combo = None
    best_vector = (0, 0)
    
    for combo in itertools.product(fastener_names, repeat=len(search_indices)):
        sum_x = 0
        sum_y = 0
        
        for idx_in_search, f_name in enumerate(combo):
            net_mass = options_dict[f_name]
            if net_mass > 0:
                actual_hole_idx = search_indices[idx_in_search]
                angle_rad = np.radians(hole_angles[actual_hole_idx])
                sum_x += net_mass * np.cos(angle_rad)
                sum_y += net_mass * np.sin(angle_rad)
                
        error = np.sqrt((target_x - sum_x)**2 + (target_y - sum_y)**2)
        
        if error < best_error:
            best_error = error
            best_combo = combo
            best_vector = (sum_x, sum_y)
            
    return search_indices, best_combo, best_error, best_vector

def plot_polar_balancing(cma, target_angle, indices, combo, net_options, best_vector):
    """Generates a polar plot of the alternator and mass vectors."""
    fig = go.Figure()
    
    # Calculate applied vector radius and angle
    applied_r = np.sqrt(best_vector[0]**2 + best_vector[1]**2)
    applied_theta = np.degrees(np.arctan2(best_vector[1], best_vector[0])) % 360
    
    # Dynamic scaling for the rim so vectors fit nicely inside
    rim_radius = max(cma, applied_r) * 1.4
    if rim_radius == 0: rim_radius = 5
    
    angles = np.arange(0, 360, 15)
    
    # Map combo to actual holes
    replaced_dict = {}
    for idx_in_search, f_name in enumerate(combo):
        if f_name != "Standard":
            actual_hole_idx = indices[idx_in_search]
            replaced_dict[actual_hole_idx * 15] = f_name

    # Separate data for standard vs replaced holes for plotting
    std_angles, rep_angles, rep_texts = [], [], []
    for a in angles:
        if a in replaced_dict:
            rep_angles.append(a)
            # Text formatting for the label
            rep_texts.append(f"<b>{a}°</b><br>{replaced_dict[a]}")
        else:
            std_angles.append(a)

    # 1. Plot standard holes (Grey)
    fig.add_trace(go.Scatterpolar(
        r=[rim_radius]*len(std_angles),
        theta=std_angles,
        mode='markers',
        marker=dict(color='lightgrey', size=10, line=dict(color='black', width=1)),
        name='Standard Fastener',
        hoverinfo='theta',
        text=[f"{a}°" for a in std_angles]
    ))

    # 2. Plot replaced holes (Gold)
    if rep_angles:
        fig.add_trace(go.Scatterpolar(
            r=[rim_radius]*len(rep_angles),
            theta=rep_angles,
            mode='markers+text',
            text=rep_texts,
            textposition='top center',
            textfont=dict(size=10, color='darkorange'),
            marker=dict(color='gold', size=14, line=dict(color='black', width=2)),
            name='Replaced Fastener',
            hoverinfo='text'
        ))

    # 3. Measured Vector (Target CMA) - Red
    fig.add_trace(go.Scatterpolar(
        r=[0, cma],
        theta=[0, target_angle],
        mode='lines+markers',
        marker=dict(size=[0, 8], color='red'),
        line=dict(color='red', width=3, dash='solid'),
        name=f'Target (CMA: {cma}g @ {target_angle}°)'
    ))

    # 4. Applied Mass Vector - Green
    fig.add_trace(go.Scatterpolar(
        r=[0, applied_r],
        theta=[0, applied_theta],
        mode='lines+markers',
        marker=dict(size=[0, 8], color='green'),
        line=dict(color='green', width=3, dash='dot'),
        name=f'Applied ({applied_r:.2f}g @ {applied_theta:.1f}°)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, rim_radius + (rim_radius*0.2)]),
            angularaxis=dict(direction="counterclockwise", rotation=0, tickmode='array', tickvals=angles)
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=40, b=40, l=40, r=40),
        height=600
    )
    return fig

# --- UI Setup ---
st.title("Alternator Balancing Calculator")
st.markdown("Calculate and visualize fastener replacements to balance the alternator.")

with st.sidebar:
    st.header("Hardware Configuration")
    std_weight = st.number_input("Standard Fastener Weight (g)", value=3.2, step=0.1)
    
    st.subheader("Available Replacements (g)")
    opt1_w = st.number_input("Option 1", value=4.0, step=0.1)
    opt2_w = st.number_input("Option 2", value=4.7, step=0.1)
    opt3_w = st.number_input("Option 3", value=5.5, step=0.1)
    
    fastener_inventory = {
        f"M6 x 16 SS ({opt1_w}g)": opt1_w,
        f"M6 x 12 SS ({opt2_w}g)": opt2_w,
        f"M6 x 16 SS ({opt3_w}g)": opt3_w
    }
    
    st.markdown("---")
    st.markdown("App developed & maintained by: **Bimo**")

# --- Main App ---
st.header("Vibrotest Inputs")
input_col1, input_col2, input_col3 = st.columns([1, 1, 2])

with input_col1:
    cma_input = st.number_input("CMA (grams)", min_value=0.0, value=2.5, step=0.1)
with input_col2:
    angle_input = st.number_input("Location (Degrees)", min_value=0.0, max_value=360.0, value=45.0, step=1.0)

if st.button("Calculate & Visualize", type="primary"):
    net_options = get_net_weights(fastener_inventory, std_weight)
    
    indices, combo, error, best_vec = calculate_best_pattern(cma_input, angle_input, net_options)
    
    st.divider()
    
    # Use columns to put the action plan and the plot side-by-side
    res_col1, res_col2 = st.columns([1, 2])
    
    with res_col1:
        st.subheader("Action Plan")
        results_data = []
        for idx_in_search, f_name in enumerate(combo):
            if f_name != "Standard":
                actual_hole_idx = indices[idx_in_search]
                angle = actual_hole_idx * 15
                net_addition = net_options[f_name]
                results_data.append({
                    "Pos": f"{angle}°",
                    "Install": f_name,
                    "Net Mass": f"+{net_addition:.1f}g"
                })
                
        if not results_data:
            st.info("The required CMA is too small to warrant replacing standard fasteners.")
        else:
            df = pd.DataFrame(results_data)
            st.dataframe(df, hide_index=True)
            
            st.metric(label="Residual Unbalance (Error)", value=f"{error:.2f} g")
            st.caption("Theoretical remaining unbalance due to discrete mass limitations.")
            
    with res_col2:
        st.subheader("Balancing Vector Map")
        fig = plot_polar_balancing(cma_input, angle_input, indices, combo, net_options, best_vec)
        st.plotly_chart(fig, use_container_width=True)
