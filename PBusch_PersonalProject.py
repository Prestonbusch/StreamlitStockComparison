import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

def safe_divide(numerator, denominator):
    """Safely divide two numbers, returning None if division is not possible."""
    try:
        return numerator / denominator if numerator is not None and denominator else None
    except ZeroDivisionError:
        return None

def get_scalar(value):
    """Convert a pandas Series or DataFrame to a scalar, if possible."""
    if isinstance(value, pd.Series):
        return value.item() if len(value) == 1 else value.sum()
    return value

def get_annual_metrics(ticker, year):
    stock = yf.Ticker(ticker)
    
    # Define the start and end date for the specified year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get historical stock data
    stock_data = stock.history(start=start_date, end=end_date)
    
    if stock_data.empty:
        st.warning(f"No data found for {ticker} in {year}.")
        return None

    # Get financial data
    financials = stock.financials
    balance_sheet = stock.balance_sheet
    cashflow = stock.cashflow
    info = stock.info

    # Calculations
    metrics = {}

    try:
        # Safely fetch fields with checks for missing data
        net_income = get_scalar(financials.loc['Net Income', f"{year}"]) if f"{year}" in financials.columns else None
        stockholders_equity = (
            get_scalar(balance_sheet.loc["Total Equity Gross Minority Interest", f"{year}"])
            if f"{year}" in balance_sheet.columns
            else None
        )
        total_assets = (
            get_scalar(balance_sheet.loc['Total Assets', f"{year}"])
            if f"{year}" in balance_sheet.columns
            else None
        )
        gross_profit = (
            get_scalar(financials.loc['Gross Profit', f"{year}"])
            if f"{year}" in financials.columns
            else None
        )
        revenue = (
            get_scalar(financials.loc['Total Revenue', f"{year}"])
            if f"{year}" in financials.columns
            else None
        )
        total_liabilities = (
            get_scalar(balance_sheet.loc['Total Liabilities Net Minority Interest', f"{year}"])
            if f"{year}" in balance_sheet.columns
            else None
        )
        ebitda = (
            get_scalar(financials.loc['EBITDA', f"{year}"])
            if f"{year}" in financials.columns
            else None
        )
        ev_ebitda = info.get('enterpriseToEbitda', None)  # EV/EBITDA directly from statistics
        peg_ratio = info.get('pegRatio', None)  # PEG Ratio from statistics

        # ROE = Net Income / Stockholders' Equity
        metrics['ROE'] = safe_divide(net_income, stockholders_equity)

        # ROA = Net Income / Total Assets
        metrics['ROA'] = safe_divide(net_income, total_assets)

        # Gross Profit Margin = Gross Profit / Revenue
        metrics['Gross Profit Margin'] = safe_divide(gross_profit, revenue)

        # Debt-to-Equity = Total Liabilities / Stockholders' Equity
        metrics['Debt-to-Equity'] = safe_divide(total_liabilities, stockholders_equity)

        # P/E Ratio = Current Price / EPS
        end_of_year_price = stock_data['Close'].iloc[-1]
        eps = info.get('trailingEps', None)
        metrics['P/E Ratio'] = safe_divide(end_of_year_price, eps)

        # EV/EBITDA from statistics
        metrics['EV/EBITDA'] = ev_ebitda

        # P/EBITDA = Market Cap / EBITDA
        market_cap = info.get('marketCap', None)
        metrics['P/EBITDA'] = safe_divide(market_cap, ebitda)

        # Earnings Yield = EPS / Current Price
        metrics['Earnings Yield'] = safe_divide(eps, end_of_year_price)

        # Revenue Growth = (Current Revenue - Previous Revenue) / Previous Revenue
        previous_revenue = (
            get_scalar(financials.loc['Total Revenue', f"{int(year) - 1}"])
            if f"{int(year) - 1}" in financials.columns
            else None
        )
        metrics['Revenue Growth'] = safe_divide((revenue - previous_revenue), previous_revenue)

        # PEG Ratio: Calculate manually if not available in info
        if peg_ratio is None:
            earnings_growth_rate = safe_divide(metrics['Revenue Growth'], 100)
            metrics['PEG Ratio'] = safe_divide(metrics['P/E Ratio'], earnings_growth_rate)
        else:
            metrics['PEG Ratio'] = peg_ratio

    except Exception as e:
        st.warning(f"Error calculating metrics for {year}: {e}")
        return None
    
    return metrics

def compare_stocks_over_range(ticker1, ticker2, start_year, end_year):
    yearly_data = []

    for year in range(start_year, end_year + 1):
        st.write(f"Fetching metrics for {ticker1} and {ticker2} in {year}...")
        metrics1 = get_annual_metrics(ticker1, year)
        metrics2 = get_annual_metrics(ticker2, year)

        if metrics1 and metrics2:
            combined_data = {
                "Year": year,
                **{f"{ticker1}_{key}": value for key, value in metrics1.items()},
                **{f"{ticker2}_{key}": value for key, value in metrics2.items()},
            }
            yearly_data.append(combined_data)

    if yearly_data:
        return pd.DataFrame(yearly_data)
    else:
        st.warning(f"No data available for {ticker1} and {ticker2} in the specified range.")
        return None

def plot_stock_prices(ticker1, ticker2, start_year, end_year):
    # Define the start and end dates for the range
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    
    # Fetch historical data for both stocks
    stock1 = yf.Ticker(ticker1).history(start=start_date, end=end_date)
    stock2 = yf.Ticker(ticker2).history(start=start_date, end=end_date)
    
    # Plot the stock prices
    st.write(f"Stock Prices: {ticker1} vs {ticker2} ({start_year}-{end_year})")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(stock1.index, stock1['Close'], label=ticker1, linewidth=2)
    ax.plot(stock2.index, stock2['Close'], label=ticker2, linewidth=2)
    ax.set_title(f"Stock Prices: {ticker1} vs {ticker2} ({start_year}-{end_year})")
    ax.set_xlabel("Date")
    ax.set_ylabel("Stock Price")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)

# Streamlit App
st.title("Stock Comparison Tool")

# User inputs
ticker1 = st.text_input("Enter the first stock ticker:", value="TSLA").upper()
ticker2 = st.text_input("Enter the second stock ticker:", value="MSFT").upper()
start_year = st.number_input("Enter the start year (YYYY):", min_value=1900, max_value=2100, value=2021)
end_year = st.number_input("Enter the end year (YYYY):", min_value=1900, max_value=2100, value=2023)

if st.button("Compare Stocks"):
    # Compare stocks over range
    comparison_table = compare_stocks_over_range(ticker1, ticker2, start_year, end_year)

    # Display the comparison table
    if comparison_table is not None:
        st.subheader(f"Comparison of {ticker1} and {ticker2} from {start_year} to {end_year}")
        st.dataframe(comparison_table)

    # Plot stock prices
    plot_stock_prices(ticker1, ticker2, start_year, end_year)
