# EMAIL
# https://realpython.com/python-send-email/

from telethon.sync import TelegramClient, events

with TelegramClient('name', CREDS["username"], api_hash=CREDS["password"]) as client:
   client.send_message('me', 'Hello, myself!')
   print(client.download_profile_photo('me'))

   @client.on(events.NewMessage(pattern='(?i).*Hello'))
   async def handler(event):
      await event.reply('Hey!')

   client.run_until_disconnected()