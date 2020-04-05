from collections import defaultdict
from typing import List
import requests
import logging
from tqdm import tqdm


class GoblineerUpdater(object):

    def __init__(self, oauth_client: str, oauth_secret: str, region: str, realm: str, locale: str):
        self.log = logging.getLogger(__name__)
        self.region = region
        self.realm = realm
        self.locale = locale
        self.auth_client = oauth_client
        self.auth_secret = oauth_secret
        self.api_base_url = f'https://{self.region}.api.blizzard.com'
        self.oauth_base_url = f'https://{self.region}.battle.net/oauth/token'
        self.token = self.get_oauth_token(self.auth_client, self.auth_secret, self.oauth_base_url)
        self.data = None

    def get_oauth_token(self, client_id: str, client_secret: str, url: str) -> str:
        """
        Fetches the OAuth token from the url.
        Reference: https://develop.battle.net/documentation/battle-net/oauth-apis

        Args:
            client_id: str: OAuth Client ID
            client_secret: str: OAuth Client Secret
            url: str: OAuth server URL, the default is the Blizzard OAuth Token URL

        Returns:
            str: The generated OAuth token

        Raises:
            TypeError: If the provided arguments are of the wrong type
            ValueError: If the data provided by the user is incorrect
            ConnectionError: Any other error that prevens connection to the API
        """

        # Type checking
        type_checks = [
            isinstance(client_id, str),
            isinstance(client_secret, str),
            isinstance(url, str)
        ]
        if not all(type_checks):
            raise TypeError

        # Executing the request
        data = {
            'grant_type': 'client_credentials'
        }

        try:
            response = requests.post(url, data=data, auth=(client_id, client_secret))
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError(
                f'Request make to Blizzard servers failed, are you sure you entered the correct client information? '
                f'Error: {err}', err)

        # Checking if the request is successful
        if response.status_code != 200:
            if response.status_code == 401:
                raise ValueError(
                    f'Invorrect client and/or secret. Please check that they are correct. '
                    f'HTTP error: {response.status_code}')
            else:
                raise ConnectionError(
                    f'Request to Blizzard servers failed, are you sure you entered the correct client information? '
                    f'HTTP error: {response.status_code}')

        # Returning the data
        return response.json()['access_token']

    def get_auction_data(self) -> List[dict]:
        self.data = self._get_auction_data(self.token, self.realm, self.locale)
        return self.data

    def _get_auction_data(self, token: str, realm: str, locale: str = 'en_US') -> List[dict]:
        """
        Fetches the auction data of the auction house data for a given region and realm

        Args:
            realm: str: The realm of the data
            locale: str: The locale the data should be in, default is en_US
            token: str: The oauth access token for the Blizzard API

        Returns:
            dict: The auction house data for the given realm

        Raises:
            TypeError: If the provided arguments are of the wrong type
            ValueError: If the data provided by the user is incorrect
            ConnectionError: Any other error that prevens connection to the API
        """

        # Type checking
        type_checks = [
            isinstance(token, str),
            isinstance(realm, str),
            isinstance(locale, str)
        ]
        if not all(type_checks):
            raise TypeError

        api_headers = {
            'Battlenet-Namespace': 'dynamic-eu',
            'Authorization': f'Bearer {token}'
        }
        params = {
            'locale': locale,
        }

        # Get connected realm id
        try:
            realm_api_url = f'{self.api_base_url}/data/wow/realm/{realm}'
            realm_resp = requests.get(realm_api_url, params=params, headers=api_headers)
            realm_json = realm_resp.json()

            conn_realm_url = realm_json['connected_realm']['href']
            conn_realm_resp = requests.get(conn_realm_url, params=params, headers=api_headers)
            conn_realm_json = conn_realm_resp.json()

        except requests.exceptions.ConnectionError as err:
            raise ConnectionError(
                f'Request to Blizzard servers failed, are you sure you entered the correct client information? '
                f'Error: {err}')

        # Get auction house data
        try:
            auction_api_url = conn_realm_json['auctions']['href']
            auction_resp = requests.get(auction_api_url, params=params, headers=api_headers)
            auction_json = auction_resp.json()
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError(
                f'Request to Blizzard servers failed, are you sure you entered the correct client information? '
                f'Error: {err}')

        # Checking if the request is successful
        if auction_resp.status_code != 200:
            if auction_resp.status_code == 401:
                raise ValueError('Invorrect client and/or secret. Please check that they are correct. HTTP error:', auction_resp.status_code)
            else:
                raise ConnectionError('Request make to Blizzard servers failed, are you sure you entered the correct client information? HTTP error:', auction_resp.status_code)

        # Returning the data
        return auction_json['auctions']

    def parse_auctions(self, auctions: List[dict]) -> dict:
        """
        Parses the auctions returned from the API

        Args:
            auctions: List[dict]: The auctions returned from the API

        Returns:
            dict: The parsed auctions

        Raises:
            TypeError: If the provided arguments are of the wrong type
        """

        # Type checking
        if not isinstance(auctions, list):
            raise TypeError

        # Parsing the auctions
        parsed_auctions = defaultdict(dict)
        for auc in tqdm(auctions):
            # The item won't be taken into account when it has no price
            if 'buyout' in auc and auc['buyout'] != 0:
                buy_price = auc['buyout']
            elif 'unit_price' in auc and auc['unit_price'] != 0:
                buy_price = auc['unit_price']
            else:
                # Skip this item
                continue

            # unit_price = buy_price / auc['quantity'] / 10000
            unit_price = buy_price / 10000

            # Creating the dictionary key with the item id and bonus ids
            item_id_tuple = (auc['item']['id'],)
            dict_key_list = list(item_id_tuple)

            if 'bonus_lists' in auc['item']:
                for bonus_id in auc['item']['bonus_lists']:
                    dict_key_list.append(bonus_id)

            dict_key = tuple(dict_key_list)

            # This will create a dict
            # the key is the unit price, the value is the number of times that unit_price appears
            if unit_price in parsed_auctions[dict_key]:
                parsed_auctions[dict_key][unit_price] += auc['quantity']
            else:
                parsed_auctions[dict_key][unit_price] = auc['quantity']

        return parsed_auctions
