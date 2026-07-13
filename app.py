
import streamlit as st
import numpy as np
import itertools
import pandas as pd

st.set_page_config(page_title="Alternator Balancing Calculator", layout="centered")

def get_net_weights(fastener_options, std_weight):
    """Calculates the net added mass for each fastener option."""
    # Option 0 is always keeping the standard fastener (0g net change)
    options = {"Standard": 0.0}
    for name, weight in fastener_options.items():
        if weight > std_weight:
            options[name] = weight - std_weight
    return options

def calculate_best_pattern(cma, target_angle, options_dict):
    """Finds the best combination of fasteners to match the target vector."""
    # Convert target to cartesian
    target_rad = np.radians(target_angle)
    target_x = cma * np.cos(target_rad)
    target_y = cma * np.sin(target_rad)
    
    # Fastener positions (24 holes, 15 degrees apart)
    hole_angles = [i * 15 for i in range(24)]
    
    # Find the nearest hole to the target angle to localize the search
    nearest_idx = round(target_angle / 15) % 24
    
    # Search window: the 5 nearest holes (e.g., -30, -15, 0, +15, +30 degrees relative to target)
    search_indices = [(nearest_idx + offset) % 24 for offset in [-2, -1, 0, 1, 2]]
    
    fastener_names = list(options_dict.keys())
    best_error = float('inf')
    best_combo = None
    best_vector = (0, 0)
    
    # Brute force combinations for the 5 localized holes (Number of Options ^ 5)
    # This runs almost instantly for a small search space
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
            
    return search_indices, best_combo, best_error

# --- UI Setup ---
st.title("Alternator Balancing Calculator")
st.markdown("Calculates fastener replacements to achieve the target CMA and Location.")

with st.sidebar:
    st.header("Hardware Configuration")
    std_weight = st.number_input("Standard Fastener Weight (g)", value=3.2, step=0.1)
    
    st.subheader("Available Replacements (g)")
    opt1_w = st.number_input("Option 1", value=4.0, step=0.1)
    opt2_w = st.number_input("Option 2", value=4.7, step=0.1)
    opt3_w = st.number_input("Option 3", value=5.5, step=0.1)
    
    # Dictionary mapping display names to weights
    fastener_inventory = {
        f"M6 x 16 SS ({opt1_w}g)": opt1_w,
        f"M6 x 12 SS ({opt2_w}g)": opt2_w,
        f"M6 x 16 SS ({opt3_w}g)": opt3_w
    }

# --- Main App ---
st.header("Vibrotest Readings")
col1, col2 = st.columns(2)

with col1:
    cma_input = st.number_input("CMA (grams)", min_value=0.0, value=2.5, step=0.1)
with col2:
    angle_input = st.number_input("Location (Degrees)", min_value=0.0, max_value=360.0, value=45.0, step=1.0)

if st.button("Calculate Balancing Pattern", type="primary"):
    net_options = get_net_weights(fastener_inventory, std_weight)
    
    indices, combo, error = calculate_best_pattern(cma_input, angle_input, net_options)
    
    st.divider()
    st.subheader("Action Plan")
    
    results_data = []
    for idx_in_search, f_name in enumerate(combo):
        if f_name != "Standard":
            actual_hole_idx = indices[idx_in_search]
            angle = actual_hole_idx * 15
            net_addition = net_options[f_name]
            results_data.append({
                "Position (Degrees)": f"{angle}°",
                "Fastener to Install": f_name,
                "Net Mass Added": f"+{net_addition:.1f}g"
            })
            
    if not results_data:
        st.info("The required CMA is too small to warrant replacing the standard fasteners.")
    else:
        df = pd.DataFrame(results_data)
        st.table(df)
        
        st.metric(label="Residual Unbalance (Estimated Error)", value=f"{error:.2f} g")
        st.caption(f"This is the theoretical remaining unbalance based on the limited discrete mass options.")
