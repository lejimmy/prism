import requests
import pandas as pd
import streamlit as st

risk_free_rate = 0.195
luna_ust_address = "terra1m6ywlgn6wrjuagcmmezzz2a029gtldhey5k552"
beth_ust_address = "terra1c0afrdc5253tkp5wt7rxhuj42xwyf2lcre0s7c"

st.set_page_config(layout="wide")


@st.cache
def get_price(pair_address):

    # requests headers
    headers = {
        "authority": "api.coinhall.org",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
        "accept": "*/*",
        "sec-gpc": "1",
        "origin": "https://coinhall.org",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://coinhall.org/",
        "accept-language": "en-US,en;q=0.9",
    }

    # coinhall api
    response = requests.get(
        "https://api.coinhall.org/api/v1/charts/terra/pairs", headers=headers
    ).json()

    # convert to dataframe
    df = (
        pd.DataFrame.from_dict(response, orient="index")
        .reset_index(drop=False)
        .rename(columns={"index": "address"})
        .drop(labels=["timestamp", "unofficial", "startAt", "endAt"], axis=1)
    )

    # filter for astroport pair
    df = df[df["address"] == pair_address].reset_index()

    # parse json data
    df = pd.concat(
        [
            df,
            df["asset0"].apply(pd.Series).add_prefix("asset0_"),
            df["asset1"].apply(pd.Series).add_prefix("asset1_"),
        ],
        axis=1,
    )

    # price
    if df["asset0_symbol"][0] == "UST":
        price = float(df["asset0_poolAmount"] / df["asset1_poolAmount"])
    else:
        price = float(df["asset1_poolAmount"] / df["asset0_poolAmount"])

    return price


@st.cache
def get_oracle_rewards(luna_price):

    # oracle address
    response = requests.get(
        " https://lcd.terra.dev/bank/balances/terra1jgp27m8fykex4e4jtt0l7ze8q528ux2lh4zh0f",
    ).json()

    # convert to dataframe
    df = pd.DataFrame.from_dict(response["result"]).set_index("denom")

    # parse for ust and luna rewards
    ust_rewards = int(df.loc["uusd", "amount"]) / 1e6
    luna_rewards = int(df.loc["uluna", "amount"]) / 1e6

    # add ust and value of luna
    oracle_rewards = ust_rewards + luna_rewards * luna_price

    return oracle_rewards


@st.cache
def get_staked_luna():

    # staking pool
    response = requests.get(
        " https://lcd.terra.dev/cosmos/staking/v1beta1/pool",
    ).json()

    # convert to dataframe
    df = pd.DataFrame.from_dict(response)

    # parse number of staked luna
    staked_luna = round(int(df.loc["bonded_tokens", "pool"]) / 1e6, -6)

    return staked_luna


@st.cache
def get_staking_yield(luna_price, staked_luna):

    # amount of oracle rewards in UST
    oracle_rewards = get_oracle_rewards(luna_price)

    avg_validator_commission = 0.05

    # oracle rewards paid over two years, distributed to staked luna, divided my current luna price, minus validator commissions
    staking_yield = (
        oracle_rewards / 2 / staked_luna / luna_price * (1 - avg_validator_commission)
    )

    return staking_yield


# initial parameters
luna_price = get_price(luna_ust_address)
staked_luna = get_staked_luna()
staking_yield = get_staking_yield(luna_price, staked_luna) * 100

eth_price = get_price(beth_ust_address)

# sidebar assumptions

st.sidebar.header("Assumptions")
st.sidebar.write("Exand the following sections to change your assumptions.")

with st.sidebar.expander("PRISM", expanded=True):

    prism_price = st.number_input(
        label="PRISM Price", min_value=0.0, step=0.1, value=1.0, format="%.2f"
    )

    circulating_supply = st.number_input(
        label="Circulating Supply (Millions)",
        min_value=70,
        max_value=1_000,
        value=70,
        help="First year circulating supply of 333m tokens.  Max of 1b tokens.",
    )

    percent_prism_staked = st.slider(
        label="PRISM Staked",
        min_value=0.0,
        max_value=100.0,
        value=75.0,
        help="Amount of circulating PRISM that is staked.",
        format="%.0f%%",
    )


with st.sidebar.expander("LUNA", expanded=True):

    staked_luna = st.number_input(
        label="Total Staked",
        min_value=100.0,
        step=100_000.0,
        value=staked_luna,
        format="%.2d",
        help="Total amount of LUNA Staked.",
    )

    luna_price = st.number_input(
        label="Price",
        min_value=1.0,
        step=1.0,
        value=luna_price,
        format="%.0d",
    )

    luna_yield = st.slider(
        label="Staking Yield",
        min_value=1.0,
        max_value=20.0,
        value=staking_yield + 1,
        format="%.1f%%",
        help="Yield after validator commissions, including airdrops.",
    )

    luna_market_share = st.slider(
        label="Staked Market Share",
        min_value=1,
        max_value=100,
        value=10,
        format="%d%%",
        help="Percent share of all staked LUNA.",
    )

    yluna_staked = st.slider(
        label="yLUNA Staked",
        min_value=1,
        max_value=100,
        value=90,
        format="%d%%",
        help="yLUNA used for LP farms will receive swap fees and PRISM incentives but not receive staking rewards.",
    )

with st.sidebar.expander("bETH"):

    staked_eth = st.number_input(
        label="Total Staked",
        min_value=100.0,
        step=1_000.0,
        value=148_000.0,
        format="%.2d",
        help="Total amount of ETH Staked.",
    )

    eth_price = st.number_input(
        label="Price",
        min_value=1.0,
        step=10.0,
        value=eth_price,
        format="%.2d",
    )

    eth_yield = st.slider(
        label="Staking Yield",
        min_value=1.0,
        max_value=20.0,
        value=5.0,
        format="%.1f%%",
    )

    eth_market_share = st.slider(
        label="Staked ETH Market Share",
        min_value=1,
        max_value=100,
        value=10,
        format="%d%%",
        help="Percent share of all staked ETH.",
    )

    yeth_staked = st.slider(
        label="yETH Staked",
        min_value=1,
        max_value=100,
        value=90,
        format="%d%%",
        help="yETH used for LP farms will receive swap fees and PRISM incentives but not receive staking rewards.",
    )

with st.sidebar.expander("Liquidity Providers"):

    total_lp = st.number_input(
        label="Total Liquidity on Terra (Billions)",
        min_value=0.5,
        step=0.1,
        value=2.0,
        format="%.1f",
        help="Total volume of all swaps on Terra.",
    )

    lp_yield = st.slider(
        label="Average LP APR",
        min_value=1.0,
        max_value=100.0,
        value=50.0,
        format="%.1f%%",
        help="Includes swap fees and LP incentives.",
    )

    lp_market_share = st.slider(
        label="LP Market Share",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.1,
        format="%.1f%%",
        help="Percent share of all swaps on Terra.",
    )

    ylp_staked = st.slider(
        label="yLP Staked",
        min_value=1,
        max_value=100,
        value=90,
        format="%d%%",
        help="yLP used for LP farms will receive swap fees and PRISM incentives but not receive staking rewards.",
    )

st.markdown("# PRISM Protocol Valuation Calculator")
st.markdown(
    """
    This calculator builds on [@LunaEvangelist's](https://twitter.com/lunaisfreedom) article on [Medium](https://medium.com/@LunaEvangelist/prism-whats-it-worth-eee965644fa8) regarding the valuation of the PRISM token.
    
    Open the menu on the left to change your assumptions.
    """
)
st.info(
    "To support more community tools like this, consider delegating to the [GT Capital Validator](https://station.terra.money/validator/terravaloper1rn9grwtg4p3f30tpzk8w0727ahcazj0f0n3xnk)."
)

# luna calculations
prism_luna = staked_luna * luna_market_share / 100
prism_luna_rewards = prism_luna * luna_yield / 100
staked_yluna_revenue = prism_luna_rewards * yluna_staked / 100 * 0.1
unstaked_yluna_revenue = prism_luna_rewards * (1 - yluna_staked / 100)
total_yluna_revenue_usd = (staked_yluna_revenue + unstaked_yluna_revenue) * luna_price

# eth calculations
prism_eth = staked_eth * eth_market_share / 100
prism_eth_rewards = prism_eth * eth_yield / 100
staked_yeth_revenue = prism_eth_rewards * yeth_staked / 100 * 0.1
unstaked_yeth_revenue = prism_eth_rewards * (1 - yeth_staked / 100)
total_yeth_revenue_usd = (staked_yeth_revenue + unstaked_yeth_revenue) * eth_price

# lp calculations
prism_lp = total_lp * lp_market_share * 1_000_000_000 / 100
prism_lp_rewards = prism_lp * lp_yield / 100
staked_ylp_revenue = prism_lp_rewards * lp_yield / 100 * 0.15
unstaked_ylp_revenue = prism_lp_rewards * (1 - ylp_staked / 100)
total_ylp_revenue_usd = staked_ylp_revenue + unstaked_ylp_revenue

st.markdown("## Profit Centers")

col1, col2, col3 = st.columns(3)

with col1:

    st.subheader("LUNA Vault")
    st.markdown(
        f"""
        | Description | Amount |
        | --- | ---: |
        | Total Staked | {staked_luna:,.0f} |
        | Prism Market Share | {prism_luna:,.0f} |
        | Rewards per year | {prism_luna_rewards:,.0f} |
        | Staked yLUNA Revenue | {staked_yluna_revenue:,.0f} |
        | Unstaked yLUNA Revenue | {unstaked_yluna_revenue:,.0f} |
        | Total yLUNA Revenue | ${total_yluna_revenue_usd:,.0f} |
        """
    )

with col2:
    st.subheader("ETH Vault")
    st.markdown(
        f"""
        | Description | Amount |
        | --- | ---: |
        | Total Staked | {staked_eth:,.0f} |
        | Prism Market Share | {prism_eth:,.0f} |
        | Rewards per year | {prism_eth_rewards:,.0f} |
        | Staked yETH Revenue | {staked_yeth_revenue:,.0f} |
        | Unstaked yETH Revenue | {unstaked_yeth_revenue:,.0f} |
        | Total yETH Revenue | ${total_yeth_revenue_usd:,.0f} |
        """
    )

with col3:
    st.subheader("yLP Vaults")
    st.markdown(
        f"""
        | Description | Amount |
        | --- | ---: |
        | Total Liquidity | ${total_lp * 1_000_000_000:,.0f} |
        | Prism Market Share | ${prism_lp:,.0f} |
        | Rewards per year | ${prism_lp_rewards:,.0f} |
        | Staked yLP Revenue | ${staked_ylp_revenue:,.0f} |
        | Unstaked yLP Revenue | ${unstaked_ylp_revenue:,.0f} |
        | Total yLP Revenue | ${total_ylp_revenue_usd:,.0f} |
        """
    )

st.markdown("<br>", unsafe_allow_html=True)

# metrics

# total revenues
total_ytoken_revenue_usd = (
    total_yluna_revenue_usd + total_yeth_revenue_usd + total_ylp_revenue_usd
)

# total value locked
tvl = prism_lp + (luna_price * prism_luna) + (eth_price * prism_eth)

# earnings per tvl
earn_tvl = total_ytoken_revenue_usd / tvl

col4, col5, col6 = st.columns(3)

col4.metric(
    label="Total Value Locked",
    value=f"${tvl:,.0f}",
)

col5.metric(
    label="Total Revenue Per Year",
    value=f"${total_ytoken_revenue_usd:,.0f}",
)

col6.metric(
    label="Revenue Per Total Value Locked",
    value=f"{earn_tvl*100:,.2f}%",
)

# xprism revenue per token
xprism_revenue_per_token = (
    total_ytoken_revenue_usd
    / (circulating_supply * 1_000_000)
    / (percent_prism_staked / 100)
)

# xprism apr
xprism_apr = xprism_revenue_per_token / prism_price * 100

col7, col8, col9 = st.columns(3)

col7.metric(
    label="PRISM Circulating Supply",
    value=f"{circulating_supply * 1_000_000:,.0f}",
)

col8.metric(
    label="xPRISM Annual Revenue",
    value=f"${xprism_revenue_per_token:,.2f}",
)

col9.metric(label="xPRISM APR", value=f"{xprism_apr:.2f}%")

st.info(
    "You can compare protocol revenue and total value locked at https://www.theblockcrypto.com"
)

st.markdown(
    """

## Other Profit Centers
- AMM Fees
- Limit order fees
- Lido bAssets: ySOL, yDOT, etc.
- IBC PoS Assets: ySCRT, yJUNO, yOSMO, etc.
- Fixed maturities: p/yaUST-24m, etc.
"""
)

st.markdown("")

# disclaimer
st.warning("This tool was created for educational purposes only, not financial advice.")
