import json
import pandas as pd
from pywebio.input import input, TEXT, checkbox
from pywebio.output import put_text, put_file, put_html, put_markdown
from pywebio.platform.flask import webio_view
from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from flask import Flask

app = Flask(__name__)


def get_data(api_key):
    """
    Takes API key and returns current data for top 100 cryptocurrencies by CoinMarketCap ranking.
    :param api_key: str
    :return: Pandas DataFrame
    """
    url = 'http://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    parameters = {
        'start': '1',
        # TODO: add option for user to override default limit of 100 rows.
        # 'limit': '1000',
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }

    session = Session()
    session.headers.update(headers)

    try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        # put_text(data)
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        put_text(e)

    df = pd.json_normalize(data['data'])
    return df


def clean_data(dataframe, columns):
    """
    Filters dataframe by columns and re-maps column names for legibility.
    :param dataframe: currency listings data as Pandas DataFrame
    :param columns: list of column names to filter
    :return: Pandas DataFrame, cleaned and filtered
    """
    columns.insert(0, 'id')
    df_cleaned = dataframe[columns]

    relabeling_map = {
        "symbol": "ticker",
        "num_market_pairs": "market_pairs",
        "circulating_supply": "circ_supply",
        "cmc_rank": "CMC_rank",
        "quote.USD.price": "price_USD",
        "quote.USD.volume_24h": "24h_volume",
        "quote.USD.volume_change_24h": "24h_volume_change",
        "quote.USD.percent_change_1h": "1h%",
        "quote.USD.percent_change_24h": "24h%",
        "quote.USD.percent_change_7d": "7d%",
        "quote.USD.percent_change_30d": "30d%",
        "quote.USD.percent_change_60d": "60d%",
        "quote.USD.percent_change_90d": "90d%",
        "quote.USD.market_cap": "market_cap",
        "quote.USD.market_cap_dominance": "market_cap_dominance",
        "quote.USD.fully_diluted_market_cap": "fully_diluted_market_cap",
        "quote.USD.last_updated": "last_updated"
    }

    df_cleaned = df_cleaned.rename(columns=relabeling_map)

    return df_cleaned


def get_ids(ticker_string, api_key):
    """
    CMC IDs are unique, while cryptocurrency ticker symbols are not necessarily unique. Get_ids() takes a list of
    ticker symbols and a CMC API key and returns a list of CMC IDs that may be longer.
    :param ticker_string:
    :param api_key:
    :return: list of IDs
    """
    ticker_string = ticker_string.replace(' ', '')

    url = 'http://pro-api.coinmarketcap.com/v1/cryptocurrency/map'
    parameters = {
        'symbol': ticker_string

    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }

    session = Session()
    session.headers.update(headers)

    try:
        response = session.get(url, params=parameters)
        id_map = json.loads(response.text)
    #       print(id_map)
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)

    cmc_ids = []
    for i in range(0, len(id_map['data'])):
        id = id_map['data'][i]['id']
        cmc_ids.append(id)

    return cmc_ids


def get_info(ticker_string, api_key, columns):
    """
    Generates cryptocurrency dataset based on user input specifications
    :param ticker_string: str containing digits or comma seperated ticker symbols
    :param api_key:
    :param columns: list of column names from checkbox input, configurable in 'checkbox_config.txt'
    :return: 3 outputs: unfiltered Pandas DataFrame with top 100 listings; filtered results as pandas DataFrame;
    filtered results as html (for display in browser)
    """
    df = get_data(api_key)
    df_cleaned = clean_data(df, columns)
    if type(ticker_string) is str:
        id_list = get_ids(ticker_string, api_key)
        info_df = df_cleaned[df_cleaned['id'].isin(id_list)]
    else:
        info_df = df_cleaned.head(ticker_string)
    info_html = info_df.to_html(index=False)
    return df, info_df, info_html


def task_func():
    """
    Runs tasks and callbacks based on user input
    :return:
    """
    put_markdown('# CryptoTableMaker')
    put_markdown('A simple web app for generating lightly customizable tables from CoinMarketCap data. Results can be '
                 'viewed in the browser and downloaded as .csv files. The app requires an API key, which can be '
                 'acquired here: https://coinmarketcap.com/api/. CryptoTableMaker works (for now) with a free Basic '
                 'account. This site is not affiliated with CoinMarketCap and should  be used in accordance with all '
                 'Terms of Service agreements.')

    api_key = input("Enter CoinMarketCap API key：", type=TEXT, required=True)

    ticker_string = input("Enter cryptocurrency ticker symbols, seperated by commas (e.g. BTC, ETH, BNB). Or enter n "
                          "between 1 and 100 for top n listings (e.g. 50).",
                          type=TEXT, required=True)
    if ticker_string.isdigit():
        ticker_string = int(ticker_string)

    with open('checkbox_config.txt', 'r') as f:
        checkbox_config = json.load(f)
    column_ids = checkbox(label="Select columns:", options=checkbox_config)

    df, info_df, info_html = get_info(ticker_string, api_key, column_ids)
    put_html(info_html)
    put_text('Download current, filtered results as a .csv file:')
    info_csv = info_df.to_csv(index=False).encode('utf-8')
    put_file('CMC_filtered.csv', info_csv, 'Download filtered')
    put_text('Download top 100 current, unfiltered CoinMarketCap listings as a .csv file: ')
    unfiltered_csv = df.to_csv(index=True).encode('utf-8')
    put_file('CMC_unfiltered.csv', unfiltered_csv, 'Download unfiltered')


app.add_url_rule('/', 'webio_view', webio_view(task_func),
                 methods=['GET', 'POST', 'OPTIONS'])

if __name__ == '__main__':
    app.run(debug=True)
