def plot_polar_balancing(cma, target_angle, indices, combo, current_holes, options_df, best_vector, std_name):
    fig = go.Figure()
    
    applied_r = np.sqrt(best_vector[0]**2 + best_vector[1]**2)
    applied_theta = np.degrees(np.arctan2(best_vector[1], best_vector[0])) % 360
    
    rim_radius = max(cma, applied_r) * 1.4
    if rim_radius == 0: rim_radius = 5
    
    angles = np.arange(0, 360, 15)
    
    # Create the custom labels for the rim (e.g., "#1 (0°)", "#2 (15°)")
    tick_labels = [f"#{i+1} ({angle}°)" for i, angle in enumerate(angles)]
    
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
        bolt_num = idx + 1  # Bolt 1 is at 0 degrees
        
        if angle in proposed_changes:
            new_angles.append(angle)
            new_texts.append(f"<b>Bolt {bolt_num} ({angle}°)</b><br>CHANGE TO:<br>{proposed_changes[angle]}")
        elif current_f != std_name:
            prev_mod_angles.append(angle)
            prev_mod_texts.append(f"<b>Bolt {bolt_num} ({angle}°)</b><br>Prev Mod:<br>{current_f}")
        else:
            std_angles.append(angle)

    # 1. Standard holes (Grey)
    fig.add_trace(go.Scatterpolar(
        r=[rim_radius]*len(std_angles), theta=std_angles, mode='markers',
        marker=dict(color='lightgrey', size=10, line=dict(color='black', width=1)),
        name='Standard Fastener', hoverinfo='text', 
        text=[f"Bolt {std_angles.index(a)+1} ({a}°)" for a in std_angles]
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
            angularaxis=dict(
                direction="clockwise", 
                rotation=270, 
                tickmode='array', 
                tickvals=angles,
                ticktext=tick_labels  # Maps the custom #Bolt (Degree) labels to the rim
            )
        ),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=40, b=40, l=40, r=40), height=600
    )
    return fig
