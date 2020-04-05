from dotenv import load_dotenv
from os import getenv, path
from tqdm import tqdm
from json import dumps, dump

from .marketvalue import marketvalue
from .printer import start_process_print, success_process_print
from .update import GoblineerUpdater


def main():
    # Loading the environmental variables
    load_dotenv()

    updater_settings = {
        'oauth_client': getenv('OAUTH_CLIENT'),
        'oauth_secret': getenv('OAUTH_SECRET'),
        'region': getenv('REGION'),
        'realm': getenv("REALM"),
        'locale': getenv("LOCALE")
    }

    # Get updater instance and the OAuth token from Blizzard's API
    start_process_print("Preparing Updater and getting OAuth token")
    updater = GoblineerUpdater(**updater_settings)
    success_process_print("Preparing Updater and getting OAuth token")

    # Getting the Auction House Data
    start_process_print("Getting the Auction House data (may take some time based on your internet speed)")
    auction_data = updater.get_auction_data()
    success_process_print("Getting the Auction House data (may take some time based on your internet speed)")

    # Parsing the Auctions
    print("\nParsing the data")
    parsed_auctions = updater.parse_auctions(auction_data)

    # Calculating the marketvalues
    print("\nCalculating marketvalues")
    marketvalues = []
    for item_ids, item_data in tqdm(parsed_auctions.items()):
        marketvalue_data = marketvalue(item_data)
        marketvalues.append({
            'item': item_ids[0],
            'bonusIds': item_ids[1:],
            'marketvalue': str(marketvalue_data['marketvalue']),
            'quantity': str(marketvalue_data['quantity']),
            'MIN': str(marketvalue_data['MIN'])
        })
    print("\n")

    # Writing the marketvalues to the Addon's file
    start_process_print("Writing marketvalues to file")
    data_path = path.join(getenv('WOW_DIRECTORY'), '_retail_', 'Interface', 'AddOns', 'Goblineer', 'data.lua')

    with open(data_path, 'w') as f:
        f.write("goblineer_data = [" + dumps(marketvalues, separators=(',', ':')) + "]")
    success_process_print("Writing marketvalues to file")

    print('\nDone!')


if __name__ == "__main__":
    main()
