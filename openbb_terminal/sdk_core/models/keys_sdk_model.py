# flake8: noqa
# pylint: disable=C0301,R0902,R0903
from openbb_terminal.sdk_core.sdk_helpers import Category
import openbb_terminal.sdk_core.sdk_init as lib


class KeysRoot(Category):
    """OpenBB SDK Keys Module

    Attributes:
        `av`: Set Alpha Vantage key\n
        `binance`: Set Binance key\n
        `bitquery`: Set Bitquery key\n
        `cmc`: Set Coinmarketcap key\n
        `coinbase`: Set Coinbase key\n
        `coinglass`: Set Coinglass key.\n
        `cpanic`: Set Cpanic key.\n
        `degiro`: Set Degiro key\n
        `eodhd`: Set Eodhd key.\n
        `ethplorer`: Set Ethplorer key.\n
        `finnhub`: Set Finnhub key\n
        `fmp`: Set Financial Modeling Prep key\n
        `fred`: Set FRED key\n
        `get_keys_info`: Get info on available APIs to use in set_keys.\n
        `github`: Set GitHub key.\n
        `glassnode`: Set Glassnode key.\n
        `iex`: Set IEX Cloud key\n
        `messari`: Set Messari key.\n
        `mykeys`: Get currently set API keys.\n
        `news`: Set News key\n
        `oanda`: Set Oanda key\n
        `polygon`: Set Polygon key\n
        `quandl`: Set Quandl key\n
        `reddit`: Set Reddit key\n
        `rh`: Set Robinhood key\n
        `santiment`: Set Santiment key.\n
        `set_keys`: Set API keys in bundle.\n
        `shroom`: Set Shroom key\n
        `si`: Set Sentimentinvestor key.\n
        `smartstake`: Set Smartstake key.\n
        `tokenterminal`: Set Token Terminal key.\n
        `tradier`: Set Tradier key\n
        `twitter`: Set Twitter key\n
        `walert`: Set Walert key\n
    """

    def __init__(self):
        super().__init__()
        self.av = lib.keys_model.set_av_key
        self.binance = lib.keys_model.set_binance_key
        self.bitquery = lib.keys_model.set_bitquery_key
        self.cmc = lib.keys_model.set_cmc_key
        self.coinbase = lib.keys_model.set_coinbase_key
        self.coinglass = lib.keys_model.set_coinglass_key
        self.cpanic = lib.keys_model.set_cpanic_key
        self.degiro = lib.keys_model.set_degiro_key
        self.eodhd = lib.keys_model.set_eodhd_key
        self.ethplorer = lib.keys_model.set_ethplorer_key
        self.finnhub = lib.keys_model.set_finnhub_key
        self.fmp = lib.keys_model.set_fmp_key
        self.fred = lib.keys_model.set_fred_key
        self.get_keys_info = lib.keys_model.get_keys_info
        self.github = lib.keys_model.set_github_key
        self.glassnode = lib.keys_model.set_glassnode_key
        self.iex = lib.keys_model.set_iex_key
        self.messari = lib.keys_model.set_messari_key
        self.mykeys = lib.keys_model.get_keys
        self.news = lib.keys_model.set_news_key
        self.oanda = lib.keys_model.set_oanda_key
        self.polygon = lib.keys_model.set_polygon_key
        self.quandl = lib.keys_model.set_quandl_key
        self.reddit = lib.keys_model.set_reddit_key
        self.rh = lib.keys_model.set_rh_key
        self.santiment = lib.keys_model.set_santiment_key
        self.set_keys = lib.keys_model.set_keys
        self.shroom = lib.keys_model.set_shroom_key
        self.si = lib.keys_model.set_si_key
        self.smartstake = lib.keys_model.set_smartstake_key
        self.tokenterminal = lib.keys_model.set_tokenterminal_key
        self.tradier = lib.keys_model.set_tradier_key
        self.twitter = lib.keys_model.set_twitter_key
        self.walert = lib.keys_model.set_walert_key
