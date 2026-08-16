import streamlit as st
import requests

st.set_page_config(page_title="Archmage 0-CD Tester", layout="wide")

# --- DATA FETCHING (DDRAGON FOR NAMES, CDRAGON FOR STATS) ---
@st.cache_data(ttl=86400)
def get_champion_directory():
    """Uses DDragon just to map Champion Names to their numeric IDs."""
    res = requests.get("https://ddragon.leagueoflegends.com/cdn/13.24.1/data/en_US/champion.json")
    if res.status_code == 200:
        champ_dict = {}
        for champ_data in res.json()['data'].values():
            champ_dict[champ_data['name']] = champ_data['key'] # Name -> ID (e.g., "Gangplank" -> "41")
        return champ_dict
    return {}

@st.cache_data(ttl=86400)
def get_cdragon_spells(champ_id):
    """Fetches the raw game engine stats from Community Dragon."""
    res = requests.get(f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champions/{champ_id}.json")
    if res.status_code == 200:
        data = res.json()
        # CDragon usually stores Q, W, E, R in the first 4 slots of the 'spells' array
        spells = data.get('spells', [])
        if len(spells) >= 4:
            return {
                "Q": spells[0],
                "W": spells[1],
                "E": spells[2],
                "R": spells[3]
            }
    return {}

champ_directory = get_champion_directory()
champions = sorted(list(champ_directory.keys()))

st.title("Archmage 0-CD Alternating Tester")
st.markdown("*Pulling live engine data via Community Dragon*")

# --- GLOBAL CHAMPION SELECTION ---
st.subheader("Champion Selection")
selected_champ = st.selectbox("Select Champion", options=champions)

# Get the numeric ID to query CDragon
champ_id = champ_directory.get(selected_champ)
champ_spells = get_cdragon_spells(champ_id)

st.divider()

# --- UI LAYOUT & CDRAGON PARSER ---
col1, col2 = st.columns(2)

def spell_selection_ui(col, spell_id, spells):
    with col:
        st.subheader(f"Spell {spell_id}")
        
        if spells:
            spell_key = st.selectbox(f"Select Skill {spell_id}", options=["Q", "W", "E", "R"], key=f"skill_key_{spell_id}")
            selected_spell = spells.get(spell_key, {})
            st.markdown(f"**{selected_spell.get('name', 'Unknown Spell')}**")
            
            # --- CDRAGON PARSING LOGIC ---
            ammo_data = selected_spell.get('ammo', {})
            has_charges = ammo_data is not None and 'ammoRechargeTime' in ammo_data and len(ammo_data['ammoRechargeTime']) > 0
            
            if has_charges:
                cd_array = ammo_data['ammoRechargeTime']
                max_charges_array = ammo_data.get('maxAmmo', [1])
                st.success("✅ Charge-based spell automatically detected via CDragon.")
            else:
                cd_array = selected_spell.get('cooldownCoefficients', [10.0])
                max_charges_array = [1]
            
            valid_ranks = [cd for cd in cd_array if cd > 0]
            if not valid_ranks:
                valid_ranks = [10.0] # Fallback
                
            # THE FIX: Only render a slider if there are multiple ranks
            if len(valid_ranks) > 1:
                rank_index = st.slider(f"Skill Rank", min_value=1, max_value=len(valid_ranks), value=1, key=f"rank_{spell_id}") - 1
            else:
                rank_index = 0
                st.info("Skill only has 1 rank.")
            
            # Extract the correct Base CD / Recharge Time
            base_cd = float(valid_ranks[rank_index])
            
            # Extract the correct number of charges for that rank
            valid_max_charges = [c for c in max_charges_array if c > 0]
            if not valid_max_charges:
                valid_max_charges = [1]
            charge_rank_index = min(rank_index, len(valid_max_charges) - 1)
            num_charges = int(valid_max_charges[charge_rank_index])
            
            st.info(f"**{'Base Recharge Time' if has_charges else 'Base CD'}:** {base_cd}s")
            if has_charges:
                st.info(f"**Max Charges Available:** {num_charges}")
                
        else:
            base_cd = 10.0
            num_charges = 1
            st.error("Failed to load CDragon data.")

        st.markdown("---")
        spec_ah = st.number_input(f"Specific AH", min_value=0.0, max_value=200.0, value=0.0, step=1.0, key=f"ah_{spell_id}")
        
        return base_cd, spec_ah, num_charges

# Pass the globally fetched spells down into the column UI
s1_base_cd, s1_spec_ah, s1_charges = spell_selection_ui(col1, "1", champ_spells)
s2_base_cd, s2_spec_ah, s2_charges = spell_selection_ui(col2, "2", champ_spells)

st.divider()

st.subheader("Global Stats")
gen_ah = st.slider("General Ability Haste:", min_value=0.0, max_value=500.0, value=60.0, step=1.0)
purist = st.checkbox("Purist-Caster (10% Total CD Reduction)")

# --- CORE MATH LOGIC ---

s1_refund_per_cast = s1_base_cd * 0.30
s2_refund_per_cast = s2_base_cd * 0.30

s1_total_refund = s1_charges * s1_refund_per_cast
s2_total_refund = s2_charges * s2_refund_per_cast

cd_modifier = 0.90 if purist else 1.0

total_ah_s1 = gen_ah + s1_spec_ah
total_ah_s2 = gen_ah + s2_spec_ah

s1_cd = s1_base_cd * (100 / (100 + total_ah_s1)) * cd_modifier
s2_cd = s2_base_cd * (100 / (100 + total_ah_s2)) * cd_modifier

s1_charges_generated = s2_total_refund / s1_cd if s1_cd > 0 else float('inf')
s2_charges_generated = s1_total_refund / s2_cd if s2_cd > 0 else float('inf')

ah_mult = 90 if purist else 100

s1_req_total_ah = (ah_mult * s1_base_cd / s2_total_refund) - 100 if s2_total_refund > 0 else float('inf')
s2_req_total_ah = (ah_mult * s2_base_cd / s1_total_refund) - 100 if s1_total_refund > 0 else float('inf')

s1_req_gen = s1_req_total_ah - s1_spec_ah if s1_req_total_ah != float('inf') else float('inf')
s2_req_gen = s2_req_total_ah - s2_spec_ah if s2_req_total_ah != float('inf') else float('inf')

required_general_ah = max(s1_req_gen, s2_req_gen, 0)

# --- OUTPUT RENDERING ---
st.divider()
st.header("Results")

st.markdown(f"**Archmage refund from S1 → S2:** `{s1_total_refund:.2f}s` *(from {s1_charges} cast{'s' if s1_charges > 1 else ''})*")
st.markdown(f"**Archmage refund from S2 → S1:** `{s2_total_refund:.2f}s` *(from {s2_charges} cast{'s' if s2_charges > 1 else ''})*")

st.markdown(f"**S1 In-Game CD / Recharge:** `{s1_cd:.2f}s` *(Using {s1_base_cd}s Base & {total_ah_s1:.0f} Total AH)*")
st.markdown(f"**S2 In-Game CD / Recharge:** `{s2_cd:.2f}s` *(Using {s2_base_cd}s Base & {total_ah_s2:.0f} Total AH)*")

st.divider()
st.subheader("Charge Generation & Loop Test")

st.markdown(f"**Casting S2 ({s2_charges}x)** generates **{s1_charges_generated:.2f}** charges of S1.")
if s1_cd <= s2_total_refund:
    st.success(f"✅ **Spell 1: VALID** - S2 completely refunds at least 1 charge of S1.")
else:
    st.error(f"❌ **Spell 1: INVALID** - {s1_cd - s2_total_refund:.2f}s remaining for a single charge.")

st.markdown(f"**Casting S1 ({s1_charges}x)** generates **{s2_charges_generated:.2f}** charges of S2.")
if s2_cd <= s1_total_refund:
    st.success(f"✅ **Spell 2: VALID** - S1 completely refunds at least 1 charge of S2.")
else:
    st.error(f"❌ **Spell 2: INVALID** - {s2_cd - s1_total_refund:.2f}s remaining for a single charge.")

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