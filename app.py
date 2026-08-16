import streamlit as st

# Configure the page layout
st.set_page_config(page_title="Archmage 0-CD Tester", layout="centered")

st.title("Archmage 0-CD Alternating Tester")
st.markdown("Test if your spell loop can achieve a mathematical 0-second cooldown.")

# Use columns to lay out the inputs cleanly
col1, col2 = st.columns(2)

with col1:
    st.subheader("Spell 1")
    s1_base_cd = st.number_input("S1 Base CD (s):", min_value=0.0, max_value=200.0, value=80.0, step=0.5)
    s1_spec_ah = st.number_input("S1 Specific AH:", min_value=0.0, max_value=200.0, value=40.0, step=1.0)

with col2:
    st.subheader("Spell 2")
    s2_base_cd = st.number_input("S2 Base CD (s):", min_value=0.0, max_value=200.0, value=50.0, step=0.5)
    s2_spec_ah = st.number_input("S2 Specific AH:", min_value=0.0, max_value=200.0, value=0.0, step=1.0)

st.divider()

st.subheader("Global Stats")
gen_ah = st.slider("General Ability Haste:", min_value=0.0, max_value=500.0, value=60.0, step=1.0)
purist = st.checkbox("Purist-Caster (10% Total CD Reduction)")

# --- CORE MATH LOGIC ---

# Archmage refund uses the CURRENT Base CD
s1_refund = s1_base_cd * 0.30
s2_refund = s2_base_cd * 0.30

# Purist-Caster 10% reduction modifier
cd_modifier = 0.90 if purist else 1.0

# Total Ability Haste per spell
total_ah_s1 = gen_ah + s1_spec_ah
total_ah_s2 = gen_ah + s2_spec_ah

# Effective cooldown uses the CURRENT Base CD
s1_cd = s1_base_cd * (100 / (100 + total_ah_s1)) * cd_modifier
s2_cd = s2_base_cd * (100 / (100 + total_ah_s2)) * cd_modifier

# Required TOTAL AH for each spell to be completely refunded
ah_mult = 90 if purist else 100

s1_req_total_ah = (ah_mult * s1_base_cd / s2_refund) - 100 if s2_refund > 0 else float('inf')
s2_req_total_ah = (ah_mult * s2_base_cd / s1_refund) - 100 if s1_refund > 0 else float('inf')

# Required GENERAL AH
s1_req_gen = s1_req_total_ah - s1_spec_ah if s1_req_total_ah != float('inf') else float('inf')
s2_req_gen = s2_req_total_ah - s2_spec_ah if s2_req_total_ah != float('inf') else float('inf')

required_general_ah = max(s1_req_gen, s2_req_gen, 0)

# --- OUTPUT RENDERING ---

st.divider()
st.header("Results")

st.markdown(f"**Archmage refund from S1 → S2:** `{s1_refund:.2f}s`")
st.markdown(f"**Archmage refund from S2 → S1:** `{s2_refund:.2f}s`")

st.markdown(f"**S1 In-Game CD:** `{s1_cd:.2f}s` *(Using {s1_base_cd}s Base CD & {total_ah_s1:.0f} Total AH)*")
st.markdown(f"**S2 In-Game CD:** `{s2_cd:.2f}s` *(Using {s2_base_cd}s Base CD & {total_ah_s2:.0f} Total AH)*")

st.subheader("Current AH Test:")

if s1_cd <= s2_refund:
    st.success("✅ **Spell 1: VALID** - Spell 1 can be fully refunded by Spell 2")
else:
    st.error(f"❌ **Spell 1: INVALID** - {s1_cd - s2_refund:.2f}s remaining")

if s2_cd <= s1_refund:
    st.success("✅ **Spell 2: VALID** - Spell 2 can be fully refunded by Spell 1")
else:
    st.error(f"❌ **Spell 2: INVALID** - {s2_cd - s1_refund:.2f}s remaining")

st.divider()
st.subheader("Minimum Ability Haste")

req_s1_str = f"{max(0, s1_req_total_ah):.2f}" if s1_req_total_ah != float('inf') else "Impossible"
req_s2_str = f"{max(0, s2_req_total_ah):.2f}" if s2_req_total_ah != float('inf') else "Impossible"
req_gen_str = f"{required_general_ah:.2f}" if required_general_ah != float('inf') else "Impossible"

st.markdown(f"* Total AH required for S1: **{req_s1_str}**")
st.markdown(f"* Total AH required for S2: **{req_s2_str}**")
st.markdown(f"* Target General AH for BOTH: **{req_gen_str}**")

if required_general_ah == float('inf'):
    st.error("RESULT: 0-CD loop is impossible.")
elif gen_ah >= required_general_ah:
    st.success("RESULT: 0-CD alternating loop is mathematically possible! 🎉")
else:
    st.warning(f"RESULT: Not enough AH. Need **{required_general_ah - gen_ah:.2f}** more General AH.")