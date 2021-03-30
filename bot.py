import asyncio
import json
import requests
from twitchio.ext import commands
import time

tiltify_auth_token = "TILTIFY AUTH TOKEN HERE"
tiltify_username = "TILTIFY USERNAME HERE" # Username must be in all lowercase!
tiltify_campaign_slug = "TILTIFY CAMPAIGN SLUG HERE" # Campaign slug must be in all lowercase!

twitch_channel_name = "TWITCH CHANNEL NAME HERE" # This is the channel name of where you want to send the alerts to.
twitch_bot_username = "TWITCH BOT USERNAME HERE" # This is the channel name of the bot account sending the alerts.
twitch_client_id = "TWITCH CLIENT ID HERE"
twitch_oauth_token = "TWITCH OAUTH TOKEN HERE"

#  Twitch bot class
channel = None
message_list = []

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(client_id=twitch_client_id, irc_token=twitch_oauth_token, nick=twitch_bot_username, prefix='!', initial_channels=[twitch_channel_name])
        self.loop.create_task(self.process_tiltify_api_call())

    async def event_ready(self):
        global channel
        channel = self.get_channel(twitch_channel_name)
        print ("Bot ready.")

    async def process_tiltify_api_call(self):
        while True:
            await asyncio.sleep(5)
            if init_tiltify_api_call():
                # Please note that this will send all messages in the list at once. Twitch's v5 API has a rate limit of 800 requests per minute (with OAuth).
                for x in message_list:         
                    await channel.send(x)

# Tiltify API calls
tiltify_latest_saved_donation_ids = []
def init_tiltify_api_call():
    global message_list, tiltify_latest_saved_donation_ids

    # Grab campaign ID from campaign slug and Tiltify user.
    api_endpoint = f"https://tiltify.com/api/v3/users/{tiltify_username}/campaigns/{tiltify_campaign_slug}"
    head = {'Authorization': 'Bearer ' + tiltify_auth_token}
    r = requests.get(url = api_endpoint, headers = head)
    tiltify_campaign_id = str(r.json()['data']['id'])

    # Grab donations from campaign ID.
    api_endpoint = f"https://tiltify.com/api/v3/campaigns/{tiltify_campaign_id}/donations"
    head = {'Authorization': 'Bearer ' + tiltify_auth_token}
    r = requests.get(url = api_endpoint, headers = head)

    tiltify_recent_donation_data = r.json()['data']
    current_timestamp = time.time()

    # Making sure we don't send duplicates in chat: one is storage-based (main check), the other is timestamp-based (prevents double-sending upon initial run).
    # I've decided on 6s (6000ms) because it covers two edge cases: a) donation received 1ms after 5000ms check, b) local clock inaccuracy up to 1001ms.
    # If you have an idea how to streamline this into one check while still covering these edge cases, open an issue or pull request with your suggestion!
    for x in reversed(tiltify_recent_donation_data):       
        if x['id'] not in tiltify_latest_saved_donation_ids and current_timestamp - x['completedAt']/1000 < 90000:
            tiltify_latest_saved_donation_ids.append(x['id'])
            
            formatted_donation_total = str("${:,.2f}".format(int(x['amount'])))
            message = f"We have a {formatted_donation_total} donation from {x['name']}"

            # Only say there's a comment if there actually is one
            if x['comment'] != "":
                message += f" with the comment \"{x['comment']}\""

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