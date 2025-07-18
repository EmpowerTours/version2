<div align="center">
  <img src="https://raw.githubusercontent.com/EmpowerTours/version1/main/public/IMG_3466.jpg" alt="EmpowerTours Logo" width="300" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
  <h1 style="color: #FF4500; font-family: 'Arial Black', sans-serif; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">EmpowerTours</h1>
  <p style="font-size: 1.2em; color: #333; max-width: 800px; margin: 0 auto;">🧗 Web3-Powered Rock Climbing Adventures & Community – Conquer Peaks, Earn Tokens, Build Routes on Monad Blockchain!</p>
  
  [![Monad Testnet](https://img.shields.io/badge/Blockchain-Monad%20Testnet-orange?style=for-the-badge&logo=ethereum)](https://monad.xyz)
  [![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/empowertoursbot)
  [![Community Chat](https://img.shields.io/badge/Chat-Join%20Now-green?style=for-the-badge&logo=telegram)](https://t.me/empowertourschat)
  [![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)
  [![Open to Investors](https://img.shields.io/badge/Invest-Open%20to%20Angels-yellow?style=for-the-badge&logo=bitcoin)](mailto:earvin@empowertours.com)

</div>

---

### 🚀 Quick Start
Launch the bot: [@empowertoursbot](https://t.me/AI_RobotExpert_bott)  
Join the community: [@empowertourschat](https://t.me/empowertourschat)  
Faucet $MON: [Monad Faucet](https://testnet.monad.xyz/faucet)  

<details>
<summary><b>🌟 Why EmpowerTours? (Click to Expand)</b></summary>
<div style="background-color: #f9f9f9; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">

- **Journal Climbs 🗒️**: Log ascents with photos, GPS, notes – earn 5 $TOURS per entry!
- **Build & Buy Routes 🪨**: Create/share custom climbs (10 $TOURS cost) or purchase (10 $TOURS to creator).
- **Tournaments 🏆**: Compete for $TOURS pots – entry fees build the prize!
- **Web3 Incentives 💰**: Transparent fees, on-chain events, Monad speed.
- **Community Vibes 👥**: Telegram chat for tips, meets, collabs.

</div>
</details>

---

### 🔧 Technologies & Stack
<div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 10px;">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100-green?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Web3.py-6.0-orange?style=flat-square&logo=ethereum" alt="Web3.py">
  <img src="https://img.shields.io/badge/PostgreSQL-15-blue?style=flat-square&logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Solidity-0.8-black?style=flat-square&logo=solidity" alt="Solidity">
  <img src="https://img.shields.io/badge/Telegram-Bot_API-cyan?style=flat-square&logo=telegram" alt="Telegram">
</div>

**Contract Addresses (Monad Testnet):**
- **EmpowerTours:** `0xB69D011496B7d7a5e5B3D0021dBF4468b0050AB6`
- **$TOURS Token:** `0x2Da15A8B55BE310A7AB8EB0010506AB30CD6CBcf` 
- **Owner Wallet:** 0x5fE8373C839948bFCB707A8a8A75A16E2634A725` (90% fees for dev/ops)
- **Legacy Wallet:** `0x3de6FCEECd5d05363D80A77963Edd3787c96E593` (10% fees for maintenance)
- **RPC:** https://testnet-rpc.monad.xyz
- **Explorer:** https://testnet.monadexplorer.com

---

### 📖 How It Works
<details>
<summary><b>🧑‍💻 User Journey (Interactive Flow)</b></summary>
<ol style="list-style-type: none; padding: 0;">
  <li style="background: linear-gradient(to right, #FF4500, #FFA500); color: white; padding: 10px; margin: 5px 0; border-radius: 5px;">/start – Welcome & join chat 🏞️</li>
  <li style="background: linear-gradient(to right, #FF4500, #FFA500); color: white; padding: 10px; margin: 5px 0; border-radius: 5px;">/connectwallet – Link MetaMask (Chain ID 10143)</li>
  <li style="background: linear-gradient(to right, #FF4500, #FFA500); color: white; padding: 10px; margin: 5px 0; border-radius: 5px;">/createprofile – Sign tx (1 $MON fee, earn 1 $TOURS)</li>
  <li style="background: linear-gradient(to right, #FF4500, #FFA500); color: white; padding: 10px; margin: 5px 0; border-radius: 5px;">Explore: /journal, /buildaclimb, /purchaseclimb...</li>
  <li style="background: linear-gradient(to right, #FF4500, #FFA500); color: white; padding: 10px; margin: 5px 0; border-radius: 5px;">Tournaments: Create/Join/End for $TOURS pots</li>
</ol>
</details>

<details>
<summary><b>🔗 Backend & Blockchain Flow</b></summary>
- **Bot:** Processes commands, builds unsigned tx.
- **API:** Handles wallet/tx submission.
- **DB:** Sessions, pendings (expires 30min).
- **Monitoring:** Events polled every 30s; notifies chat/users.
- **Fees in Tournaments:** 100% of entry fees ($TOURS) go to pot; winner receives full pot on end (no cuts).
</details>

---

### 📋 Commands & Usage
<table style="width:100%; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
  <thead>
    <tr style="background-color: #FF4500; color: white;">
      <th style="padding: 10px; text-align: left;">Command</th>
      <th style="padding: 10px; text-align: left;">Description</th>
      <th style="padding: 10px; text-align: left;">Cost/Reward</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background-color: #f9f9f9;">
      <td>/start</td>
      <td>Welcome message</td>
      <td>Free</td>
    </tr>
    <tr>
      <td>/tutorial</td>
      <td>Setup guide</td>
      <td>Free</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/connectwallet</td>
      <td>Link wallet</td>
      <td>Free</td>
    </tr>
    <tr>
      <td>/createprofile</td>
      <td>Create profile</td>
      <td>1 $MON (earn 1 $TOURS)</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/buyTours <amount></td>
      <td>Buy $TOURS</td>
      <td>1 $MON per $TOURS</td>
    </tr>
    <tr>
      <td>/sendTours <recipient> <amount></td>
      <td>Send $TOURS</td>
      <td>Gas only</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/journal <entry></td>
      <td>Log climb</td>
      <td>Earn 5 $TOURS</td>
    </tr>
    <tr>
      <td>/comment <id> <comment></td>
      <td>Comment on journal</td>
      <td>0.1 $MON</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/buildaclimb <name> <difficulty></td>
      <td>Create route</td>
      <td>10 $TOURS</td>
    </tr>
    <tr>
      <td>/purchaseclimb <id></td>
      <td>Buy route</td>
      <td>10 $TOURS (to creator)</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/findaclimb</td>
      <td>List climbs</td>
      <td>Free</td>
    </tr>
    <tr>
      <td>/viewclimb <id></td>
      <td>Climb details</td>
      <td>Free</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/mypurchases</td>
      <td>Your purchases</td>
      <td>Free</td>
    </tr>
    <tr>
      <td>/journals</td>
      <td>List entries</td>
      <td>Free</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/viewjournal <id></td>
      <td>Entry + comments</td>
      <td>Free</td>
    </tr>
    <tr>
      <td>/createtournament <fee></td>
      <td>Start tournament</td>
      <td>Free (gas)</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/tournaments</td>
      <td>List tournaments</td>
      <td>Free</td>
    </tr>
    <tr>
      <td>/jointournament <id></td>
      <td>Join</td>
      <td>Entry fee $TOURS (to pot)</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/endtournament <id> <winner></td>
      <td>End (owner)</td>
      <td>Free; pot to winner</td>
    </tr>
    <tr>
      <td>/balance</td>
      <td>Check balances</td>
      <td>Free</td>
    </tr>
    <tr style="background-color: #f9f9f9;">
      <td>/help</td>
      <td>Command list</td>
      <td>Free</td>
    </tr>
  </tbody>
</table>

---

### 💰 Costs, Fees & Transparency
<details>
<summary><b>📊 Fee Breakdown (All On-Chain)</b></summary>
<ul>
  <li><b>Profiles/Comments/Buy $TOURS:</b> 90% to OWNER_ADDRESS (dev/ops), 10% to LEGACY_ADDRESS (maintenance).</li>
  <li><b>Build/Purchase Climbs:</b> 100% TOURS to contract/creator.</li>
  <li><b>Tournaments:</b> 100% entry fees ($TOURS) go to pot; winner gets full pot (no cuts).</li>
  <li><b>Rewards:</b> From contract pool (prefunded).</li>
  <li><b>Gas:</b> ~0.001-0.01 $MON/tx.</li>
  <li><b>Audit:</b> Explorer links; events for all actions.</li>
</ul>
</details>

<details>
<summary><b>⚡ Response Times</b></summary>
- Commands: 1-5s
- Tx Confirm: 1-10s (Monad)
- Events: ~30s poll
- Overall: <10s typical
</details>

---

### 🔮 Future Features
- **3D World Map 🌍**: Interactive 3D globe for climb locations – zoom, explore perspectives with Three.js.
- Farcaster enhancements, NFTs, leaderboards, AR mobile app, mainnet.

Open to angel investors – contact Earvin Gallardo.

---

### ⚠️ Risks & Disclaimer
Testnet only. No liability for damages. Proprietary – see License.

## License

Copyright © 2025 Earvin Gallardo. All rights reserved.

This software is proprietary and confidential. You may not copy, modify, publish, use, compile, sell, or distribute this software, either in source code form or as a compiled binary, for any purpose, commercial or non-commercial, without explicit written permission from Earvin Gallardo.

The name "EmpowerTours" is a trademark owned by Earvin Gallardo. Use of the "EmpowerTours" brand, name, or any related trademarks requires a rental license agreement and payment of applicable fees. Unauthorized use is prohibited and subject to trademark and copyright laws.

Commercial use of this software or any derivative works is strictly prohibited without a valid license. Violations may result in legal action.

THIS SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL EARVIN GALLARDO BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Earvin Gallardo owns the entity in its entirety, including all intellectual property rights. For licensing inquiries, investment opportunities, or permissions, contact Earvin Gallardo directly.

© 2025 EmpowerTours. Built with xAI & Monad. Join the adventure! 🧗
