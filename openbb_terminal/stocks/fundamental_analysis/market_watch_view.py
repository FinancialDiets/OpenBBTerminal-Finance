""" Fundamental Analysis Market Watch View. LEGACY.

MarketWatch now requires a user to be a subscriber in order to have access to the financials...
So this code is not being used for the time being, it may be at a later stage.
"""
__docformat__ = "numpy"

import argparse
import logging
from typing import List

import pandas as pd

from openbb_terminal.decorators import log_start_end
from openbb_terminal.helper_funcs import (
    lambda_financials_colored_values,
    patch_pandas_text_adjustment,
    print_rich_table,
    parse_simple_args,
)
from openbb_terminal.rich_config import console
from openbb_terminal.stocks.fundamental_analysis import market_watch_model as mwm
from openbb_terminal import rich_config

# pylint: disable=too-many-branches


logger = logging.getLogger(__name__)


@log_start_end(log=logger)
def income(other_args: List[str], ticker: str):
    """Market Watch ticker income statement

    Parameters
    ----------
    other_args : List[str]
        argparse other args
    ticker : str
        Fundamental analysis ticker symbol
    """
    parser = argparse.ArgumentParser(
        add_help=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog="income",
        description="""
            Prints either yearly or quarterly income statement the company. The following fields
            are expected: Sales Growth, Cost of Goods Sold (COGS) incl. D&A, COGS Growth, COGS
            excluding D&A, Depreciation & Amortization Expense, Depreciation, Amortization of
            Intangibles, Gross Income, Gross Income Growth, Gross Profit Margin, SG&A Expense, SGA
            Growth, Research & Development, Other SG&A, Other Operating Expense, Unusual Expense,
            EBIT after Unusual Expense, Non Operating Income/Expense, Non-Operating Interest
            Income, Equity in Affiliates (Pretax), Interest Expense, Interest Expense Growth,
            Gross Interest Expense, Interest Capitalized, Pretax Income, Pretax Income Growth,
            Pretax Margin, Income Tax, Income Tax - Current Domestic, Income Tax - Current Foreign,
            Income Tax - Deferred Domestic, Income Tax - Deferred Foreign, Income Tax Credits,
            Equity in Affiliates, Other After Tax Income (Expense), Consolidated Net Income,
            Minority Interest Expense, Net Income Growth, Net Margin Growth, Extraordinaries &
            Discontinued Operations, Extra Items & Gain/Loss Sale Of Assets, Cumulative Effect -
            Accounting Chg, Discontinued Operations, Net Income After Extraordinaries,
            Preferred Dividends, Net Income Available to Common, EPS (Basic), EPS (Basic) Growth,
            Basic Shares Outstanding, EPS (Diluted), EPS (Diluted) Growth, Diluted Shares
            Outstanding, EBITDA, EBITDA Growth, EBITDA Margin, Sales/Revenue, and Net Income.
            [Source: Market Watch]
        """,
    )
    parser.add_argument(
        "-q",
        "--quarter",
        action="store_true",
        default=False,
        dest="b_quarter",
        help="Quarter fundamental data flag.",
    )

    ns_parser = parse_simple_args(parser, other_args)
    if not ns_parser:
        return

    df_financials = mwm.prepare_df_financials(ticker, "income", ns_parser.b_quarter)
    if len(df_financials) == 0 or df_financials.empty:
        console.print("Marketwatch does not yet provide financials for this ticker")
        return

    if rich_config.USE_COLOR:
        df_financials = df_financials.applymap(lambda_financials_colored_values)

        patch_pandas_text_adjustment()
        pd.set_option("display.max_colwidth", None)
        pd.set_option("display.max_rows", None)

    if df_financials.empty:
        console.print("Marketwatch does not yet provide financials for this ticker")
    else:
        console.print(df_financials.to_string(index=False))


@log_start_end(log=logger)
def balance(other_args: List[str], ticker: str):
    """Market Watch ticker balance statement

    Parameters
    ----------
    other_args : List[str]
        argparse other args
    ticker : str
        Fundamental analysis ticker symbol
    """
    parser = argparse.ArgumentParser(
        add_help=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog="balance",
        description="""
            Prints either yearly or quarterly assets from balance sheet of the company.
            The following fields are expected: Cash & Short Term Investments, Cash & Short Term
            Investments Growth, Cash Only, Short-Term Investments, Cash & ST Investments / Total
            Assets, Total Accounts Receivable, Total Accounts Receivable Growth, Accounts
            Receivables, Net, Accounts Receivables, Gross, Bad Debt/Doubtful Accounts, Other
            Receivable, Accounts Receivable Turnover, Inventories, Finished Goods, Work in
            Progress, Raw Materials, Progress Payments & Other, Other Current Assets,
            Miscellaneous Current Assets, Net Property, Plant & Equipment, Property, Plant &
            Equipment - Gross, Buildings, Land & Improvements, Computer Software and Equipment,
            Other Property, Plant & Equipment, Accumulated Depreciation, Total Investments and
            Advances, Other Long-Term Investments, Long-Term Note Receivables, Intangible Assets,
            Net Goodwill, Net Other Intangibles, Other Assets.

            Prints either yearly or quarterly liabilities and shareholders' equity from balance
            sheet of the company. The following fields are expected: ST Debt & Current Portion LT
            Debt, Short Term Debt, Current Portion of Long Term Debt, Accounts Payable, Accounts
            Payable Growth, Income Tax Payable, Other Current Liabilities, Dividends Payable,
            Accrued Payroll, Miscellaneous Current Liabilities, Long-Term Debt, Long-Term Debt
            excl. Capitalized Leases, Non-Convertible Debt, Convertible Debt, Capitalized Lease
            Obligations, Provision for Risks & Charges, Deferred Taxes, Deferred Taxes - Credits,
            Deferred Taxes - Debit, Other Liabilities, Other Liabilities (excl. Deferred Income),
            Deferred Income, Non-Equity Reserves, Total Liabilities / Total Assets, Preferred Stock
            (Carrying Value), Redeemable Preferred Stock, Non-Redeemable Preferred Stock, Common
            Equity (Total), Common Equity/Total Assets, Common Stock Par/Carry Value, Retained
            Earnings, ESOP Debt Guarantee, Cumulative Translation Adjustment/Unrealized For. Exch.
            Gain, Unrealized Gain/Loss Marketable Securities, Revaluation Reserves, Treasury Stock,
            Total Shareholders' Equity, Total Shareholders' Equity / Total Assets, Accumulated
            Minority Interest, Total Equity, Total Current Assets, Total Assets, Total Current
            Liabilities, Total Liabilities, and Liabilities & Shareholders' Equity.
            [Source: Market Watch]
        """,
    )
    parser.add_argument(
        "-q",
        "--quarter",
        action="store_true",
        default=False,
        dest="b_quarter",
        help="Quarter fundamental data flag.",
    )

    ns_parser = parse_simple_args(parser, other_args)
    if not ns_parser:
        return

    df_financials = mwm.prepare_df_financials(ticker, "balance", ns_parser.b_quarter)
    if len(df_financials) == 0 or df_financials.empty:
        console.print("Marketwatch does not yet provide financials for this ticker")
        return

    if rich_config.USE_COLOR:
        df_financials = df_financials.applymap(lambda_financials_colored_values)

        patch_pandas_text_adjustment()
        pd.set_option("display.max_colwidth", None)
        pd.set_option("display.max_rows", None)

    if df_financials.empty:
        console.print("Marketwatch does not yet provide financials for this ticker")
    else:
        console.print(df_financials.to_string(index=False))


@log_start_end(log=logger)
def cash(other_args: List[str], ticker: str):
    """Market Watch ticker cash flow statement

    Parameters
    ----------
    other_args : List[str]
        argparse other args
    ticker : str
        Fundamental analysis ticker symbol
    """
    parser = argparse.ArgumentParser(
        add_help=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog="cash_flow",
        description="""
            Prints either yearly or quarterly cash flow operating activities of the company.
            The following fields are expected: Net Income before Extraordinaries, Net Income
            Growth, Depreciation, Depletion & Amortization, Depreciation and Depletion,
            Amortization of Intangible Assets, Deferred Taxes & Investment Tax Credit, Deferred
            Taxes, Investment Tax Credit, Other Funds, Funds from Operations, Extraordinaries,
            Changes in Working Capital, Receivables, Accounts Payable, Other Assets/Liabilities,
            and Net Operating Cash Flow Growth.

            Prints either yearly or quarterly cash flow investing activities of the company.
            The following fields are expected: Capital Expenditures, Capital Expenditures Growth,
            Capital Expenditures/Sales, Capital Expenditures (Fixed Assets), Capital Expenditures
            (Other Assets), Net Assets from Acquisitions, Sale of Fixed Assets & Businesses,
            Purchase/Sale of Investments, Purchase of Investments, Sale/Maturity of Investments,
            Other Uses, Other Sources, Net Investing Cash Flow Growth.

            Prints either yearly or quarterly cash flow financing activities of the company.
            The following fields are expected: Cash Dividends Paid - Total, Common Dividends,
            Preferred Dividends, Change in Capital Stock, Repurchase of Common & Preferred Stk.,
            Sale of Common & Preferred Stock, Proceeds from Stock Options, Other Proceeds from Sale
            of Stock, Issuance/Reduction of Debt, Net, Change in Current Debt, Change in Long-Term
            Debt, Issuance of Long-Term Debt, Reduction in Long-Term Debt, Other Funds, Other Uses,
            Other Sources, Net Financing Cash Flow Growth, Net Financing Cash Flow/Sales, Exchange
            Rate Effect, Miscellaneous Funds, Net Change in Cash, Free Cash Flow, Free Cash Flow
            Growth, Free Cash Flow Yield, Net Operating Cash Flow, Net Investing Cash Flow, Net
            Financing Cash Flow.
            [Source: Market Watch]
        """,
    )
    parser.add_argument(
        "-q",
        "--quarter",
        action="store_true",
        default=False,
        dest="b_quarter",
        help="Quarter fundamental data flag.",
    )

    ns_parser = parse_simple_args(parser, other_args)
    if not ns_parser:
        return

    df_financials = mwm.prepare_df_financials(ticker, "cashflow", ns_parser.b_quarter)
    if len(df_financials) == 0 or df_financials.empty:
        console.print("Marketwatch does not yet provide financials for this ticker")
        return

    if rich_config.USE_COLOR:
        df_financials = df_financials.applymap(lambda_financials_colored_values)

        patch_pandas_text_adjustment()
        pd.set_option("display.max_colwidth", None)
        pd.set_option("display.max_rows", None)

    if df_financials.empty:
        console.print("Marketwatch does not yet provide financials for this ticker")
    else:
        console.print(df_financials.to_string(index=False))


@log_start_end(log=logger)
def display_sean_seah_warnings(symbol: str, debug: bool = False):
    """Display Sean Seah warnings

    Parameters
    ----------
    other_args : List[str]
        argparse other args
    symbol : str
        Stock ticker
    """
    financials, warnings, debugged_warnings = mwm.get_sean_seah_warnings(symbol, debug)

    if financials.empty:
        console.print(f"No financials found for {symbol}\n")
        return

    print_rich_table(
        financials,
        headers=list(financials.columns),
        title="Sean Seah Warnings",
        show_index=True,
    )

    if not warnings:
        console.print("No warnings found. Good stonk")
        return

    messages = (
        [item for pair in zip(warnings, debugged_warnings) for item in pair]
        if debug
        else warnings
    )

    console.print("Warnings:\n")
    console.print("\n".join(messages))
