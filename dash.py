import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
import json
import os

# --- LOCAL SAVE / LOAD UTILITIES ---
PROFILE_FILE = "finance_profile.json"

def load_profile():
    """Loads saved JSON data if it exists."""
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

profile_data = load_profile()

def get_val(category, key, default):
    """Helper to fetch nested values from the loaded profile."""
    return profile_data.get(category, {}).get(key, default)

# --- DATA FETCHING (Cached to prevent rate-limiting) ---
@st.cache_data(ttl=3600)
def get_live_price(ticker_symbol):
    if not ticker_symbol or not isinstance(ticker_symbol, str): return 0.0
    try:
        ticker = yf.Ticker(ticker_symbol.strip().upper())
        todays_data = ticker.history(period='1d')
        if not todays_data.empty:
            return float(todays_data['Close'].iloc[0])
        return 0.0
    except Exception:
        return 0.0

def calc_portfolio_value(df):
    total = 0.0
    for _, row in df.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        raw_shares = row.get("Shares", 0.0)
        
        # Bulletproof check for empty cells, NaNs, or typos
        try:
            shares = float(raw_shares)
            if pd.isna(shares):  # Catches Streamlit's blank cell NaNs
                shares = 0.0
        except (ValueError, TypeError):
            shares = 0.0
        
        if ticker and ticker.lower() != "nan" and ticker.lower() != "none":
            price = get_live_price(ticker)
            total += price * shares
            
    return total

# --- TAX CALCULATION UTILITY ---
def calculate_estimated_taxes(gross_income):
    standard_deduction = 15000 
    taxable_income = max(0, gross_income - standard_deduction)
    
    federal_tax = 0
    brackets = [
        (11600, 0.10), (47150, 0.12), (100525, 0.22),
        (191950, 0.24), (243725, 0.32), (609350, 0.35),
        (float('inf'), 0.37)
    ]
    
    prev_limit = 0
    for limit, rate in brackets:
        if taxable_income > prev_limit:
            taxable_amount = min(taxable_income, limit) - prev_limit
            federal_tax += taxable_amount * rate
            prev_limit = limit
        else:
            break
            
    fica_tax = min(gross_income, 168600) * 0.0765
    if gross_income > 168600:
        fica_tax += (gross_income - 168600) * 0.0145
        
    return federal_tax + fica_tax

# --- STREAMLIT APP ---
st.set_page_config(page_title="Personal Finance Tracker", layout="wide")
st.title("💸 Live Personal Finance & Portfolio Dashboard")
st.markdown("Track your income flow and live portfolio balances dynamically. All inputs are listed above their respective charts.")

# --- SESSION STATE FOR DYNAMIC TABLES (Checks JSON profile first) ---
if "crypto_df" not in st.session_state:
    saved_crypto = profile_data.get("portfolios", {}).get("crypto")
    if saved_crypto: st.session_state.crypto_df = pd.DataFrame(saved_crypto)
    else: st.session_state.crypto_df = pd.DataFrame({"Ticker": ["BTC-USD"], "Shares": [0.05]})

if "roth_df" not in st.session_state:
    saved_roth = profile_data.get("portfolios", {}).get("roth")
    if saved_roth: st.session_state.roth_df = pd.DataFrame(saved_roth)
    else: st.session_state.roth_df = pd.DataFrame({"Ticker": ["VOO", "QQQ"], "Shares": [18.0, 5.0]})

if "ind_df" not in st.session_state:
    saved_ind = profile_data.get("portfolios", {}).get("ind")
    if saved_ind: st.session_state.ind_df = pd.DataFrame(saved_ind)
    else: st.session_state.ind_df = pd.DataFrame({"Ticker": ["VTI"], "Shares": [180.0]})

if "k401_df" not in st.session_state:
    saved_k401 = profile_data.get("portfolios", {}).get("k401")
    if saved_k401: st.session_state.k401_df = pd.DataFrame(saved_k401)
    else: st.session_state.k401_df = pd.DataFrame({"Ticker": ["FXAIX"], "Shares": [0.0]})


# ==========================================
# SECTION 1: INCOME & INVESTMENT ASSUMPTIONS
# ==========================================
st.markdown("---")
st.subheader("1. Income & Current Investments")

col1, col2, col3, col4 = st.columns(4)
with col1:
    salary = st.number_input("Annual Salary ($)", min_value=0, value=get_val("income", "salary", 85000), step=5000)
with col2:
    bonus = st.number_input("Annual Bonus ($)", min_value=0, value=get_val("income", "bonus", 50000), step=1000)
with col3:
    kalshi = st.number_input("Kalshi (USD Base)", min_value=0.0, value=get_val("income", "kalshi", 1330.0))
with col4:
    extra_inv_pct = st.number_input("Extra Inv Flow %", min_value=0, max_value=100, value=get_val("income", "extra_inv_pct", 40), step=5, help="% of Remaining Base to invest (rest goes to Spend)")

hsa_col1, hsa_col2 = st.columns(2)
with hsa_col1:
    hsa_employer_seed = st.number_input("HSA Employer Seed (Love's) ($)", min_value=0, max_value=4400, value=get_val("income", "hsa_employer_seed", 1000), step=100, help="Love's annual HSA contribution. IRS 2026 individual limit is $4,400.")
with hsa_col2:
    hsa_current = st.number_input("Current HSA Balance ($)", min_value=0, value=get_val("income", "hsa_current", 0), step=100)

st.markdown("**Current Portfolios (Live tracking via yfinance)**")
t_col1, t_col2, t_col3, t_col4 = st.columns(4)

with t_col1:
    st.caption("Crypto Roth IRA")
    crypto_df = st.data_editor(st.session_state.crypto_df, num_rows="dynamic", key="crypto", use_container_width=True)
with t_col2:
    st.caption("Standard Roth IRA")
    roth_df = st.data_editor(st.session_state.roth_df, num_rows="dynamic", key="roth", use_container_width=True)
with t_col3:
    st.caption("Individual Account")
    ind_df = st.data_editor(st.session_state.ind_df, num_rows="dynamic", key="ind", use_container_width=True)
with t_col4:
    st.caption("Current 401k")
    k401_df = st.data_editor(st.session_state.k401_df, num_rows="dynamic", key="k401", use_container_width=True)

# --- MACRO CALCULATIONS ---
crypto_roth = calc_portfolio_value(crypto_df)
std_roth = calc_portfolio_value(roth_df)
ind_account = calc_portfolio_value(ind_df)
current_401k = calc_portfolio_value(k401_df)

HSA_IRS_LIMIT_2026 = 4400

# Tax split logic
salary_taxes = calculate_estimated_taxes(salary)
total_taxes_combined = calculate_estimated_taxes(salary + bonus)
bonus_taxes = max(0, total_taxes_combined - salary_taxes)

# 5% deducted from total eligible pay (salary + bonus) — dollar-for-dollar match up to 5% ceiling
salary_401k = salary * 0.05
bonus_401k = bonus * 0.05
employee_401k = salary_401k + bonus_401k
employer_401k = employee_401k
total_new_401k = employee_401k + employer_401k

# HSA: Love's seeds the account; you contribute the remainder up to IRS limit (pre-tax)
hsa_employee = max(0, HSA_IRS_LIMIT_2026 - hsa_employer_seed)
total_hsa_new = hsa_employer_seed + hsa_employee

# Net base deducts salary's 401k and HSA employee contribution (both pre-tax payroll deductions)
net_base = max(0, salary - salary_taxes - salary_401k - hsa_employee)
# 5% of bonus goes to 401k; remainder after taxes flows to investments
bonus_to_extra = max(0, bonus * 0.95 - bonus_taxes)

roth_contribution = min(7500, net_base)
remaining_base = net_base - roth_contribution

inv_rate = extra_inv_pct / 100.0
spend_rate = 1.0 - inv_rate

spend = remaining_base * spend_rate
base_extra_inv = remaining_base * inv_rate
total_extra_inv = bonus_to_extra + base_extra_inv
total_current_base = kalshi + crypto_roth + std_roth + ind_account + current_401k + hsa_current
final_portfolio_total = total_current_base + total_new_401k + roth_contribution + total_extra_inv + total_hsa_new

# --- SANKEY DIAGRAM 1: MACRO FLOW ---
st.markdown("### Macro Financial Flow")

# 1. Define all possible labels with current data (Names only)
node_defs = {
    "Salary": "<b>Salary</b>",
    "Bonus": "<b>Bonus</b>",
    "EmpMatch": "<b>Employer 401k Match</b>",
    "Taxes": "<b>Taxes</b>",
    "BonusTaxes": "<b>Bonus Taxes</b>",
    "NetBase": "<b>Net Base</b>",
    "Spend": "<b>Spend</b>",
    "RemBase": "<b>Remaining Base</b>",
    "New401k": "<b>New 401k Flow</b>",
    "NewRoth": "<b>New Roth Flow</b>",
    "ExtraInv": "<b>Extra Inv Flow</b>",
    "EmpHSA": "<b>Employer HSA Seed</b>",
    "NewHSA": "<b>New HSA Flow</b>",
    "CurHSA": "<b>Current HSA</b>",
    "TotHSA": "<b>Total HSA</b>",

    "Cur401k": "<b>Current 401k</b>",
    "CurStdRoth": "<b>Current Std Roth</b>",
    "CurCrypto": "<b>Current Crypto</b>",
    "CurInd": "<b>Current Ind Acct</b>",
    "CurKalshi": "<b>Current Kalshi</b>",

    "Tot401k": "<b>Total 401k</b>",
    "TotStdRoth": "<b>Total Std Roth</b>",
    "TotCrypto": "<b>Total Crypto</b>",
    "TotInd": "<b>Total Ind Acct</b>",
    "TotKalshi": "<b>Total Kalshi</b>",

    "Projected": "<b>Projected Total Portfolio</b>"
}

node_positions = {
    "CurCrypto": (0.01, 0.01),
    "TotCrypto": (0.88, 0.01),
    "CurKalshi": (0.01, 0.04),
    "TotKalshi": (0.88, 0.04),

    "Cur401k": (0.01, 0.08),
    "EmpMatch": (0.01, 0.08),
    "New401k": (0.35, 0.10),
    "Tot401k": (0.88, 0.08),

    "EmpHSA": (0.01, 0.14),
    "CurHSA": (0.01, 0.17),
    "NewHSA": (0.35, 0.16),
    "TotHSA": (0.88, 0.20),

    "CurStdRoth": (0.45, 0.24),
    "NewRoth": (0.55, 0.27),
    "TotStdRoth": (0.88, 0.27),

    "Taxes": (0.25, 0.33),
    "Salary": (0.01, 0.46),
    "NetBase": (0.35, 0.48),

    "Spend": (0.75, 0.40),
    "RemBase": (0.55, 0.44),

    "Bonus": (0.51, 0.65),
    "ExtraInv": (0.75, 0.63),
    "BonusTaxes": (0.65, 0.78),

    "CurInd": (0.01, 0.91),
    "TotInd": (0.88, 0.80),

    "Projected": (0.99, 0.50)
}

# 3. Dynamic Node Builder
nodes_used = {}
source_1 = []
target_1 = []
value_1 = []
link_colors_1 = []

def add_link(src_key, tgt_key, val, color):
    # Only map flows > 0. This skips empty nodes naturally.
    if val > 0:
        if src_key not in nodes_used:
            nodes_used[src_key] = len(nodes_used)
        if tgt_key not in nodes_used:
            nodes_used[tgt_key] = len(nodes_used)
        
        source_1.append(nodes_used[src_key])
        target_1.append(nodes_used[tgt_key])
        value_1.append(val)
        link_colors_1.append(color)

# -> Core Income
add_link("Salary", "Taxes", salary_taxes, 'rgba(231, 76, 60, 0.5)')
add_link("Salary", "NetBase", net_base, 'rgba(46, 204, 113, 0.4)')
add_link("Salary", "New401k", salary_401k, 'rgba(22, 160, 133, 0.4)')
add_link("Salary", "NewHSA", hsa_employee, 'rgba(52, 152, 219, 0.4)')
add_link("EmpMatch", "New401k", employer_401k, 'rgba(22, 160, 133, 0.4)')
add_link("EmpHSA", "NewHSA", hsa_employer_seed, 'rgba(52, 152, 219, 0.4)')
add_link("CurHSA", "TotHSA", hsa_current, 'rgba(52, 152, 219, 0.3)')
add_link("NewHSA", "TotHSA", total_hsa_new, 'rgba(52, 152, 219, 0.5)')

# -> Net Base
add_link("NetBase", "NewRoth", roth_contribution, 'rgba(22, 160, 133, 0.4)')
add_link("NetBase", "RemBase", remaining_base, 'rgba(46, 204, 113, 0.4)')

# -> Spend & Investments
add_link("RemBase", "Spend", spend, 'rgba(231, 76, 60, 0.5)')
add_link("RemBase", "ExtraInv", base_extra_inv, 'rgba(22, 160, 133, 0.4)')

# -> Existing Portfolios -> Totals
add_link("Cur401k", "Tot401k", current_401k, 'rgba(39, 174, 96, 0.3)')
add_link("CurStdRoth", "TotStdRoth", std_roth, 'rgba(39, 174, 96, 0.3)')
add_link("CurCrypto", "TotCrypto", crypto_roth, 'rgba(39, 174, 96, 0.3)')
add_link("CurInd", "TotInd", ind_account, 'rgba(39, 174, 96, 0.3)')
add_link("CurKalshi", "TotKalshi", kalshi, 'rgba(39, 174, 96, 0.3)')

# -> New Capital -> Totals
add_link("New401k", "Tot401k", total_new_401k, 'rgba(22, 160, 133, 0.5)')
add_link("NewRoth", "TotStdRoth", roth_contribution, 'rgba(22, 160, 133, 0.5)')
add_link("ExtraInv", "TotInd", total_extra_inv, 'rgba(22, 160, 133, 0.5)')

# -> Totals -> Final Projected Node
add_link("Tot401k", "Projected", current_401k + total_new_401k, 'rgba(39, 174, 96, 0.3)')
add_link("TotStdRoth", "Projected", std_roth + roth_contribution, 'rgba(39, 174, 96, 0.3)')
add_link("TotCrypto", "Projected", crypto_roth, 'rgba(39, 174, 96, 0.3)')
add_link("TotInd", "Projected", ind_account + total_extra_inv, 'rgba(39, 174, 96, 0.3)')
add_link("TotKalshi", "Projected", kalshi, 'rgba(39, 174, 96, 0.3)')
add_link("TotHSA", "Projected", hsa_current + total_hsa_new, 'rgba(52, 152, 219, 0.3)')

# -> Bonus: 5% to 401k (pre-tax match), 95% net of taxes to investments
add_link("Bonus", "New401k", bonus_401k, 'rgba(22, 160, 133, 0.4)')
add_link("Bonus", "ExtraInv", bonus_to_extra, 'rgba(46, 204, 113, 0.4)')
add_link("Bonus", "BonusTaxes", bonus_taxes, 'rgba(231, 76, 60, 0.5)')

# 5. Extract Final Plotly Arrays
labels_1 = [""] * len(nodes_used)
node_x_1 = [0.0] * len(nodes_used)
node_y_1 = [0.0] * len(nodes_used)
node_colors_1 = ['#27ae60'] * len(nodes_used) 

for key, idx in nodes_used.items():
    labels_1[idx] = node_defs[key]
    node_x_1[idx] = node_positions[key][0]
    node_y_1[idx] = node_positions[key][1]
    
    if key in ["Taxes", "BonusTaxes", "Spend"]:
        node_colors_1[idx] = '#e74c3c'
    elif key in ["New401k", "NewRoth", "ExtraInv"]:
        node_colors_1[idx] = '#16a085'
    elif key in ["NewHSA", "EmpHSA", "CurHSA", "TotHSA"]:
        node_colors_1[idx] = '#2980b9'
    elif key == "Projected":
        node_colors_1[idx] = '#0e6655'

fig_1 = go.Figure(data=[go.Sankey(
    arrangement='fixed', 
    node=dict(
        pad=15,           
        thickness=15,     
        line=dict(color="black", width=0.5), 
        label=labels_1, 
        color=node_colors_1, 
        x=node_x_1, 
        y=node_y_1,
        # Formats the hover box to strictly show "Name: $10,000"
        hovertemplate="%{label}: $%{value:,.0f}<extra></extra>"
    ),
    link=dict(
        source=source_1, 
        target=target_1, 
        value=value_1, 
        color=link_colors_1,
        # Formats the flow lines on hover: "Source -> Target: $10,000"
        hovertemplate="%{source.label} → %{target.label}<br>$%{value:,.0f}<extra></extra>"
    )
)])



# Reduced height from 1000 to 650 to fit entirely on a standard screen, 
# and slightly lowered font size to prevent overlapping text in the compact view.
fig_1.update_layout(height=650, font=dict(size=12, color="#000000", family="Arial"), margin=dict(t=30, b=30, l=20, r=20))
st.plotly_chart(fig_1, use_container_width=True)

# ==========================================
# SECTION 2: MONTHLY SPEND BUDGETING
# ==========================================
st.markdown("---")
st.subheader("2. Detailed Spending Breakdown")
st.markdown(f"Your Macro Flow allocates **\${spend:,.0f} annually** for spending (Approx. **\${spend/12:,.0f} / month**). Break it down below:")

b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns(5)
rent = b_col1.number_input("Rent ($/mo)", value=get_val("budget", "rent", 800), step=50)
food = b_col2.number_input("Food ($/mo)", value=get_val("budget", "food", 400), step=25)
car = b_col3.number_input("Car ($/mo)", value=get_val("budget", "car", 300), step=25)
insurance = b_col4.number_input("Insurance ($/mo)", value=get_val("budget", "insurance", 100), step=10)
travel = b_col5.number_input("Travel ($/mo)", value=get_val("budget", "travel", 150), step=25)

b_col6, b_col7, b_col8, b_col9, b_col10 = st.columns(5)
gifts = b_col6.number_input("Gifts ($/mo)", value=get_val("budget", "gifts", 50), step=10)
dates = b_col7.number_input("Dates ($/mo)", value=get_val("budget", "dates", 100), step=20)
leisure = b_col8.number_input("Leisure ($/mo)", value=get_val("budget", "leisure", 100), step=20)
medical = b_col9.number_input("Medical ($/mo)", value=get_val("budget", "medical", 50), step=10)
other = b_col10.number_input("Other ($/mo)", value=get_val("budget", "other", 0), step=10)

# --- SPEND CALCULATIONS ---
monthly_expenses = {
    "Rent": rent, "Food": food, "Car": car, "Insurance": insurance, "Travel": travel,
    "Gifts": gifts, "Dates": dates, "Leisure": leisure, "Medical": medical, "Other": other
}

annual_expenses = {k: v * 12 for k, v in monthly_expenses.items() if v > 0}
total_budgeted_annual = sum(annual_expenses.values())
unallocated_annual = spend - total_budgeted_annual

if unallocated_annual < 0:
    st.error(f"⚠️ You are over budget by ${abs(unallocated_annual):,.2f} annually! Reduce your monthly inputs or increase your macro Spend allocation.")

# --- SANKEY DIAGRAM 2: SPEND BREAKDOWN ---
st.markdown("### Spend Allocation Flow")

labels_2 = [f"<b>Total Annual Spend: ${spend:,.0f}</b>"]
node_colors_2 = ['#e74c3c'] 
source_2 = []
target_2 = []
value_2 = []
link_colors_2 = []

target_idx = 1
for cat, val in annual_expenses.items():
    labels_2.append(f"<b>{cat}: ${val:,.0f}/yr</b><br>(${val/12:,.0f}/mo)")
    node_colors_2.append('#f39c12') 
    source_2.append(0)
    target_2.append(target_idx)
    value_2.append(val)
    link_colors_2.append('rgba(243, 156, 18, 0.4)')
    target_idx += 1

if unallocated_annual > 0:
    labels_2.append(f"<b>Unallocated / Slush: ${unallocated_annual:,.0f}/yr</b><br>(${unallocated_annual/12:,.0f}/mo)")
    node_colors_2.append('#bdc3c7') 
    source_2.append(0)
    target_2.append(target_idx)
    value_2.append(unallocated_annual)
    link_colors_2.append('rgba(189, 195, 199, 0.4)')

fig_2 = go.Figure(data=[go.Sankey(
    node=dict(pad=20, thickness=30, line=dict(color="black", width=0.5), label=labels_2, color=node_colors_2),
    link=dict(source=source_2, target=target_2, value=value_2, color=link_colors_2)
)])
fig_2.update_layout(height=500, font=dict(size=16, color="#000000", family="Arial"), margin=dict(t=30, b=30, l=20, r=20))
st.plotly_chart(fig_2, use_container_width=True)


# ==========================================
# SECTION 3: PORTFOLIO PROJECTIONS
# ==========================================
st.markdown("---")
new_401k = current_401k + total_new_401k
new_std_roth = std_roth + roth_contribution
new_ind_account = ind_account + total_extra_inv
new_hsa = hsa_current + total_hsa_new

portfolios = {
    "Kalshi": kalshi,
    "Crypto Roth IRA": crypto_roth,
    "Standard Roth IRA": new_std_roth,
    "HSA": new_hsa,
    "Individual Account": new_ind_account,
    "401k": new_401k
}

df_portfolio = pd.DataFrame(list(portfolios.items()), columns=['Account', 'Projected Balance'])

col_p1, col_p2 = st.columns([1, 1])

with col_p1:
    st.write("### Projected Year-End Balances")
    st.dataframe(df_portfolio.style.format({'Projected Balance': '${:,.2f}'}), hide_index=True)
    st.write(f"**Total Projected Portfolio:** ${sum(portfolios.values()):,.2f}")

with col_p2:
    fig_pie = go.Figure(data=[go.Pie(labels=df_portfolio['Account'], values=df_portfolio['Projected Balance'], hole=.4)])
    fig_pie.update_layout(title_text="Investment Distribution", margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# SECTION 4: 25-YEAR GROWTH PROJECTION
# ==========================================
st.markdown("---")
st.subheader("4. 25-Year Portfolio Projection")
st.markdown("Projects the future value of your core retirement and investment accounts based on your current balances, ongoing annual contribution flows, and selected growth rate.")

# Dropdown for expected return rate
return_option = st.selectbox(
    "Expected Annual Return", 
    options=[4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25], 
    index=3, # Defaults to 7
    format_func=lambda x: f"{x}%"
)

# Time horizon and rate
years = list(range(26)) # t=0 through t=25
rate = return_option / 100.0

# Calculate projections using compound interest + future value of an annuity formula
def project_growth(pv, pmt, r, t_list):
    if r == 0:
        return [pv + (pmt * t) for t in t_list]
    return [pv * ((1 + r)**t) + pmt * (((1 + r)**t - 1) / r) for t in t_list]

# Calculate projections using your macro variables
proj_401k = project_growth(current_401k, total_new_401k, rate, years)
proj_roth = project_growth(std_roth, roth_contribution, rate, years)
proj_ind = project_growth(ind_account, total_extra_inv, rate, years)
proj_hsa = project_growth(hsa_current, total_hsa_new, rate, years)

# Create the Plotly figure
fig_proj = go.Figure()

fig_proj.add_trace(go.Scatter(x=years, y=proj_401k, mode='lines', name='401k', line=dict(width=3, color='#2980b9')))
fig_proj.add_trace(go.Scatter(x=years, y=proj_roth, mode='lines', name='Standard Roth IRA', line=dict(width=3, color='#8e44ad')))
fig_proj.add_trace(go.Scatter(x=years, y=proj_hsa, mode='lines', name='HSA', line=dict(width=3, color='#2980b9', dash='dot')))
fig_proj.add_trace(go.Scatter(x=years, y=proj_ind, mode='lines', name='Individual Account', line=dict(width=3, color='#27ae60')))

# Calculate and plot the total portfolio projection line
proj_total = [sum(x) for x in zip(proj_401k, proj_roth, proj_ind, proj_hsa)]
fig_proj.add_trace(go.Scatter(x=years, y=proj_total, mode='lines', name='Total Projected', 
                              line=dict(width=4, dash='dash', color='black')))

fig_proj.update_layout(
    xaxis_title="Years from Now",
    yaxis_title="Projected Value ($)",
    hovermode="x unified",
    height=500,
    margin=dict(t=30, b=30, l=20, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig_proj, use_container_width=True)


# ==========================================
# SECTION 4: SAVE PROFILE
# ==========================================
st.markdown("---")
st.subheader("💾 Save Your Setup")
st.write("Click below to save your current inputs and portfolio holdings. They will automatically load the next time you open the dashboard.")

if st.button("Save Profile to File", type="primary"):
    current_profile = {
        "income": {
            "salary": salary, "bonus": bonus, "kalshi": kalshi, "extra_inv_pct": extra_inv_pct,
            "hsa_employer_seed": hsa_employer_seed, "hsa_current": hsa_current
        },
        "portfolios": {
            "crypto": crypto_df.to_dict('records'),
            "roth": roth_df.to_dict('records'),
            "ind": ind_df.to_dict('records'),
            "k401": k401_df.to_dict('records')
        },
        "budget": {
            "rent": rent, "food": food, "car": car, "insurance": insurance, "travel": travel,
            "gifts": gifts, "dates": dates, "leisure": leisure, "medical": medical, "other": other
        }
    }
    
    with open(PROFILE_FILE, "w") as f:
        json.dump(current_profile, f, indent=4)
        
    st.success("✅ Profile successfully saved! You can safely close out.")