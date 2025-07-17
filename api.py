from fastapi import FastAPI, HTTPException
from socketio import AsyncServer, ASGIApp
from pydantic import BaseModel
import sqlite3
import json
import uuid
import logging
import aiohttp
from web3 import Web3
from dotenv import load_dotenv
import os
from contract import broadcast_transaction
import time  # For expiry

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
MONAD_RPC_URL = os.getenv("MONAD_RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
TOURS_TOKEN_ADDRESS = os.getenv("TOURS_TOKEN_ADDRESS")
WALLET_CONNECT_PROJECT_ID = os.getenv("WALLET_CONNECT_PROJECT_ID")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_HANDLE = "@empowertourschat"
EXPIRY_SECONDS = 1800  # 30 minutes

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(MONAD_RPC_URL))

# Assume contract ABI (stubbed; replace with actual from contract.py)
CONTRACT_ABI = []  # Full ABI here
TOURS_ABI = []  # Full ABI here
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
tours_contract = w3.eth.contract(address=TOURS_TOKEN_ADDRESS, abi=TOURS_ABI)

# Initialize FastAPI and SocketIO
app = FastAPI()
sio = AsyncServer(async_mode='asgi', cors_allowed_origins="*")
app.mount("/socket.io", ASGIApp(sio))

# Initialize SQLite database
conn = sqlite3.connect('empowertours.db')
cursor = conn.cursor()

# Existing tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        user_id TEXT PRIMARY KEY,
        session_id TEXT,
        wallet_address TEXT,
        connected_at INTEGER  -- Timestamp for expiry
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS pending_txs (
        user_id TEXT,
        tx_type TEXT,
        tx_data TEXT,
        name TEXT,
        difficulty TEXT,
        latitude INTEGER,
        longitude INTEGER,
        photo_hash TEXT,
        location_id INTEGER,
        tournament_id INTEGER,
        UNIQUE(user_id, tx_type)  -- Prevent duplicates
    )
''')

# New tables for features
cursor.execute('''
    CREATE TABLE IF NOT EXISTS climbs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_user_id TEXT,
        title TEXT,
        description TEXT,
        picture_url TEXT,  -- Encrypted
        location TEXT,     -- Encrypted (JSON: {'lat': float, 'lon': float})
        price_tours INTEGER,
        created_at INTEGER
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        climb_id INTEGER,
        buyer_user_id TEXT,
        purchased_at INTEGER
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS journals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        climb_id INTEGER,
        user_id TEXT,
        entry_text TEXT,
        date INTEGER
    )
''')
conn.commit()

# Simple encryption (XOR with key; replace with better e.g., cryptography.fernet)
ENCRYPT_KEY = b'secret_key'  # Use env var in prod
def encrypt(data: str) -> str:
    return ''.join(chr(ord(c) ^ ENCRYPT_KEY[i % len(ENCRYPT_KEY)]) for i, c in enumerate(data))

def decrypt(data: str) -> str:
    return encrypt(data)  # XOR is symmetric

class ConnectRequest(BaseModel):
    user_id: str

class WalletRequest(BaseModel):
    telegramUserId: str
    walletAddress: str

class SignRequest(BaseModel):
    user_id: str
    tx_data: dict

class BroadcastRequest(BaseModel):
    telegramUserId: str
    signedTxHex: str

class HashRequest(BaseModel):  # New for automated submission
    telegramUserId: str
    txHash: str

class BuildClimbRequest(BaseModel):
    user_id: str
    title: str
    description: str
    picture_url: str
    location: dict  # {'lat': float, 'lon': float}
    price_tours: int

class PurchaseClimbRequest(BaseModel):
    user_id: str
    climb_id: int

class JournalRequest(BaseModel):
    user_id: str
    climb_id: int
    entry_text: str

@app.post("/connect")
async def connect_wallet(request: ConnectRequest):
    try:
        session_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT OR REPLACE INTO sessions (user_id, session_id, wallet_address, connected_at) VALUES (?, ?, ?, ?)",
            (request.user_id, session_id, None, int(time.time()))
        )
        conn.commit()
        return {"session_id": session_id}
    except Exception as e:
        logger.error(f"Error in /connect: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/wallet")
async def set_wallet(request: WalletRequest):
    try:
        # Check if already connected and not expired
        cursor.execute("SELECT connected_at FROM sessions WHERE user_id = ?", (request.telegramUserId,))
        row = cursor.fetchone()
        if row and time.time() - row[0] < EXPIRY_SECONDS:
            return {"status": "already_connected"}

        cursor.execute(
            "UPDATE sessions SET wallet_address = ?, connected_at = ? WHERE user_id = ?",
            (request.walletAddress, int(time.time()), request.telegramUserId)
        )
        conn.commit()
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": request.telegramUserId,
                    "text": f"Wallet connected: {request.walletAddress}! 🎉 Use /createprofile to join.",
                    "parse_mode": "HTML"
                }
            )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error in /wallet: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sign")
async def sign_transaction(request: SignRequest):
    try:
        # Prevent double: Check pending
        cursor.execute("SELECT 1 FROM pending_txs WHERE user_id = ?", (request.user_id,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Transaction already pending")

        # Insert pending (assuming tx_data includes all fields)
        cursor.execute(
            "INSERT INTO pending_txs (user_id, tx_type, tx_data) VALUES (?, ?, ?)",
            (request.user_id, 'transfer', json.dumps(request.tx_data))  # Simplify; add fields as needed
        )
        conn.commit()

        await sio.emit('sign_tx', {
            'user_id': request.user_id,
            'tx_data': request.tx_data
        })
        return {"status": "sent"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Duplicate transaction type pending")
    except Exception as e:
        logger.error(f"Error in /sign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/broadcast")
async def broadcast_transaction_endpoint(request: BroadcastRequest):
    try:
        # Check connection expiry
        cursor.execute("SELECT connected_at FROM sessions WHERE user_id = ?", (request.telegramUserId,))
        row = cursor.fetchone()
        if not row or time.time() - row[0] > EXPIRY_SECONDS:
            raise HTTPException(status_code=401, detail="Session expired; reconnect wallet")

        cursor.execute(
            "SELECT tx_type, name, difficulty, location_id, tournament_id FROM pending_txs WHERE user_id = ? ORDER BY ROWID DESC LIMIT 1",
            (request.telegramUserId,)
        )
        pending_tx = cursor.fetchone()
        if not pending_tx:
            raise HTTPException(status_code=404, detail="No pending transaction found")
        
        tx_type, name, difficulty, location_id, tournament_id = pending_tx
        result = await broadcast_transaction(
            signed_tx_hex=request.signedTxHex,
            pending_tx={
                'tx_type': tx_type,
                'wallet_address': cursor.execute("SELECT wallet_address FROM sessions WHERE user_id = ?", (request.telegramUserId,)).fetchone()[0],
                'name': name,
                'difficulty': difficulty,
                'location_id': location_id,
                'tournament_id': tournament_id
            },
            user={'id': request.telegramUserId, 'first_name': 'User', 'username': f"user_{request.telegramUserId}"},
            context=None
        )
        
        tx_hash = result.get('tx_hash', '')
        explorer_url = f"https://testnet.monadexplorer.com/tx/{tx_hash}"
        
        if result['status'] == 'success':
            async with aiohttp.ClientSession() as session:
                user_msg = f"Transaction confirmed! <a href='{explorer_url}'>Tx: {tx_hash}</a> 🪙 Action completed."
                user_resp = await session.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": request.telegramUserId,
                        "text": user_msg,
                        "parse_mode": "HTML"
                    }
                )
                if 'group_message' in result:
                    group_msg = f"New activity by {result.get('username', 'user')} on EmpowerTours! 🧗 <a href='{explorer_url}'>Tx: {tx_hash}</a>"
                    group_resp = await session.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": CHAT_HANDLE,
                            "text": group_msg,
                            "parse_mode": "HTML"
                        }
                    )
                    if not group_resp.json().get('ok'):
                        logger.error(f"Group notification failed: {group_resp.json()['description']}")
        else:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": request.telegramUserId,
                        "text": result['message'],
                        "parse_mode": "HTML"
                    }
                )
        return {"tx_hash": tx_hash, "status": result['status']}
    except Exception as e:
        logger.error(f"Error in /broadcast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit_hash")  # New: For automated frontend submission
async def submit_tx_hash(request: HashRequest):
    try:
        # Check expiry as above
        cursor.execute("SELECT connected_at FROM sessions WHERE user_id = ?", (request.telegramUserId,))
        row = cursor.fetchone()
        if not row or time.time() - row[0] > EXPIRY_SECONDS:
            raise HTTPException(status_code=401, detail="Session expired; reconnect wallet")

        # Confirm tx
        receipt = w3.eth.wait_for_transaction_receipt(request.txHash, timeout=120)
        if receipt.status != 1:
            raise HTTPException(status_code=400, detail="Transaction failed")

        # Clear pending
        cursor.execute("DELETE FROM pending_txs WHERE user_id = ?", (request.telegramUserId,))
        conn.commit()

        explorer_url = f"https://testnet.monadexplorer.com/tx/{request.txHash}"
        async with aiohttp.ClientSession() as session:
            user_msg = f"Transaction confirmed automatically! <a href='{explorer_url}'>Tx: {request.txHash}</a> 🪙 Action completed."
            await session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": request.telegramUserId,
                    "text": user_msg,
                    "parse_mode": "HTML"
                }
            )
            # Group notification similar to above
            group_msg = f"New activity on EmpowerTours! 🧗 <a href='{explorer_url}'>Tx: {request.txHash}</a>"
            group_resp = await session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": CHAT_HANDLE,
                    "text": group_msg,
                    "parse_mode": "HTML"
                }
            )
            if not group_resp.json().get('ok'):
                logger.error(f"Group notification failed: {group_resp.json()['description']}")
        return {"status": "success", "tx_hash": request.txHash}
    except Exception as e:
        logger.error(f"Error in /submit_hash: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# New endpoints for features

@app.post("/build_climb")
async def build_climb(request: BuildClimbRequest):
    try:
        enc_picture = encrypt(request.picture_url)
        enc_location = encrypt(json.dumps(request.location))
        cursor.execute(
            "INSERT INTO climbs (creator_user_id, title, description, picture_url, location, price_tours, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (request.user_id, request.title, request.description, enc_picture, enc_location, request.price_tours, int(time.time()))
        )
        conn.commit()
        return {"status": "success", "climb_id": cursor.lastrowid}
    except Exception as e:
        logger.error(f"Error in /build_climb: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_climbs")
async def get_climbs():
    try:
        cursor.execute("SELECT id, title, description, price_tours FROM climbs")
        climbs = [{"id": row[0], "title": row[1], "desc": row[2], "price": row[3]} for row in cursor.fetchall()]
        return {"climbs": climbs}
    except Exception as e:
        logger.error(f"Error in /get_climbs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/purchase_climb")
async def purchase_climb(request: PurchaseClimbRequest):
    try:
        # Fetch climb
        cursor.execute("SELECT creator_user_id, price_tours FROM climbs WHERE id = ?", (request.climb_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Climb not found")
        creator_id, price = row

        # Build transfer tx to creator (similar to sendTours)
        creator_wallet = cursor.execute("SELECT wallet_address FROM sessions WHERE user_id = ?", (creator_id,)).fetchone()[0]
        tx_data = {
            "value": 0,
            "chainId": 10143,
            "from": cursor.execute("SELECT wallet_address FROM sessions WHERE user_id = ?", (request.user_id,)).fetchone()[0],
            "to": TOURS_TOKEN_ADDRESS,
            "data": w3.eth.contract(address=TOURS_TOKEN_ADDRESS).functions.transfer(creator_wallet, price * 10**18).build_transaction()['data']  # Assume 18 decimals
        }

        # Insert pending purchase tx
        cursor.execute(
            "INSERT INTO pending_txs (user_id, tx_type, tx_data) VALUES (?, ?, ?)",
            (request.user_id, 'purchase_climb', json.dumps(tx_data))
        )
        conn.commit()

        return {"status": "tx_built", "tx_data": tx_data}  # Frontend signs/broadcasts
    except Exception as e:
        logger.error(f"Error in /purchase_climb: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_purchases")
async def get_purchases(userId: str):
    try:
        cursor.execute("SELECT climb_id FROM purchases WHERE buyer_user_id = ?", (userId,))
        purchase_ids = [row[0] for row in cursor.fetchall()]
        purchases = []
        for climb_id in purchase_ids:
            cursor.execute("SELECT title, description, price_tours FROM climbs WHERE id = ?", (climb_id,))
            row = cursor.fetchone()
            purchases.append({"climb_id": climb_id, "title": row[0], "desc": row[1], "price": row[2]})
        return {"purchases": purchases}
    except Exception as e:
        logger.error(f"Error in /get_purchases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_journal")
async def add_journal(request: JournalRequest):
    try:
        # Check purchase
        cursor.execute("SELECT 1 FROM purchases WHERE climb_id = ? AND buyer_user_id = ?", (request.climb_id, request.user_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=403, detail="Not purchased")

        cursor.execute(
            "INSERT INTO journals (climb_id, user_id, entry_text, date) VALUES (?, ?, ?, ?)",
            (request.climb_id, request.user_id, request.entry_text, int(time.time()))
        )
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error in /add_journal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_journal")
async def get_journal(id: int):
    try:
        cursor.execute("SELECT entry_text, user_id, date FROM journals WHERE id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Journal not found")
        # Stub comments (add table if needed)
        return {"entry": {"content": row[0], "author": row[1], "date": row[2]}, "comments": []}
    except Exception as e:
        logger.error(f"Error in /get_journal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_journals")
async def get_journals():
    try:
        cursor.execute("SELECT id, climb_id, entry_text, user_id FROM journals")
        journals = [{"id": row[0], "climb_id": row[1], "content": row[2], "author": row[3]} for row in cursor.fetchall()]
        return {"journals": journals}
    except Exception as e:
        logger.error(f"Error in /get_journals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_tournaments")
async def get_tournaments():
    try:
        # Query contract for tournaments
        count = await contract.functions.getTournamentCount().call()
        tournaments = []
        for i in range(count):
            t = await contract.functions.tournaments(i).call()
            entryFee = t[0] / 10**18
            pot = t[1] / 10**18
            status = "Active" if t[3] else "Ended"
            participants = int(pot / entryFee) if entryFee > 0 else 0
            tournaments.append({
                "id": i,
                "entryFee": entryFee,
                "pot": pot,
                "participants": participants,
                "status": status
            })
        return {"tournaments": tournaments}
    except Exception as e:
        logger.error(f"Error in /get_tournaments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_climb/{climb_id}")
async def get_climb(climb_id: int, user_id: str):
    try:
        # Check purchase for full details
        cursor.execute("SELECT 1 FROM purchases WHERE climb_id = ? AND buyer_user_id = ?", (climb_id, user_id))
        purchased = bool(cursor.fetchone())

        cursor.execute("SELECT title, description, picture_url, location FROM climbs WHERE id = ?", (climb_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Climb not found")

        data = {"title": row[0], "desc": row[1]}
        if purchased:
            data["picture_url"] = decrypt(row[2])
            data["location"] = json.loads(decrypt(row[3]))

        return data
    except Exception as e:
        logger.error(f"Error in /get_climb: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Added overlooked endpoints
@app.get("/get_balance")
async def get_balance(user_id: str):
    try:
        cursor.execute("SELECT wallet_address FROM sessions WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No wallet connected")
        wallet = row[0]
        checksum_wallet = w3.to_checksum_address(wallet)
        mon_balance = await w3.eth.get_balance(checksum_wallet) / 10**18
        tours_balance = await tours_contract.functions.balanceOf(checksum_wallet).call() / 10**18
        return {"mon_balance": mon_balance, "tours_balance": tours_balance}
    except Exception as e:
        logger.error(f"Error in /get_balance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_help")
async def get_help():
    help_text = (
        "<b>EmpowerTours Commands</b>\n"
        "/start - Welcome message\n\n"
        "/tutorial - Setup guide\n\n"
        "/connectwallet - Connect your wallet (use chain ID 10143; remove incorrect Monad Testnet entries from MetaMask if needed)\n\n"
        "/createprofile - Create profile (1 $MON, receive 1 $TOURS)\n\n"
        "/buyTours amount - Buy $TOURS tokens with $MON (e.g., /buyTours 10 to buy 10 $TOURS)\n\n"
        "/sendTours recipient amount - Send $TOURS to another wallet (e.g., /sendTours 0x123...456 10 to send 10 $TOURS)\n\n"
        "/journal entry - Log a climb for an existing climb with photos or notes (5 $TOURS)\n\n"
        "/buildaclimb name difficulty - Create a new climb with name, difficulty, and optional photo/location (10 $TOURS)\n\n"
        "/comment id comment - Comment on a journal (0.1 $MON)\n\n"
        "/purchaseclimb id - Buy a climb (10 $TOURS)\n\n"
        "/findaclimb - List available climbs\n\n"
        "/journals - List all journal entries\n\n"
        "/viewjournal id - View a journal entry and its comments\n\n"
        "/viewclimb id - View a specific climb\n\n"
        "/mypurchases - View your purchased climbs\n\n"
        "/createtournament fee - Start a tournament with an entry fee in $TOURS (e.g., /createtournament 10 sets a 10 $TOURS fee per participant)\n\n"
        "/tournaments - List all tournaments with IDs and participant counts\n\n"
        "/jointournament id - Join a tournament by paying the entry fee in $TOURS\n\n"
        "/endtournament id winner - End a tournament (owner only) and award the prize pool to the winner’s wallet address (e.g., /endtournament 1 0x5fE8373C839948bFCB707A8a8A75A16E2634A725)\n\n"
        "/miniapp - Launch the Rock Climbing Mini App 🧗\n\n"
        "/balance - Check wallet balance ($MON, $TOURS, profile status)\n\n"
        "/debug - Check webhook status\n\n"
        "/forcewebhook - Force reset webhook\n\n"
        "/clearcache - Clear Telegram cache\n\n"
        "/ping - Check bot status\n\n"
        "Join our community at <a href=\"https://t.me/empowertourschat\">EmpowerTours Chat</a> for support!"
    )
    return {"help_text": help_text}
