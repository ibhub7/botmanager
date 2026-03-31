# Telegram Bot Status Monitor

A professional status monitor that pings your bots hosted on Koyeb/Render and updates a live status message in a Telegram channel.

## Features
- **Auto-Update**: Edits a single message every 5 minutes.
- **Persistent Storage**: Uses MongoDB to store your bot list.
- **Timezone Support**: Displays updates in Asia/Kolkata time.
- **Clean UI**: Minimalist status report without messy URLs.

## Commands (Private Chat)
- `/addbot "Bot Name" URL` - Add a new bot (use quotes for names with spaces).
- `/removebot "Bot Name"` - Remove a bot from monitoring.

## Deployment
1. Set up a MongoDB Atlas cluster.
2. Get your `API_ID` and `API_HASH` from my.telegram.org.
3. Deploy to Koyeb using the provided `Dockerfile`.
4. Set all Environment Variables in the Koyeb dashboard.
