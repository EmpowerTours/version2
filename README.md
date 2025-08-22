# EmpowerTours Version 2

Upgraded version of EmpowerTours with Reown for wallet connections, Envio for real-time indexing and dashboard, 0x Swap API for token swaps, Para for $TOURS transactions via iOS App Clip, and music NFT fetching/playback from Monad blockchain. The 1 MON profile creation fee remains unchanged, and the bot can fetch/play music NFTs (small files as base64, large via Pinata links) after verifying ownership.

## Setup
1. Clone the repo: `git clone https://github.com/yourusername/version2.git`
2. Copy files from `EmpowerTours/version1` and apply the modifications below.
3. Create a new Telegram bot via BotFather; get new `TELEGRAM_TOKEN` and update `.env`.
4. Create a new Railway project, link to `version2` repo, and deploy (uses `Procfile`).
5. Add env vars in Railway:
   - `TELEGRAM_TOKEN` (new bot)
   - `MONAD_RPC_URL=https://testnet-rpc.monad.xyz`
   - `CONTRACT_ADDRESS` (EmpowerTours contract)
   - `TOURS_TOKEN_ADDRESS`
   - `OWNER_ADDRESS`
   - `WALLET_CONNECT_PROJECT_ID` (from https://cloud.walletconnect.com for Reown)
   - `0X_API_KEY` (from https://dashboard.0x.org for 0x Swap)
   - `PARA_API_KEY` (from https://developer.getpara.com for Para)
   - `ENVIO_GRAPHQL_URL` (from your Envio instance)
   - `MUSIC_NFT_ADDRESS` (deployed MusicNFT contract)
   - `PINATA_JWT` (from https://pinata.cloud, optional for Farcaster uploads)
6. Deploy Envio indexer on a separate server (e.g., DigitalOcean VPS): Install Envio CLI (`npm i -g @envio-dev/envio`), create project dir, add `indexer.yaml` and `handlers.js`, run `envio start`. Update `ENVIO_GRAPHQL_URL` to the instance URL (e.g., http://your-vps:4000/graphql).
7. For iOS App Clip: On macOS (cloud Mac or VM), open Xcode 16+, create App Clip project, add Podfile, run `pod install`, paste `ViewController.swift`, build, and test on iPhone 11 Pro Max (iOS 15+).
8. Deploy MusicNFT contract on Monad Testnet via Remix[](https://remix.ethereum.org), update `MUSIC_NFT_ADDRESS`.

## Features
- **Profile Creation**: `/createprofile` with 1 MON fee, signed via Reown.
- **$TOURS Transactions**: `/buytours <amount>` triggers Para App Clip or Reown web for swaps/purchases via 0x.
- **Music NFT Playback**: `/play <song_id>` fetches from Monad (verifies ownership, plays base64 or Pinata link).
- **Dashboard**: `/dashboard` shows real-time txs, music NFTs (indexed by Envio).
- **Reown**: Wallet connect in `miniapp.html` and `connect.html`.
- **0x Swap**: Backend endpoint for swapping to $TOURS.
- **Envio**: Indexes events for dashboard.
- **Para**: iOS App Clip for $TOURS txs.

## Testing
- Set webhook: `curl "https://api.telegram.org/bot<NEW_TOKEN>/setWebhook?url=https://your-railway-app.up.railway.app/webhook"`
- Commands: `/createprofile` (check fee tx), `/buytours 10` (Para/Reown/0x), `/play 1` (music NFT).
- Music: Mint on Farcaster (use upload script), play in bot.
- iPhone: Invoke App Clip via QR/link for $TOURS; extend for music if needed.
- Dashboard: Access `/dashboard` in browser or Telegram webview.

## Notes
- iPhone 11 Pro Max (64GB): Ensure ~1GB free; update to iOS 15+.
- Farcaster Music App: Use upload script for minting; integrate with frames for UI.
- No disruption to version1: New bot, new Railway.
- Costs: Free for testnet; Pinata ~$0.15/GB storage.

Contact: support@reown.com, support@envio.dev, support@0x.org, support@getpara.com, support@pinata.cloud, empowertours@gmail.com
