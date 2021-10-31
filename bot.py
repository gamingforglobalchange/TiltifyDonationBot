import asyncio
import json
import requests
from twitchio.ext import commands
import time

tiltify_access_token = "TILTIFY ACCESS TOKEN HERE"
tiltify_username = "TILTIFY USERNAME HERE"
tiltify_campaign_slug = "TILTIFY CAMPAIGN SLUG HERE"

twitch_channel_names = ["TWITCH CHANNEL NAME HERE"] # This is the list of channel names where you want to send the alerts to.
twitch_bot_username = "TWITCH BOT USERNAME HERE" # This is the channel name of the bot account sending the alerts.
twitch_client_id = "TWITCH CLIENT ID HERE"
twitch_oauth_token = "TWITCH OAUTH TOKEN HERE"

#  Twitch bot class
channels = None
message_list = []

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            client_id=twitch_client_id,
            token=twitch_oauth_token,
            nick=twitch_bot_username, prefix='!',
            initial_channels=twitch_channel_names
        )
        self.loop.create_task(self.process_tiltify_api_call())

    async def event_ready(self):
        global channels
        channels = list(map(lambda c : self.get_channel(c), twitch_channel_names))
        print ("Bot ready.")

    async def process_tiltify_api_call(self):
        while True:
            await asyncio.sleep(5)
            if init_tiltify_api_call():
                # Please note that this will send all messages in the list at once. Twitch's v5 API has a rate limit of 800 requests per minute (with OAuth).
                for message in message_list:
                    for channel in channels:
                        await channel.send(message)

# Tiltify API calls
tiltify_latest_saved_donation_ids = []
def init_tiltify_api_call():
    global message_list, tiltify_latest_saved_donation_ids

    # Grab campaign ID from campaign slug and Tiltify user.
    api_endpoint = f"https://tiltify.com/api/v3/users/{tiltify_username.lower()}/campaigns/{tiltify_campaign_slug.lower()}"
    head = {'Authorization': 'Bearer ' + tiltify_access_token}
    r = requests.get(url = api_endpoint, headers = head)
    tiltify_campaign_id = str(r.json()['data']['id'])

    # Grab donations from campaign ID.
    api_endpoint = f"https://tiltify.com/api/v3/campaigns/{tiltify_campaign_id}/donations"
    head = {'Authorization': 'Bearer ' + tiltify_access_token}
    r = requests.get(url = api_endpoint, headers = head)

    tiltify_recent_donation_data = r.json()['data']
    current_timestamp = time.time()

    # Making sure we don't send duplicates in chat: one is storage-based (main check), the other is timestamp-based (prevents double-sending upon initial run).
    # I've decided on 6s (technically 5.999s) because it covers two edge cases: a) donation received 1ms after 5000ms check, b) local clock inaccuracy up to 1000ms.
    # If you have an idea how to streamline this into one check while still covering these edge cases, open an issue or pull request with your suggestion!
    for donation in reversed(tiltify_recent_donation_data):       
        if donation['id'] not in tiltify_latest_saved_donation_ids and current_timestamp - donation['completedAt']/1000 < 6:
            tiltify_latest_saved_donation_ids.append(donation['id'])
            
            formatted_donation_total = str("${:,.2f}".format(int(donation['amount'])))
            message = f"We have a {formatted_donation_total} donation from {donation['name']}"

            # Only say there's a comment if there actually is one
            if donation['comment'] != "None":
                message += f" with the comment \"{donation['comment']}\""

            message_list.append(message)

        # If there are no new donations, make sure to clear the message list to ensure there are no duplicate sends.
        else:
            message_list = []
    
    # If the message list is empty, that means there are no new donations. If it's not empty, then there are new donations.
    if not message_list: return False
    else: return True

# Run the Twitch bot.
bot = Bot()
bot.run()