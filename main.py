import logging
import os
import signal
import asyncio
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, PicklePersistence
import aiohttp
from web3 import Web3
from dotenv import load_dotenv
import html
import uvicorn
import socket
import json
import subprocess
from datetime import datetime
import asyncpg

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/public", StaticFiles(directory="public", html=True), name="public")

# Global variables
application = None
pool = None
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
CHAT_HANDLE = os.getenv("CHAT_HANDLE")
MONAD_RPC_URL = os.getenv("MONAD_RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
TOURS_TOKEN_ADDRESS = os.getenv("TOURS_TOKEN_ADDRESS")
OWNER_ADDRESS = os.getenv("OWNER_ADDRESS")
LEGACY_ADDRESS = os.getenv("LEGACY_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_CONNECT_PROJECT_ID = os.getenv("WALLET_CONNECT_PROJECT_ID")
EXPLORER_URL = "https://testnet.monadexplorer.com"
YOUR_TELEGRAM_ID = os.getenv("YOUR_TELEGRAM_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
base_url = API_BASE_URL.rstrip('/') if API_BASE_URL else ''

# Log environment variables
logger.info("Environment variables:")
logger.info(f"TELEGRAM_TOKEN: {'Set' if TELEGRAM_TOKEN else 'Missing'}")
logger.info(f"API_BASE_URL: {'Set' if API_BASE_URL else 'Missing'}")
logger.info(f"CHAT_HANDLE: {'Set' if CHAT_HANDLE else 'Missing'}")
logger.info(f"MONAD_RPC_URL: {'Set' if MONAD_RPC_URL else 'Missing'}")
logger.info(f"CONTRACT_ADDRESS: {'Set' if CONTRACT_ADDRESS else 'Missing'}")
logger.info(f"TOURS_TOKEN_ADDRESS: {'Set' if TOURS_TOKEN_ADDRESS else 'Missing'}")
logger.info(f"OWNER_ADDRESS: {'Set' if OWNER_ADDRESS else 'Missing'}")
logger.info(f"LEGACY_ADDRESS: {'Set' if LEGACY_ADDRESS else 'Missing'}")
logger.info(f"PRIVATE_KEY: {'Set' if PRIVATE_KEY else 'Missing'}")
logger.info(f"WALLET_CONNECT_PROJECT_ID: {'Set' if WALLET_CONNECT_PROJECT_ID else 'Missing'}")
logger.info(f"YOUR_TELEGRAM_ID: {'Set' if YOUR_TELEGRAM_ID else 'Missing'}")
logger.info(f"DATABASE_URL: {'Set' if DATABASE_URL else 'Missing'}")
missing_vars = []
if not TELEGRAM_TOKEN: missing_vars.append("TELEGRAM_TOKEN")
if not API_BASE_URL: missing_vars.append("API_BASE_URL")
if not CHAT_HANDLE: missing_vars.append("CHAT_HANDLE")
if not MONAD_RPC_URL: missing_vars.append("MONAD_RPC_URL")
if not CONTRACT_ADDRESS: missing_vars.append("CONTRACT_ADDRESS")
if not TOURS_TOKEN_ADDRESS: missing_vars.append("TOURS_TOKEN_ADDRESS")
if not OWNER_ADDRESS: missing_vars.append("OWNER_ADDRESS")
if not LEGACY_ADDRESS: missing_vars.append("LEGACY_ADDRESS")
if not PRIVATE_KEY: missing_vars.append("PRIVATE_KEY")
if not WALLET_CONNECT_PROJECT_ID: missing_vars.append("WALLET_CONNECT_PROJECT_ID")
if not YOUR_TELEGRAM_ID: missing_vars.append("YOUR_TELEGRAM_ID")
if not DATABASE_URL: missing_vars.append("DATABASE_URL")
if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    logger.warning("Proceeding with limited functionality")
else:
    logger.info("All required environment variables are set")

# Contract ABIs
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "entryId", "type": "uint256"},
            {"internalType": "string", "name": "contentHash", "type": "string"}
        ],
        "name": "addComment",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "entryId", "type": "uint256"},
            {"internalType": "string", "name": "contentHash", "type": "string"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"}
        ],
        "name": "addCommentWithFarcaster",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "contentHash", "type": "string"}
        ],
        "name": "addJournalEntry",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "contentHash", "type": "string"},
            {"internalType": "string", "name": "location", "type": "string"},
            {"internalType": "string", "name": "difficulty", "type": "string"},
            {"internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"}
        ],
        "name": "addJournalEntryWithDetails",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "buyTours",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "string", "name": "difficulty", "type": "string"},
            {"internalType": "int256", "name": "latitude", "type": "int256"},
            {"internalType": "int256", "name": "longitude", "type": "int256"},
            {"internalType": "string", "name": "photoHash", "type": "string"}
        ],
        "name": "createClimbingLocation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "string", "name": "name", "type": "string"},
                    {"internalType": "string", "name": "difficulty", "type": "string"},
                    {"internalType": "int256", "name": "latitude", "type": "int256"},
                    {"internalType": "int256", "name": "longitude", "type": "int256"},
                    {"internalType": "string", "name": "photoHash", "type": "string"},
                    {"internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"},
                    {"internalType": "string", "name": "farcasterCastHash", "type": "string"}
                ],
                "internalType": "struct EmpowerTours.ClimbingLocationParams",
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "createClimbingLocationWithFarcaster",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "createProfile",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_farcasterFid", "type": "uint256"},
            {"internalType": "string", "name": "_farcasterUsername", "type": "string"},
            {"internalType": "string", "name": "_farcasterBio", "type": "string"}
        ],
        "name": "createProfileWithFarcaster",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "entryFee", "type": "uint256"}
        ],
        "name": "createTournament",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "entryFee", "type": "uint256"},
            {"internalType": "string", "name": "tournamentName", "type": "string"},
            {"internalType": "string", "name": "description", "type": "string"},
            {"internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"}
        ],
        "name": "createTournamentWithFarcaster",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tournamentId", "type": "uint256"},
            {"internalType": "address", "name": "winner", "type": "address"}
        ],
        "name": "endTournament",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tournamentId", "type": "uint256"},
            {"internalType": "address", "name": "winner", "type": "address"}
        ],
        "name": "endTournamentWithFarcaster",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tournamentId", "type": "uint256"}
        ],
        "name": "joinTournament",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tournamentId", "type": "uint256"}
        ],
        "name": "joinTournamentWithFarcaster",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "locationId", "type": "uint256"}
        ],
        "name": "purchaseClimbingLocation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "locationId", "type": "uint256"}
        ],
        "name": "purchaseClimbingLocationWithFarcaster",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "renounceOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "newOwner", "type": "address"}
        ],
        "name": "transferOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "_toursToken", "type": "address"},
            {"internalType": "address", "name": "_legacyWallet", "type": "address"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [],
        "name": "FarcasterFidTaken",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "InsufficientFee",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "InsufficientMonSent",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "InsufficientTokenBalance",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "InvalidEntryId",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "InvalidFarcasterFid",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "InvalidLocationId",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "InvalidTournamentId",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "NotParticipant",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "PaymentFailed",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "ProfileExists",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "ProfileRequired",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "TournamentNotActive",
        "type": "error"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "locationId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "creator", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "name", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "ClimbingLocationCreated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "locationId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "creator", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "name", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "difficulty", "type": "string"},
            {"indexed": False, "internalType": "int256", "name": "latitude", "type": "int256"},
            {"indexed": False, "internalType": "int256", "name": "longitude", "type": "int256"},
            {"indexed": False, "internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "ClimbingLocationCreatedEnhanced",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "entryId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "commenter", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "contentHash", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "CommentAdded",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "entryId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "commenter", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "contentHash", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "farcasterCastHash", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "CommentAddedEnhanced",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "castHash", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "contentType", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "contentId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "FarcasterCastShared",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "newUsername", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "newBio", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "FarcasterProfileUpdated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "entryId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "author", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "contentHash", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "JournalEntryAdded",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "entryId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "author", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "contentHash", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "location", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "difficulty", "type": "string"},
            {"indexed": False, "internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "JournalEntryAddedEnhanced",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "locationId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "LocationPurchased",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "locationId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "LocationPurchasedEnhanced",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "previousOwner", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "newOwner", "type": "address"}
        ],
        "name": "OwnershipTransferred",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "ProfileCreated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "farcasterUsername", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "ProfileCreatedEnhanced",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "tournamentId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "entryFee", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "startTime", "type": "uint256"}
        ],
        "name": "TournamentCreated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "tournamentId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "creator", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "tournamentName", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "entryFee", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "startTime", "type": "uint256"}
        ],
        "name": "TournamentCreatedEmbedded",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "tournamentId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "winner", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "pot", "type": "uint256"}
        ],
        "name": "TournamentEnded",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "tournamentId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "winner", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "winnerFarcasterFid", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "pot", "type": "uint256"}
        ],
        "name": "TournamentEndedEnhanced",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "tournamentId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "participant", "type": "address"}
        ],
        "name": "TournamentJoined",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "tournamentId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "participant", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "farcasterFid", "type": "uint256"}
        ],
        "name": "TournamentJoinedEnhanced",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "toursAmount", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "monAmount", "type": "uint256"}
        ],
        "name": "ToursPurchased",
        "type": "event"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "newUsername", "type": "string"},
            {"internalType": "string", "name": "newBio", "type": "string"}
        ],
        "name": "updateFarcasterProfile",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "climbingLocations",
        "outputs": [
            {"internalType": "address", "name": "creator", "type": "address"},
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "string", "name": "difficulty", "type": "string"},
            {"internalType": "int256", "name": "latitude", "type": "int256"},
            {"internalType": "int256", "name": "longitude", "type": "int256"},
            {"internalType": "string", "name": "photoHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"},
            {"internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"},
            {"internalType": "uint256", "name": "purchaseCount", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "commentFee",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "farcasterFidToAddress",
        "outputs": [
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "locationId", "type": "uint256"}
        ],
        "name": "getClimbingLocation",
        "outputs": [
            {"internalType": "address", "name": "creator", "type": "address"},
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "string", "name": "difficulty", "type": "string"},
            {"internalType": "int256", "name": "latitude", "type": "int256"},
            {"internalType": "int256", "name": "longitude", "type": "int256"},
            {"internalType": "string", "name": "photoHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"},
            {"internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"},
            {"internalType": "uint256", "name": "purchaseCount", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getClimbingLocationCount",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "entryId", "type": "uint256"}
        ],
        "name": "getCommentCount",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"}
        ],
        "name": "getJournalEntriesByFarcasterFid",
        "outputs": [
            {"internalType": "uint256[]", "name": "", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "entryId", "type": "uint256"}
        ],
        "name": "getJournalEntry",
        "outputs": [
            {"internalType": "address", "name": "author", "type": "address"},
            {"internalType": "string", "name": "contentHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"},
            {"internalType": "string", "name": "location", "type": "string"},
            {"internalType": "string", "name": "difficulty", "type": "string"},
            {"internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getJournalEntryCount",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"}
        ],
        "name": "getLocationsByFarcasterFid",
        "outputs": [
            {"internalType": "uint256[]", "name": "", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"}
        ],
        "name": "getProfileByFarcasterFid",
        "outputs": [
            {"internalType": "address", "name": "userAddress", "type": "address"},
            {"internalType": "bool", "name": "exists", "type": "bool"},
            {"internalType": "uint256", "name": "journalCount", "type": "uint256"},
            {"internalType": "string", "name": "farcasterUsername", "type": "string"},
            {"internalType": "string", "name": "farcasterBio", "type": "string"},
            {"internalType": "uint256", "name": "createdAt", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getTournamentCount",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "journalComments",
        "outputs": [
            {"internalType": "address", "name": "commenter", "type": "address"},
            {"internalType": "string", "name": "contentHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "journalEntries",
        "outputs": [
            {"internalType": "address", "name": "author", "type": "address"},
            {"internalType": "string", "name": "contentHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"},
            {"internalType": "string", "name": "location", "type": "string"},
            {"internalType": "string", "name": "difficulty", "type": "string"},
            {"internalType": "bool", "name": "isSharedOnFarcaster", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "journalReward",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "LEGACY_FEE_PERCENT",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "legacyWallet",
        "outputs": [
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "locationCreationCost",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "profileFee",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "name": "profiles",
        "outputs": [
            {"internalType": "bool", "name": "exists", "type": "bool"},
            {"internalType": "uint256", "name": "journalCount", "type": "uint256"},
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"internalType": "string", "name": "farcasterUsername", "type": "string"},
            {"internalType": "string", "name": "farcasterBio", "type": "string"},
            {"internalType": "uint256", "name": "createdAt", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "tournaments",
        "outputs": [
            {"internalType": "uint256", "name": "entryFee", "type": "uint256"},
            {"internalType": "uint256", "name": "totalPot", "type": "uint256"},
            {"internalType": "address", "name": "winner", "type": "address"},
            {"internalType": "bool", "name": "isActive", "type": "bool"},
            {"internalType": "uint256", "name": "startTime", "type": "uint256"},
            {"internalType": "uint256", "name": "farcasterFid", "type": "uint256"},
            {"internalType": "string", "name": "farcasterCastHash", "type": "string"},
            {"internalType": "string", "name": "tournamentName", "type": "string"},
            {"internalType": "string", "name": "description", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "TOURS_PRICE",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "TOURS_REWARD",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "toursToken",
        "outputs": [
            {"internalType": "contract IERC20", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

TOURS_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Global blockchain variables
w3 = None
contract = None
tours_contract = None
pending_wallets = {}
journal_data = {}
sessions = {}
webhook_failed = False
last_processed_block = 0
reverse_sessions = {}  # wallet: user_id mapping for event PMs

# Initialize PostgreSQL database
async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    climb_exp TEXT,
                    web3_interest TEXT,
                    why_join TEXT,
                    dob TEXT,
                    address TEXT,
                    education TEXT,
                    headshot TEXT,
                    status TEXT DEFAULT 'pending'
                )
            ''')
        logger.info("PostgreSQL database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing PostgreSQL database: {str(e)}")
        raise

def initialize_web3():
    global w3, contract, tours_contract
    if not MONAD_RPC_URL or not CONTRACT_ADDRESS or not TOURS_TOKEN_ADDRESS:
        logger.error("Cannot initialize Web3: missing blockchain-related environment variables")
        return False
    retries = 3
    for attempt in range(1, retries + 1):
        try:
            w3 = Web3(Web3.HTTPProvider(MONAD_RPC_URL))
            if w3.is_connected():
                logger.info("Web3 initialized successfully")
                contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
                tours_contract = w3.eth.contract(address=Web3.to_checksum_address(TOURS_TOKEN_ADDRESS), abi=TOURS_ABI)
                logger.info("Contracts initialized successfully")
                return True
            else:
                logger.warning(f"Web3 connection failed on attempt {attempt}/{retries}: not connected")
                if attempt < retries:
                    time.sleep(5)
        except Exception as e:
            logger.error(f"Error initializing Web3 on attempt {attempt}/{retries}: {str(e)}")
            if attempt < retries:
                time.sleep(5)
    logger.error("All Web3 initialization attempts failed. Proceeding without blockchain functionality.")
    w3 = None
    contract = None
    tours_contract = None
    return False

def escape_html(text):
    if not text:
        return ""
    return html.escape(str(text))

async def send_notification(chat_id, message):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        try:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            async with session.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json=payload
            ) as response:
                response_data = await response.json()
                logger.info(f"Sent notification to chat {chat_id}: payload={json.dumps(payload, default=str)}, response={response_data}")
                if response_data.get("ok"):
                    return response_data
                else:
                    logger.error(f"Failed to send notification to chat {chat_id}: {response_data}")
                    return response_data
        except Exception as e:
            logger.error(f"Error in send_notification to chat {chat_id}: {str(e)}")
            return {"ok": False, "error": str(e)}

async def check_webhook():
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        try:
            async with session.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getWebhookInfo") as response:
                status = response.status
                data = await response.json()
                logger.info(f"Webhook info: status={status}, response={data}")
                return data.get("ok") and data.get("result", {}).get("url") == f"{API_BASE_URL.rstrip('/')}/webhook"
        except Exception as e:
            logger.error(f"Error checking webhook: {str(e)}")
            return False

async def reset_webhook():
    await asyncio.sleep(0.5)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        retries = 5
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"Webhook reset attempt {attempt}/{retries}")
                async with session.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook",
                    json={"drop_pending_updates": True}
                ) as response:
                    status = response.status
                    delete_data = await response.json()
                    logger.info(f"Webhook cleared: status={status}, response={delete_data}")
                    if not delete_data.get("ok"):
                        logger.error(f"Failed to delete webhook: status={status}, response={delete_data}")
                        continue
                webhook_url = f"{API_BASE_URL.rstrip('/')}/webhook"
                logger.info(f"Setting webhook to {webhook_url}")
                async with session.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                    json={"url": webhook_url, "max_connections": 100, "drop_pending_updates": True}
                ) as response:
                    status = response.status
                    set_data = await response.json()
                    logger.info(f"Webhook set: status={status}, response={set_data}")
                    if set_data.get("ok"):
                        logger.info("Verifying webhook after setting")
                        webhook_ok = await check_webhook()
                        if webhook_ok:
                            logger.info("Webhook verified successfully")
                            return True
                        else:
                            logger.error("Webhook verification failed after setting")
                    if set_data.get("error_code") == 429:
                        retry_after = set_data.get("parameters", {}).get("retry_after", 1)
                        logger.warning(f"Rate limited by Telegram, retrying after {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    logger.error(f"Failed to set webhook: status={status}, response={set_data}")
            except Exception as e:
                logger.error(f"Error resetting webhook on attempt {attempt}/{retries}: {str(e)}")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)
        logger.error("All webhook reset attempts failed. Forcing polling mode.")
        global webhook_failed
        webhook_failed = True
        return False

async def is_approved(user_id: str) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT status FROM applications WHERE user_id = $1", user_id)
        return row and row['status'] == 'approved'

def escape_md_v2(text):
    special = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + c if c in special else c for c in text])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /start command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        welcome_message_raw = (
            f"Welcome to EmpowerTours! 🧗\n"
            f"Join our community at [EmpowerTours Chat](https://t.me/empowertourschat) to connect with climbers and explore Web3-powered adventures.\n"
            f"Use /connectwallet to link your wallet, then /createprofile to get started.\n"
            f"Run /tutorial for a full guide or /help for all commands."
        )
        welcome_message = escape_md_v2(welcome_message_raw)
        keyboard = [[KeyboardButton("Launch Mini App", web_app=WebAppInfo(url=f"{base_url}/public/miniapp.html"))]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="MarkdownV2")
        logger.info(f"Sent /start response to user {update.effective_user.id}: {welcome_message}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /start for user {update.effective_user.id}: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at https://t.me/empowertourschat. 😅")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /ping command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        webhook_ok = await check_webhook()
        status = "Webhook OK" if webhook_ok else "Webhook failed, using polling"
        await update.message.reply_text(f"Pong! Bot is running. {status}. Try /start or /createprofile.")
        logger.info(f"Sent /ping response to user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /ping: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def clearcache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /clearcache command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        await update.message.reply_text("Clearing cache with dummy messages to reset Telegram responses.")
        await send_notification(update.effective_chat.id, "Dummy message 1 to clear Telegram cache.")
        if CHAT_HANDLE:
            await send_notification(CHAT_HANDLE, "Dummy message 2 to clear Telegram cache.")
        await reset_webhook()
        await update.message.reply_text("Cache cleared. Try /start again.")
        logger.info(f"Sent /clearcache response to user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /clearcache: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def forcewebhook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /forcewebhook command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        await update.message.reply_text("Attempting to force reset webhook...")
        webhook_success = await reset_webhook()
        if webhook_success:
            await update.message.reply_text("Webhook reset successful!")
        else:
            await update.message.reply_text("Webhook reset failed. Falling back to polling. Check logs for details.")
        logger.info(f"Sent /forcewebhook response to user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /forcewebhook: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /debug command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        webhook_ok = await check_webhook()
        if webhook_ok:
            await update.message.reply_text("Webhook is correctly set to https://version1-production.up.railway.app/webhook")
        else:
            await update.message.reply_text("Webhook is not correctly set. Use /forcewebhook to reset or check logs.")
        logger.info(f"Sent /debug response to user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /debug: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /tutorial command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        if not CHAT_HANDLE or not MONAD_RPC_URL:
            logger.error("CHAT_HANDLE or MONAD_RPC_URL missing, /tutorial command limited")
            await update.message.reply_text("Tutorial unavailable due to missing configuration (CHAT_HANDLE or MONAD_RPC_URL). Try /help! 😅")
            logger.info(f"/tutorial failed due to missing config, took {time.time() - start_time:.2f} seconds")
            return
        tutorial_text = (
            "Tutorial\n\n"
            "1\\. Wallet:\\n"
            "\\- Get MetaMask, Phantom, or Gnosis Safe\\.\\n"
            "\\- Add Monad testnet \\(RPC: [https://testnet-rpc.monad.xyz](https://testnet-rpc.monad.xyz), ID: 10143\\)\\.\\n"
            "\\- If you see a chain ID mismatch \\(e\\.g\\., 10159\\), go to MetaMask Settings > Networks, remove all Monad Testnet entries, and reconnect\\.\\n"
            "\\- Get $MON: [https://testnet.monad.xyz/faucet](https://testnet.monad.xyz/faucet)\\n\\n"
            "2\\. Connect:\\n"
            "\\- Use /connectwallet to connect via MetaMask or WalletConnect\\n\\n"
            "3\\. Profile:\\n"
            "\\- /createprofile \\(1 $MON, receive 1 $TOURS\\)\\n\\n"
            "4\\. Manage Tokens:\\n"
            "\\- /buyTours [amount] \\- Buy $TOURS tokens with $MON \\(e\\.g\\., /buyTours 10 to buy 10 $TOURS\\)\\n"
            "\\- /sendTours [recipient] [amount] \\- Send $TOURS to another wallet \\(e\\.g\\., /sendTours 0x123\\.\\.\\.456 10 to send 10 $TOURS\\)\\n\\n"
            "5\\. Explore:\\n"
            "\\- /journal [your journal entry] \\- Log a climb \\(5 $TOURS\\)\\n"
            "\\- /comment [id] [your comment] \\- Comment on a journal \\(0\\.1 $MON\\)\\n"
            "\\- /buildaclimb [name] [difficulty] \\- Create a climb \\(10 $TOURS\\)\\n"
            "\\- /purchaseclimb [id] \\- Buy a climb \\(10 $TOURS\\)\\n"
            "\\- /findaclimb \\- List available climbs\\n"
            "\\- /createtournament [fee] \\- Start a tournament with an entry fee in $TOURS \\(e\\.g\\., /createtournament 10 for 10 $TOURS per participant\\)\\n"
            "\\- /jointournament [id] \\- Join a tournament by paying the entry fee\\n"
            "\\- /endtournament [id] [winner] \\- End a tournament \\(owner only\\) and award the prize to the winner’s wallet address \\(e\\.g\\., /endtournament 1 0x5fE8373C839948bFCB707A8a8A75A16E2634A725\\)\\n"
            "\\- /balance \\- Check your $MON and $TOURS balance\\n"
            "\\- /help \\- List all commands\\n\\n"
            "Join our community at [EmpowerTours Chat](https://t.me/empowertourschat)\\! Try /connectwallet\\!"
        )
        await update.message.reply_text(tutorial_text, parse_mode="MarkdownV2")
        logger.info(f"Sent /tutorial response to user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /tutorial for user {update.effective_user.id}: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error in tutorial: {str(e)}. Try again...")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /help command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        help_text = (
            "EmpowerTours Commands\n\n"
            "/start \\- Welcome message\n\n"
            "/tutorial \\- Setup guide\n\n"
            "/connectwallet \\- Connect your wallet \\(use chain ID 10143; remove incorrect Monad Testnet entries from MetaMask if needed\\)\n\n"
            "/createprofile \\- Create profile \\(1 $MON, receive 1 $TOURS\\)\n\n"
            "/buyTours [amount] \\- Buy $TOURS tokens with $MON \\(e\\.g\\., /buyTours 10 to buy 10 $TOURS\\)\n\n"
            "/sendTours [recipient] [amount] \\- Send $TOURS to another wallet \\(e\\.g\\., /sendTours 0x123\\.\\.\\.456 10 to send 10 $TOURS\\)\n\n"
            "/journal [entry] \\- Log a climb for an existing climb with photos or notes \\(5 $TOURS\\)\n\n"
            "/buildaclimb [name] [difficulty] \\- Create a new climb with name, difficulty, and optional photo/location \\(10 $TOURS\\)\n\n"
            "/comment [id] [comment] \\- Comment on a journal \\(0\\.1 $MON\\)\n\n"
            "/purchaseclimb [id] \\- Buy a climb \\(10 $TOURS\\)\n\n"
            "/findaclimb \\- List available climbs\n\n"
            "/createtournament [fee] \\- Start a tournament with an entry fee in $TOURS \\(e\\.g\\., /createtournament 10 sets a 10 $TOURS fee per participant\\)\n\n"
            "/jointournament [id] \\- Join a tournament by paying the entry fee in $TOURS\n\n"
            "/endtournament [id] [winner] \\- End a tournament \\(owner only\\) and award the prize pool to the winner’s wallet address \\(e\\.g\\., /endtournament 1 0x5fE8373C839948bFCB707A8a8A75A16E2634A725\\)\n\n"
            "/balance \\- Check wallet balance \\($MON, $TOURS, profile status\\)\n\n"
            "/apply \\- Apply for membership \\(fill out form for approval\\)\n\n"
            "/listpending \\- List pending applications \\(owner only\\)\n\n"
            "/approve [user_id] \\- Approve application \\(owner only\\)\n\n"
            "/reject [user_id] \\- Reject application \\(owner only\\)\n\n"
            "/debug \\- Check webhook status\n\n"
            "/forcewebhook \\- Force reset webhook\n\n"
            "/clearcache \\- Clear Telegram cache\n\n"
            "/ping \\- Check bot status\n\n"
            "Join our community at [EmpowerTours Chat](https://t.me/empowertourschat) for support\\!"
        )
        await update.message.reply_text(help_text, parse_mode="MarkdownV2")
        logger.info(f"Sent /help response to user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /help: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received command: {update.message.text} from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        await update.message.reply_text(f"Debug: Received command '{update.message.text}'. Please use a valid command like /start or /tutorial.")
        logger.info(f"Sent /debug_command response to user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in debug_command: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def connect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /connectwallet command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /connectwallet command disabled")
        await update.message.reply_text("Wallet connection unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/connectwallet failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    try:
        user_id = str(update.effective_user.id)
        connect_url = f"{base_url}/public/connect.html?userId={user_id}"
        logger.info(f"Generated connect URL: {connect_url}")
        keyboard = [[InlineKeyboardButton("Connect with MetaMask/WalletConnect", url=connect_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = (
            "Click the button to connect your wallet via MetaMask or WalletConnect\\. "
            "On mobile, copy this link and open it in the MetaMask app's browser \\(Menu > Browser\\)\\. "
            "If you see a chain ID mismatch, go to MetaMask Settings > Networks, remove all Monad Testnet entries, and reconnect\\. "
            "After connecting, use /createprofile to create your profile or /balance to check your status\\. "
            "If the link fails, contact support at [EmpowerTours Chat](https://t.me/empowertourschat)\\."
        )
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="MarkdownV2")
        logger.info(f"Sent /connectwallet response to user {update.effective_user.id}: {message}, took {time.time() - start_time:.2f} seconds")
        pending_wallets[user_id] = {"awaiting_wallet": True, "timestamp": time.time()}
        logger.info(f"Added user {user_id} to pending_wallets: {pending_wallets[user_id]}")
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets for user {user_id}: {str(e)}")
            # Continue even if file write fails, as in-memory pending_wallets is sufficient
    except Exception as e:
        logger.error(f"Error in /connectwallet for user {user_id}: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def handle_wallet_address(user_id: str, wallet_address: str, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Handling wallet address for user {user_id}: {wallet_address}")
    if user_id not in pending_wallets or not pending_wallets[user_id].get("awaiting_wallet"):
        logger.warning(f"No pending wallet connection for user {user_id}")
        logger.info(f"/handle_wallet_address no pending connection, took {time.time() - start_time:.2f} seconds")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, wallet connection disabled")
        await context.bot.send_message(user_id, "Wallet connection unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/handle_wallet_address failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    try:
        if w3 and w3.is_address(wallet_address):
            checksum_address = w3.to_checksum_address(wallet_address)
            sessions[user_id] = {"wallet_address": checksum_address}
            reverse_sessions[checksum_address] = user_id
            await context.bot.send_message(user_id, f"Wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address}) connected\\! Try /createprofile\\. 🪙", parse_mode="MarkdownV2")
            del pending_wallets[user_id]
            try:
                with open("pending_wallets.json", "w") as f:
                    json.dump(pending_wallets, f, default=str)
                logger.info(f"Saved pending_wallets after clearing for user {user_id}")
            except Exception as e:
                logger.error(f"Error saving pending_wallets: {str(e)}")
            logger.info(f"Wallet connected for user {user_id}: {checksum_address}, took {time.time() - start_time:.2f} seconds")
        else:
            await context.bot.send_message(user_id, "Invalid wallet address or blockchain unavailable. Try /connectwallet again.")
            logger.info(f"/handle_wallet_address failed due to invalid address or blockchain, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in handle_wallet_address: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await context.bot.send_message(user_id, f"Error: {str(e)}. Try again! 😅")

async def buy_tours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /buyTours command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /buyTours command disabled")
        await update.message.reply_text("Buying $TOURS unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/buyTours failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    if not w3 or not contract:
        logger.error("Web3 or contract not initialized, /buyTours command disabled")
        await update.message.reply_text("Buying $TOURS unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/buyTours failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 1:
            await update.message.reply_text("Use: /buyTours [amount] 🛒 (e.g., /buyTours 10)")
            logger.info(f"/buyTours failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        try:
            amount = int(float(args[0]) * 10**18)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            await update.message.reply_text("Invalid amount. Use a positive number (e.g., /buyTours 10). 😅")
            logger.info(f"/buyTours failed due to invalid amount, took {time.time() - start_time:.2f} seconds")
            return
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/buyTours failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/buyTours failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            logger.info(f"Using contract address: {contract.address}")
        except Exception as e:
            logger.error(f"Error converting wallet address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid wallet address format: {str(e)}. Try /connectwallet again. 😅")
            logger.info(f"/buyTours failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Get TOURS_PRICE
        try:
            tours_price = contract.functions.TOURS_PRICE().call({'gas': 500000})
        except Exception as e:
            logger.error(f"Error getting TOURS_PRICE: {str(e)}")
            tours_price = 10**18  # Fallback to 1 MON per TOURS if call fails

        required_mon = (amount * tours_price) // 10**18

        # Check $MON balance
        try:
            mon_balance = w3.eth.get_balance(checksum_address)
            if mon_balance < required_mon:
                await update.message.reply_text(
                    f"Insufficient $MON. Need {required_mon / 10**18} $MON for {amount / 10**18} $TOURS, you have {mon_balance / 10**18}. Get more at [https://testnet.monad.xyz/faucet](https://testnet.monad.xyz/faucet)! 😅"
                )
                logger.info(f"/buyTours failed: insufficient $MON, took {time.time() - start_time:.2f} seconds")
                return
        except Exception as e:
            logger.error(f"Error checking $MON balance: {str(e)}")
            await update.message.reply_text(f"Failed to check $MON balance: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/buyTours failed due to balance check error, took {time.time() - start_time:.2f} seconds")
            return

        # Check $TOURS balance (to assume profile exists if >0)
        try:
            tours_balance = tours_contract.functions.balanceOf(checksum_address).call({'gas': 500000})
            logger.info(f"Profile assumed to exist due to non-zero $TOURS balance: {tours_balance / 10**18}")
        except Exception as e:
            logger.error(f"Error checking $TOURS balance: {str(e)}")
            tours_balance = 0

        # Simulation check for buyTours
        try:
            contract.functions.buyTours(amount).call({'from': checksum_address, 'value': required_mon, 'gas': 200000})
        except Exception as e:
            revert_reason = str(e)
            logger.error(f"buyTours simulation failed: {revert_reason}")
            if "InsufficientMonSent" in revert_reason:
                await update.message.reply_text(f"Insufficient $MON sent for {amount / 10**18} $TOURS. Need {required_mon / 10**18} $MON. 😅")
            else:
                await update.message.reply_text(f"Transaction simulation failed: {revert_reason}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/buyTours failed due to simulation error, took {time.time() - start_time:.2f} seconds")
            return

        # Build transaction
        nonce = w3.eth.get_transaction_count(checksum_address)
        tx = contract.functions.buyTours(amount).build_transaction({
            'chainId': 10143,
            'from': checksum_address,
            'value': required_mon,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        pending_wallets[user_id] = {
            "awaiting_tx": True,
            "tx_data": tx,
            "wallet_address": checksum_address,
            "timestamp": time.time()
        }
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets: {str(e)}")

        await update.message.reply_text(
            f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for buying {amount / 10**18} $TOURS \\({required_mon / 10**18} $MON\\) using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
            parse_mode="MarkdownV2"
        )
        logger.info(f"/buyTours transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /buyTours: {str(e)}, took {time.time() - start_time:.2f} seconds")
        special_chars = r'_*[]()~`>#+-=|{}.!'
        escaped_error = ''.join(['\\' + c if c in special_chars else c for c in str(e)])
        await update.message.reply_text(
            f"Error: {escaped_error}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", 
            parse_mode="MarkdownV2"
        )

async def send_tours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /sendTours command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /sendTours command disabled")
        await update.message.reply_text("Sending $TOURS unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/sendTours failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    if not w3 or not tours_contract:
        logger.error("Web3 or tours_contract not initialized, /sendTours command disabled")
        await update.message.reply_text("Sending $TOURS unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/sendTours failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 2:
            await update.message.reply_text("Use: /sendTours [recipient] [amount] 🪙 (e.g., /sendTours 0x123\\.\\.\\.456 10 to send 10 $TOURS)")
            logger.info(f"/sendTours failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        recipient = args[0]
        try:
            amount = int(float(args[1]) * 10**18)  # Convert to Wei
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            await update.message.reply_text("Invalid amount. Use a positive number (e.g., /sendTours 0x123\\.\\.\\.456 10). 😅")
            logger.info(f"/sendTours failed due to invalid amount, took {time.time() - start_time:.2f} seconds")
            return
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/sendTours failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/sendTours failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            checksum_recipient = w3.to_checksum_address(recipient)
            logger.info(f"Using tours contract address: {tours_contract.address}")
        except Exception as e:
            logger.error(f"Error converting address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid address format: {str(e)}. Check recipient address and try again. 😅")
            logger.info(f"/sendTours failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Check $TOURS balance for sender
        try:
            tours_balance = tours_contract.functions.balanceOf(checksum_address).call({'gas': 500000})
            if tours_balance < amount:
                await update.message.reply_text(f"Insufficient $TOURS. You have {tours_balance / 10**18} $TOURS, need {amount / 10**18}. Use /buyTours! 😅")
                logger.info(f"/sendTours failed due to insufficient $TOURS, took {time.time() - start_time:.2f} seconds")
                return
        except Exception as e:
            logger.error(f"Error checking $TOURS balance: {str(e)}")
            await update.message.reply_text(f"Failed to check $TOURS balance: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/sendTours failed due to balance check error, took {time.time() - start_time:.2f} seconds")
            return

        # Simulation check for transfer
        try:
            tours_contract.functions.transfer(checksum_recipient, amount).call({'from': checksum_address, 'gas': 200000})
        except Exception as e:
            revert_reason = str(e)
            logger.error(f"transfer simulation failed: {revert_reason}")
            if "InsufficientTokenBalance" in revert_reason:
                await update.message.reply_text(f"Insufficient $TOURS for transfer. Check with /balance or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            else:
                await update.message.reply_text(f"Transaction simulation failed: {revert_reason}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/sendTours failed due to simulation error, took {time.time() - start_time:.2f} seconds")
            return

        # Build transaction
        nonce = w3.eth.get_transaction_count(checksum_address)
        tx = tours_contract.functions.transfer(checksum_recipient, amount).build_transaction({
            'chainId': 10143,
            'from': checksum_address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        pending_wallets[user_id] = {
            "awaiting_tx": True,
            "tx_data": tx,
            "wallet_address": checksum_address,
            "timestamp": time.time()
        }
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets: {str(e)}")

        await update.message.reply_text(
            f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for sending {amount / 10**18} $TOURS to [{checksum_recipient[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_recipient}) using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
            parse_mode="MarkdownV2"
        )
        logger.info(f"/sendTours transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /sendTours: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

async def journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /journal command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /journal command disabled")
        await update.message.reply_text("Journaling unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/journal failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    if not w3 or not contract or not tours_contract:
        logger.error("Web3 or contract not initialized, /journal command disabled")
        await update.message.reply_text("Journaling unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/journal failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 1:
            await update.message.reply_text("Use: /journal [your journal entry] 📖 (e.g., /journal Climbed V5 today!)")
            logger.info(f"/journal failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        content_hash = ' '.join(args)
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/journal failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/journal failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            logger.info(f"Using contract address: {contract.address}")
        except Exception as e:
            logger.error(f"Error converting wallet address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid wallet address format: {str(e)}. Try /connectwallet again. 😅")
            logger.info(f"/journal failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Check profile existence
        profile_exists = False
        try:
            profile = contract.functions.profiles(checksum_address).call({'gas': 500000})
            profile_exists = profile[0]
        except Exception as e:
            logger.error(f"Error checking profile existence: {str(e)}")
            await update.message.reply_text(f"Failed to check profile: {str(e)}. Try /createprofile or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/journal failed due to profile check error, took {time.time() - start_time:.2f} seconds")
            return

        if not profile_exists:
            await update.message.reply_text("Profile required to journal. Use /createprofile first! 😅")
            logger.info(f"/journal failed due to missing profile, took {time.time() - start_time:.2f} seconds")
            return

        # Check $TOURS balance for journal (5 $TOURS)
        try:
            tours_balance = tours_contract.functions.balanceOf(checksum_address).call({'gas': 500000})
            journal_cost = 5 * 10**18
            if tours_balance < journal_cost:
                await update.message.reply_text(f"Insufficient $TOURS. Need 5 $TOURS for journaling, you have {tours_balance / 10**18}. Use /buyTours! 😅")
                logger.info(f"/journal failed due to insufficient $TOURS, took {time.time() - start_time:.2f} seconds")
                return
            allowance = tours_contract.functions.allowance(checksum_address, contract.address).call({'gas': 500000})
            if allowance < journal_cost:
                nonce = w3.eth.get_transaction_count(checksum_address)
                approve_tx = tours_contract.functions.approve(contract.address, journal_cost).build_transaction({
                    'chainId': 10143,
                    'from': checksum_address,
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price
                })
                pending_wallets[user_id] = {
                    "awaiting_tx": True,
                    "tx_data": approve_tx,
                    "wallet_address": checksum_address,
                    "timestamp": time.time(),
                    "next_tx": {
                        "type": "journal",
                        "content_hash": content_hash
                    }
                }
                try:
                    with open("pending_wallets.json", "w") as f:
                        json.dump(pending_wallets, f, default=str)
                    logger.info(f"Saved pending_wallets for user {user_id}")
                except Exception as e:
                    logger.error(f"Error saving pending_wallets: {str(e)}")
                await update.message.reply_text(
                    f"Please click [here to approve]({base_url}/public/connect.html?userId={user_id}) 5 $TOURS for journaling\\.",
                    parse_mode="MarkdownV2"
                )
                logger.info(f"/journal initiated approval for user {user_id}, took {time.time() - start_time:.2f} seconds")
                return
        except Exception as e:
            logger.error(f"Error checking $TOURS balance or allowance: {str(e)}")
            await update.message.reply_text(f"Failed to check $TOURS balance or allowance: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/journal failed due to balance/allowance error, took {time.time() - start_time:.2f} seconds")
            return

        # Simulation check for addJournalEntry
        try:
            contract.functions.addJournalEntry(content_hash).call({'from': checksum_address, 'gas': 200000})
        except Exception as e:
            revert_reason = str(e)
            logger.error(f"addJournalEntry simulation failed: {revert_reason}")
            if "ProfileRequired" in revert_reason:
                await update.message.reply_text("Profile required for journaling. Use /createprofile first! 😅")
            elif "InsufficientTokenBalance" in revert_reason:
                await update.message.reply_text("Insufficient $TOURS for journaling. Use /buyTours! 😅")
            else:
                await update.message.reply_text(f"Transaction simulation failed: {revert_reason}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/journal failed due to simulation error, took {time.time() - start_time:.2f} seconds")
            return

        # Build transaction
        nonce = w3.eth.get_transaction_count(checksum_address)
        tx = contract.functions.addJournalEntry(content_hash).build_transaction({
            'chainId': 10143,
            'from': checksum_address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        pending_wallets[user_id] = {
            "awaiting_tx": True,
            "tx_data": tx,
            "wallet_address": checksum_address,
            "timestamp": time.time()
        }
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets: {str(e)}")

        await update.message.reply_text(
            f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for adding journal entry '{escape_md_v2(content_hash)}' \\(5 $TOURS\\) using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
            parse_mode="MarkdownV2"
        )
        logger.info(f"/journal transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /journal: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /comment command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /comment command disabled")
        await update.message.reply_text("Commenting unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/comment failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    if not w3 or not contract:
        logger.error("Web3 or contract not initialized, /comment command disabled")
        await update.message.reply_text("Commenting unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/comment failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 2:
            await update.message.reply_text("Use: /comment [entry_id] [your comment] 💬 (e.g., /comment 1 Great climb!)")
            logger.info(f"/comment failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        try:
            entry_id = int(args[0])
            content_hash = ' '.join(args[1:])
        except ValueError:
            await update.message.reply_text("Invalid entry ID. Use a number for entry_id (e.g., /comment 1 Great climb!). 😅")
            logger.info(f"/comment failed due to invalid entry_id, took {time.time() - start_time:.2f} seconds")
            return
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/comment failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/comment failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            logger.info(f"Using contract address: {contract.address}")
        except Exception as e:
            logger.error(f"Error converting wallet address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid wallet address format: {str(e)}. Try /connectwallet again. 😅")
            logger.info(f"/comment failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Check profile existence
        profile_exists = False
        try:
            profile = contract.functions.profiles(checksum_address).call({'gas': 500000})
            profile_exists = profile[0]
        except Exception as e:
            logger.error(f"Error checking profile existence: {str(e)}")
            await update.message.reply_text(f"Failed to check profile: {str(e)}. Try /createprofile or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/comment failed due to profile check error, took {time.time() - start_time:.2f} seconds")
            return

        if not profile_exists:
            await update.message.reply_text("Profile required to comment. Use /createprofile first! 😅")
            logger.info(f"/comment failed due to missing profile, took {time.time() - start_time:.2f} seconds")
            return

        # Check $MON balance for comment (0.1 $MON)
        try:
            mon_balance = w3.eth.get_balance(checksum_address)
            comment_fee = contract.functions.commentFee().call({'gas': 500000})
            if mon_balance < comment_fee:
                await update.message.reply_text(f"Insufficient $MON. Need {comment_fee / 10**18} $MON for commenting. Get $MON from [https://testnet.monad.xyz/faucet](https://testnet.monad.xyz/faucet)! 😅")
                logger.info(f"/comment failed due to insufficient $MON, took {time.time() - start_time:.2f} seconds")
                return
        except Exception as e:
            logger.error(f"Error checking $MON balance or commentFee: {str(e)}")
            await update.message.reply_text(f"Failed to check $MON balance or comment fee: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/comment failed due to balance check error, took {time.time() - start_time:.2f} seconds")
            return

        # Simulation check for addComment
        try:
            contract.functions.addComment(entry_id, content_hash).call({'from': checksum_address, 'value': comment_fee, 'gas': 200000})
        except Exception as e:
            revert_reason = str(e)
            logger.error(f"addComment simulation failed: {revert_reason}")
            if "ProfileRequired" in revert_reason:
                await update.message.reply_text("Profile required for commenting. Use /createprofile first! 😅")
            elif "InvalidEntryId" in revert_reason:
                await update.message.reply_text(f"Invalid entry ID #{entry_id}. Check with /findaclimb or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            elif "InsufficientFee" in revert_reason:
                await update.message.reply_text(f"Insufficient $MON for commenting. Get $MON from [https://testnet.monad.xyz/faucet](https://testnet.monad.xyz/faucet)! 😅")
            else:
                await update.message.reply_text(f"Transaction simulation failed: {revert_reason}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/comment failed due to simulation error, took {time.time() - start_time:.2f} seconds")
            return

        # Build transaction
        nonce = w3.eth.get_transaction_count(checksum_address)
        tx = contract.functions.addComment(entry_id, content_hash).build_transaction({
            'chainId': 10143,
            'from': checksum_address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'value': comment_fee
        })
        pending_wallets[user_id] = {
            "awaiting_tx": True,
            "tx_data": tx,
            "wallet_address": checksum_address,
            "timestamp": time.time()
        }
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets: {str(e)}")

        await update.message.reply_text(
            f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for adding comment '{escape_md_v2(content_hash)}' to entry #{entry_id} \\(0.1 $MON\\) using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
            parse_mode="MarkdownV2"
        )
        logger.info(f"/comment transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /comment: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

BUILD_NAME, BUILD_DIFFICULTY, BUILD_PHOTO, BUILD_LOCATION = range(4)

async def buildaclimb_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /buildaclimb command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return ConversationHandler.END
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /buildaclimb command disabled")
        await update.message.reply_text("Building climbs unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/buildaclimb failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return ConversationHandler.END
    if not w3 or not contract or not tours_contract:
        logger.error("Web3 or contract not initialized, /buildaclimb command disabled")
        await update.message.reply_text("Building climbs unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/buildaclimb failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return ConversationHandler.END
    args = context.args or []
    if args:
        # Use args if provided (for testing)
        if len(args) < 2:
            await update.message.reply_text("Use: /buildaclimb [name] [difficulty] 🏗️ (e.g., /buildaclimb Everest V15)")
            logger.info(f"/buildaclimb failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return ConversationHandler.END
        context.user_data['build_name'] = args[0]
        context.user_data['build_difficulty'] = args[1]
        context.user_data['build_photo_hash'] = "example_photo_hash"
        context.user_data['build_latitude'] = 0
        context.user_data['build_longitude'] = 0
        await buildaclimb_final(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Let's build a climb! What's the name?")
        return BUILD_NAME

async def buildaclimb_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['build_name'] = update.message.text
    await update.message.reply_text("What's the difficulty (e.g., V5)?")
    return BUILD_DIFFICULTY

async def buildaclimb_difficulty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['build_difficulty'] = update.message.text
    await update.message.reply_text("Send a photo of the climb (or type 'skip' to skip).")
    return BUILD_PHOTO

async def buildaclimb_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.lower() == 'skip':
        context.user_data['build_photo_hash'] = ""
    elif update.message.photo:
        context.user_data['build_photo_hash'] = update.message.photo[-1].file_id
    else:
        await update.message.reply_text("Please send a photo or type 'skip'.")
        return BUILD_PHOTO
    keyboard = [[KeyboardButton("Share Location", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Share the location of the climb (or type 'skip' to skip).", reply_markup=reply_markup)
    return BUILD_LOCATION

async def buildaclimb_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.lower() == 'skip':
        context.user_data['build_latitude'] = 0
        context.user_data['build_longitude'] = 0
    elif update.message.location:
        context.user_data['build_latitude'] = int(update.message.location.latitude * 10**6)
        context.user_data['build_longitude'] = int(update.message.location.longitude * 10**6)
    else:
        await update.message.reply_text("Please share location or type 'skip'.")
        return BUILD_LOCATION
    await buildaclimb_final(update, context)
    return ConversationHandler.END

async def buildaclimb_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = context.user_data.get('build_name')
    difficulty = context.user_data.get('build_difficulty')
    photo_hash = context.user_data.get('build_photo_hash', "example_photo_hash")
    latitude = context.user_data.get('build_latitude', 0)
    longitude = context.user_data.get('build_longitude', 0)
    wallet_address = sessions.get(user_id, {}).get("wallet_address")
    if not wallet_address:
        await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
        return
    logger.info(f"Wallet address for user {user_id}: {wallet_address}")

    # Verify Web3 connection
    if not w3.is_connected():
        logger.error("Web3 not connected to Monad testnet")
        await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
        return

    # Ensure checksum address
    try:
        checksum_address = w3.to_checksum_address(wallet_address)
        logger.info(f"Using contract address: {contract.address}")
    except Exception as e:
        logger.error(f"Error converting wallet address to checksum: {str(e)}")
        await update.message.reply_text(f"Invalid wallet address format: {str(e)}. Try /connectwallet again. 😅")
        return

    # Check profile existence
    try:
        profile = contract.functions.profiles(checksum_address).call({'gas': 500000})
        profile_exists = profile[0]
    except Exception as e:
        logger.error(f"Error checking profile existence: {str(e)}")
        await update.message.reply_text(f"Failed to check profile: {str(e)}. Try /createprofile or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
        return

    if not profile_exists:
        await update.message.reply_text("Profile required to build a climb. Use /createprofile first! 😅")
        return

    # Check $TOURS balance and allowance
    location_cost = 10 * 10**18  # Assuming 10 $TOURS; replace with contract.functions.locationCreationCost().call() if available
    try:
        tours_balance = tours_contract.functions.balanceOf(checksum_address).call({'gas': 500000})
        if tours_balance < location_cost:
            await update.message.reply_text(
                f"Insufficient $TOURS. Need {location_cost / 10**18} $TOURS, you have {tours_balance / 10**18}. Use /buyTours! 😅"
            )
            return
        allowance = tours_contract.functions.allowance(checksum_address, contract.address).call({'gas': 500000})
        if allowance < location_cost:
            nonce = w3.eth.get_transaction_count(checksum_address)
            approve_tx = tours_contract.functions.approve(contract.address, location_cost).build_transaction({
                'chainId': 10143,
                'from': checksum_address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price
            })
            pending_wallets[user_id] = {
                "awaiting_tx": True,
                "tx_data": approve_tx,
                "wallet_address": checksum_address,
                "timestamp": time.time(),
                "next_tx": {
                    "type": "create_climbing_location",
                    "name": name,
                    "difficulty": difficulty,
                    "latitude": latitude,
                    "longitude": longitude,
                    "photo_hash": photo_hash
                }
            }
            try:
                with open("pending_wallets.json", "w") as f:
                    json.dump(pending_wallets, f, default=str)
                logger.info(f"Saved pending_wallets for user {user_id}")
            except Exception as e:
                logger.error(f"Error saving pending_wallets: {str(e)}")
            await update.message.reply_text(
                f"Please click [here to approve]({base_url}/public/connect.html?userId={user_id}) {location_cost / 10**18} $TOURS for building climb '{escape_md_v2(name)}' ({escape_md_v2(difficulty)})\\.",
                parse_mode="MarkdownV2"
            )
            return
    except Exception as e:
        logger.error(f"Error checking $TOURS balance or allowance: {str(e)}")
        special_chars = r'_*[]()~`>#+-=|{}.!'
        escaped_error = ''.join(['\\' + c if c in special_chars else c for c in str(e)])
        await update.message.reply_text(f"Failed to check $TOURS balance or allowance: {escaped_error}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
        return

    # Simulation check for createClimbingLocation
    try:
        contract.functions.createClimbingLocation(name, difficulty, latitude, longitude, photo_hash).call({'from': checksum_address, 'gas': 200000})
    except Exception as e:
        revert_reason = str(e)
        logger.error(f"createClimbingLocation simulation failed: {revert_reason}")
        special_chars = r'_*[]()~`>#+-=|{}.!'
        escaped_revert = ''.join(['\\' + c if c in special_chars else c for c in revert_reason])
        await update.message.reply_text(f"Transaction simulation failed: {escaped_revert}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
        return

    # Build transaction
    nonce = w3.eth.get_transaction_count(checksum_address)
    tx = contract.functions.createClimbingLocation(name, difficulty, latitude, longitude, photo_hash).build_transaction({
        'chainId': 10143,
        'from': checksum_address,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    pending_wallets[user_id] = {
        "awaiting_tx": True,
        "tx_data": tx,
        "wallet_address": checksum_address,
        "timestamp": time.time()
    }
    try:
        with open("pending_wallets.json", "w") as f:
            json.dump(pending_wallets, f, default=str)
        logger.info(f"Saved pending_wallets for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving pending_wallets: {str(e)}")

    await update.message.reply_text(
        f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for building climb '{escape_md_v2(name)}' ({escape_md_v2(difficulty)}) using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
        parse_mode="MarkdownV2"
    )

async def purchaseclimb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /purchaseclimb command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /purchaseclimb command disabled")
        await update.message.reply_text("Purchasing climbs unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/purchaseclimb failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    if not w3 or not contract or not tours_contract:
        logger.error("Web3 or contract not initialized, /purchaseclimb command disabled")
        await update.message.reply_text("Purchasing climbs unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/purchaseclimb failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 1:
            await update.message.reply_text("Use: /purchaseclimb [id] 🏔️ (e.g., /purchaseclimb 0)")
            logger.info(f"/purchaseclimb failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        try:
            location_id = int(args[0])
        except ValueError:
            await update.message.reply_text("Invalid climb ID. Use a number (e.g., /purchaseclimb 0). 😅")
            logger.info(f"/purchaseclimb failed due to invalid id, took {time.time() - start_time:.2f} seconds")
            return
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/purchaseclimb failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/purchaseclimb failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            logger.info(f"Using contract address: {contract.address}")
        except Exception as e:
            logger.error(f"Error converting wallet address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid wallet address format: {str(e)}. Try /connectwallet again. 😅")
            logger.info(f"/purchaseclimb failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Check profile existence
        profile_exists = False
        try:
            profile = contract.functions.profiles(checksum_address).call({'gas': 500000})
            profile_exists = profile[0]
        except Exception as e:
            logger.error(f"Error checking profile existence: {str(e)}")
            await update.message.reply_text(f"Failed to check profile: {str(e)}. Try /createprofile or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/purchaseclimb failed due to profile check error, took {time.time() - start_time:.2f} seconds")
            return

        if not profile_exists:
            await update.message.reply_text("Profile required to purchase a climb. Use /createprofile first! 😅")
            logger.info(f"/purchaseclimb failed due to missing profile, took {time.time() - start_time:.2f} seconds")
            return

        # Check $TOURS balance for purchaseClimbingLocation (10 $TOURS)
        try:
            tours_balance = tours_contract.functions.balanceOf(checksum_address).call({'gas': 500000})
            climb_cost = 10 * 10**18
            if tours_balance < climb_cost:
                await update.message.reply_text(f"Insufficient $TOURS. Need 10 $TOURS for purchasing a climb, you have {tours_balance / 10**18}. Use /buyTours! 😅")
                logger.info(f"/purchaseclimb failed due to insufficient $TOURS, took {time.time() - start_time:.2f} seconds")
                return
            allowance = tours_contract.functions.allowance(checksum_address, contract.address).call({'gas': 500000})
            if allowance < climb_cost:
                nonce = w3.eth.get_transaction_count(checksum_address)
                approve_tx = tours_contract.functions.approve(contract.address, climb_cost).build_transaction({
                    'chainId': 10143,
                    'from': checksum_address,
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price
                })
                pending_wallets[user_id] = {
                    "awaiting_tx": True,
                    "tx_data": approve_tx,
                    "wallet_address": checksum_address,
                    "timestamp": time.time(),
                    "next_tx": {
                        "type": "purchaseclimb",
                        "location_id": location_id
                    }
                }
                try:
                    with open("pending_wallets.json", "w") as f:
                        json.dump(pending_wallets, f, default=str)
                    logger.info(f"Saved pending_wallets for user {user_id}")
                except Exception as e:
                    logger.error(f"Error saving pending_wallets: {str(e)}")
                await update.message.reply_text(
                    f"Please click [here to approve]({base_url}/public/connect.html?userId={user_id}) 10 $TOURS for purchasing climb #{location_id}\\.",
                    parse_mode="MarkdownV2"
                )
                logger.info(f"/purchaseclimb initiated approval for user {user_id}, took {time.time() - start_time:.2f} seconds")
                return
        except Exception as e:
            logger.error(f"Error checking $TOURS balance or allowance: {str(e)}")
            await update.message.reply_text(f"Failed to check $TOURS balance or allowance: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/purchaseclimb failed due to balance/allowance error, took {time.time() - start_time:.2f} seconds")
            return

        # Simulation check for purchaseClimbingLocation
        try:
            contract.functions.purchaseClimbingLocation(location_id).call({'from': checksum_address, 'gas': 200000})
        except Exception as e:
            revert_reason = str(e)
            logger.error(f"purchaseClimbingLocation simulation failed: {revert_reason}")
            if "ProfileRequired" in revert_reason:
                await update.message.reply_text("Profile required for purchasing a climb. Use /createprofile first! 😅")
            elif "InvalidLocationId" in revert_reason:
                await update.message.reply_text(f"Invalid climb ID #{location_id}. Check with /findaclimb or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            elif "InsufficientTokenBalance" in revert_reason:
                await update.message.reply_text("Insufficient $TOURS for purchasing a climb. Use /buyTours! 😅")
            else:
                await update.message.reply_text(f"Transaction simulation failed: {revert_reason}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/purchaseclimb failed due to simulation error, took {time.time() - start_time:.2f} seconds")
            return

        # Build transaction
        nonce = w3.eth.get_transaction_count(checksum_address)
        tx = contract.functions.purchaseClimbingLocation(location_id).build_transaction({
            'chainId': 10143,
            'from': checksum_address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        pending_wallets[user_id] = {
            "awaiting_tx": True,
            "tx_data": tx,
            "wallet_address": checksum_address,
            "timestamp": time.time()
        }
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets: {str(e)}")

        await update.message.reply_text(
            f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for purchasing climb #{location_id} \\(10 $TOURS\\) using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
            parse_mode="MarkdownV2"
        )
        logger.info(f"/purchaseclimb transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /purchaseclimb: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

async def findaclimb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /findaclimb command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not w3 or not contract:
        logger.error("Web3 or contract not initialized, /findaclimb command disabled")
        await update.message.reply_text("Finding climbs unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/findaclimb failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/findaclimb failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Get climb count
        try:
            climb_count = contract.functions.getClimbingLocationCount().call({'gas': 500000})
        except Exception as e:
            logger.error(f"Error getting climbing location count: {str(e)}")
            await update.message.reply_text(f"Failed to get climb count: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/findaclimb failed due to climb count error, took {time.time() - start_time:.2f} seconds")
            return

        if climb_count == 0:
            await update.message.reply_text("No climbs available. Create one with /buildaclimb! 🏔️")
            logger.info(f"/findaclimb no climbs found, took {time.time() - start_time:.2f} seconds")
            return

        # Fetch climbs
        climbs = []
        for location_id in range(climb_count):
            try:
                climb = contract.functions.getClimbingLocation(location_id).call({'gas': 500000})
                climbs.append({
                    "id": location_id,
                    "name": climb[1],
                    "difficulty": climb[2],
                    "latitude": climb[3],
                    "longitude": climb[4],
                    "photo_hash": climb[5],
                    "creator": climb[0],
                    "timestamp": climb[6],
                    "purchase_count": climb[10]
                })
            except Exception as e:
                logger.error(f"Error fetching climb #{location_id}: {str(e)}")

        # Format response
        response = "Available Climbs:\n"
        for climb in climbs:
            response += f"#{climb['id']} - {escape_md_v2(climb['name'])} ({escape_md_v2(climb['difficulty'])}) by [{climb['creator'][:6]}\\.\\.\\.]({EXPLORER_URL}/address/{climb['creator']}) - Purchases: {climb['purchase_count']}\n"
        await update.message.reply_text(response, parse_mode="MarkdownV2")
        logger.info(f"Sent /findaclimb response to user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /findaclimb: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

async def createtournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /createtournament command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /createtournament command disabled")
        await update.message.reply_text("Creating tournaments unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/createtournament failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    if not w3 or not contract or not tours_contract:
        logger.error("Web3 or contract not initialized, /createtournament command disabled")
        await update.message.reply_text("Creating tournaments unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/createtournament failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 1:
            await update.message.reply_text("Use: /createtournament [fee] 🏆 (e.g., /createtournament 10 for 10 $TOURS entry fee)")
            logger.info(f"/createtournament failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        try:
            entry_fee = int(float(args[0]) * 10**18)
            if entry_fee <= 0:
                raise ValueError("Fee must be positive")
        except ValueError:
            await update.message.reply_text("Invalid fee. Use a positive number (e.g., /createtournament 10). 😅")
            logger.info(f"/createtournament failed due to invalid fee, took {time.time() - start_time:.2f} seconds")
            return
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/createtournament failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/createtournament failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            logger.info(f"Using contract address: {contract.address}")
        except Exception as e:
            logger.error(f"Error converting wallet address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid wallet address format: {str(e)}. Try /connectwallet again. 😅")
            logger.info(f"/createtournament failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Check profile existence
        profile_exists = False
        try:
            profile = contract.functions.profiles(checksum_address).call({'gas': 500000})
            profile_exists = profile[0]
        except Exception as e:
            logger.error(f"Error checking profile existence: {str(e)}")
            await update.message.reply_text(f"Failed to check profile: {str(e)}. Try /createprofile or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/createtournament failed due to profile check error, took {time.time() - start_time:.2f} seconds")
            return

        if not profile_exists:
            await update.message.reply_text("Profile required to create a tournament. Use /createprofile first! 😅")
            logger.info(f"/createtournament failed due to missing profile, took {time.time() - start_time:.2f} seconds")
            return

        # Simulation check for createTournament
        try:
            contract.functions.createTournament(entry_fee).call({'from': checksum_address, 'gas': 200000})
        except Exception as e:
            revert_reason = str(e)
            logger.error(f"createTournament simulation failed: {revert_reason}")
            if "ProfileRequired" in revert_reason:
                await update.message.reply_text("Profile required for creating a tournament. Use /createprofile first! 😅")
            else:
                await update.message.reply_text(f"Transaction simulation failed: {revert_reason}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/createtournament failed due to simulation error, took {time.time() - start_time:.2f} seconds")
            return

        # Build transaction
        nonce = w3.eth.get_transaction_count(checksum_address)
        tx = contract.functions.createTournament(entry_fee).build_transaction({
            'chainId': 10143,
            'from': checksum_address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        pending_wallets[user_id] = {
            "awaiting_tx": True,
            "tx_data": tx,
            "wallet_address": checksum_address,
            "timestamp": time.time()
        }
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets: {str(e)}")

        await update.message.reply_text(
            f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for creating tournament with {entry_fee / 10**18} $TOURS entry fee using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
            parse_mode="MarkdownV2"
        )
        logger.info(f"/createtournament transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /createtournament: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

async def jointournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /jointournament command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /jointournament command disabled")
        await update.message.reply_text("Joining tournaments unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/jointournament failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    if not w3 or not contract or not tours_contract:
        logger.error("Web3 or contract not initialized, /jointournament command disabled")
        await update.message.reply_text("Joining tournaments unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/jointournament failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 1:
            await update.message.reply_text("Use: /jointournament [id] 🏆 (e.g., /jointournament 0)")
            logger.info(f"/jointournament failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        try:
            tournament_id = int(args[0])
        except ValueError:
            await update.message.reply_text("Invalid tournament ID. Use a number (e.g., /jointournament 0). 😅")
            logger.info(f"/jointournament failed due to invalid id, took {time.time() - start_time:.2f} seconds")
            return
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/jointournament failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/jointournament failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            logger.info(f"Using contract address: {contract.address}")
        except Exception as e:
            logger.error(f"Error converting wallet address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid wallet address format: {str(e)}. Try /connectwallet again. 😅")
            logger.info(f"/jointournament failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Check profile existence
        profile_exists = False
        try:
            profile = contract.functions.profiles(checksum_address).call({'gas': 500000})
            profile_exists = profile[0]
        except Exception as e:
            logger.error(f"Error checking profile existence: {str(e)}")
            await update.message.reply_text(f"Failed to check profile: {str(e)}. Try /createprofile or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/jointournament failed due to profile check error, took {time.time() - start_time:.2f} seconds")
            return

        if not profile_exists:
            await update.message.reply_text("Profile required to join a tournament. Use /createprofile first! 😅")
            logger.info(f"/jointournament failed due to missing profile, took {time.time() - start_time:.2f} seconds")
            return

        # Get tournament details
        try:
            tournament = contract.functions.tournaments(tournament_id).call({'gas': 500000})
            entry_fee = tournament[0]
            is_active = tournament[3]
            if not is_active:
                await update.message.reply_text(f"Tournament #{tournament_id} is not active. Check with /findaclimb or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
                logger.info(f"/jointournament failed: tournament not active, took {time.time() - start_time:.2f} seconds")
                return
        except Exception as e:
            logger.error(f"Error getting tournament details: {str(e)}")
            await update.message.reply_text(f"Failed to get tournament details: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/jointournament failed due to tournament details error, took {time.time() - start_time:.2f} seconds")
            return

        # Check $TOURS balance and allowance
        try:
            tours_balance = tours_contract.functions.balanceOf(checksum_address).call({'gas': 500000})
            if tours_balance < entry_fee:
                await update.message.reply_text(
                    f"Insufficient $TOURS. Need {entry_fee / 10**18} $TOURS, you have {tours_balance / 10**18}. Use /buyTours! 😅"
                )
                logger.info(f"/jointournament failed: insufficient $TOURS, took {time.time() - start_time:.2f} seconds")
                return
            allowance = tours_contract.functions.allowance(checksum_address, contract.address).call({'gas': 500000})
            if allowance < entry_fee:
                nonce = w3.eth.get_transaction_count(checksum_address)
                approve_tx = tours_contract.functions.approve(contract.address, entry_fee).build_transaction({
                    'chainId': 10143,
                    'from': checksum_address,
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price
                })
                pending_wallets[user_id] = {
                    "awaiting_tx": True,
                    "tx_data": approve_tx,
                    "wallet_address": checksum_address,
                    "timestamp": time.time(),
                    "next_tx": {
                        "type": "join_tournament",
                        "tournament_id": tournament_id
                    }
                }
                try:
                    with open("pending_wallets.json", "w") as f:
                        json.dump(pending_wallets, f, default=str)
                    logger.info(f"Saved pending_wallets for user {user_id}")
                except Exception as e:
                    logger.error(f"Error saving pending_wallets:{str(e)}")
                await update.message.reply_text(
                    f"Please click [here to approve]({base_url}/public/connect.html?userId={user_id}) {entry_fee / 10**18} $TOURS for joining tournament #{tournament_id}\\.",
                    parse_mode="MarkdownV2"
                )
                logger.info(f"/jointournament initiated approval for user {user_id}, took {time.time() - start_time:.2f} seconds")
                return
        except Exception as e:
            logger.error(f"Error checking $TOURS balance or allowance: {str(e)}")
            await update.message.reply_text(f"Failed to check $TOURS balance or allowance: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/jointournament failed due to balance/allowance error, took {time.time() - start_time:.2f} seconds")
            return

        # Simulation check for joinTournament
        try:
            contract.functions.joinTournament(tournament_id).call({'from': checksum_address, 'gas': 200000})
        except Exception as e:
            revert_reason = str(e)
            logger.error(f"joinTournament simulation failed: {revert_reason}")
            if "TournamentNotActive" in revert_reason:
                await update.message.reply_text(f"Tournament #{tournament_id} is not active. Check with /findaclimb or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            elif "InvalidTournamentId" in revert_reason:
                await update.message.reply_text(f"Invalid tournament ID #{tournament_id}. Check with /findaclimb or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            elif "InsufficientTokenBalance" in revert_reason:
                await update.message.reply_text("Insufficient $TOURS for joining the tournament. Use /buyTours! 😅")
            else:
                await update.message.reply_text(f"Transaction simulation failed: {revert_reason}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/jointournament failed due to simulation error, took {time.time() - start_time:.2f} seconds")
            return

        # Build transaction
        nonce = w3.eth.get_transaction_count(checksum_address)
        tx = contract.functions.joinTournament(tournament_id).build_transaction({
            'chainId': 10143,
            'from': checksum_address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        pending_wallets[user_id] = {
            "awaiting_tx": True,
            "tx_data": tx,
            "wallet_address": checksum_address,
            "timestamp": time.time()
        }
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets: {str(e)}")

        await update.message.reply_text(
            f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for joining tournament #{tournament_id} \\({entry_fee / 10**18} $TOURS\\) using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
            parse_mode="MarkdownV2"
        )
        logger.info(f"/jointournament transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /jointournament: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

async def endtournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /endtournament command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if user_id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("Only the owner can end tournaments. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
        logger.info(f"/endtournament failed: unauthorized user {user_id}, took {time.time() - start_time:.2f} seconds")
        return
    if not API_BASE_URL:
        logger.error("API_BASE_URL missing, /endtournament command disabled")
        await update.message.reply_text("Ending tournaments unavailable due to configuration issues. Try again later! 😅")
        logger.info(f"/endtournament failed due to missing API_BASE_URL, took {time.time() - start_time:.2f} seconds")
        return
    if not w3 or not contract:
        logger.error("Web3 or contract not initialized, /endtournament command disabled")
        await update.message.reply_text("Ending tournaments unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/endtournament failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 2:
            await update.message.reply_text("Use: /endtournament [id] [winner_address] 🏆 (e.g., /endtournament 0 0x123\\.\\.\\.456)")
            logger.info(f"/endtournament failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        try:
            tournament_id = int(args[0])
            winner = args[1]
        except ValueError:
            await update.message.reply_text("Invalid tournament ID. Use a number for id (e.g., /endtournament 0 0x123\\.\\.\\.456). 😅")
            logger.info(f"/endtournament failed due to invalid id, took {time.time() - start_time:.2f} seconds")
            return
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/endtournament failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/endtournament failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            checksum_winner = w3.to_checksum_address(winner)
            logger.info(f"Using contract address: {contract.address}")
        except Exception as e:
            logger.error(f"Error converting address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid address format: {str(e)}. Check winner address and try again. 😅")
            logger.info(f"/endtournament failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Check if user is owner
        try:
            owner = contract.functions.owner().call({'gas': 500000})
            if checksum_address != owner:
                await update.message.reply_text("Only the contract owner can end tournaments. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
                logger.info(f"/endtournament failed: not owner, took {time.time() - start_time:.2f} seconds")
                return
        except Exception as e:
            logger.error(f"Error checking contract owner: {str(e)}")
            await update.message.reply_text(f"Failed to check contract owner: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/endtournament failed due to owner check error, took {time.time() - start_time:.2f} seconds")
            return

        # Simulation check for endTournament
        try:
            contract.functions.endTournament(tournament_id, checksum_winner).call({'from': checksum_address, 'gas': 200000})
        except Exception as e:
            revert_reason = str(e)
            logger.error(f"endTournament simulation failed: {revert_reason}")
            if "TournamentNotActive" in revert_reason:
                await update.message.reply_text(f"Tournament #{tournament_id} is not active. Check with /findaclimb or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            elif "InvalidTournamentId" in revert_reason:
                await update.message.reply_text(f"Invalid tournament ID #{tournament_id}. Check with /findaclimb or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            else:
                await update.message.reply_text(f"Transaction simulation failed: {revert_reason}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/endtournament failed due to simulation error, took {time.time() - start_time:.2f} seconds")
            return

        # Build transaction
        nonce = w3.eth.get_transaction_count(checksum_address)
        tx = contract.functions.endTournament(tournament_id, checksum_winner).build_transaction({
            'chainId': 10143,
            'from': checksum_address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        pending_wallets[user_id] = {
            "awaiting_tx": True,
            "tx_data": tx,
            "wallet_address": checksum_address,
            "timestamp": time.time()
        }
        try:
            with open("pending_wallets.json", "w") as f:
                json.dump(pending_wallets, f, default=str)
            logger.info(f"Saved pending_wallets for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving pending_wallets: {str(e)}")

        await update.message.reply_text(
            f"Please click [here to sign]({base_url}/public/connect.html?userId={user_id}) the transaction for ending tournament #{tournament_id} and awarding to [{checksum_winner[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_winner}) using your wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\\.",
            parse_mode="MarkdownV2"
        )
        logger.info(f"/endtournament transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /endtournament: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /balance command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if not await is_approved(user_id):
        await update.message.reply_text("Please apply with /apply and wait for approval!")
        return
    if not w3 or not contract or not tours_contract:
        logger.error("Web3 or contract not initialized, /balance command disabled")
        await update.message.reply_text("Checking balance unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/balance failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        wallet_address = sessions.get(user_id, {}).get("wallet_address")
        if not wallet_address:
            await update.message.reply_text("No wallet connected. Use /connectwallet first! 🪙")
            logger.info(f"/balance failed due to missing wallet, took {time.time() - start_time:.2f} seconds")
            return
        logger.info(f"Wallet address for user {user_id}: {wallet_address}")

        # Verify Web3 connection
        if not w3.is_connected():
            logger.error("Web3 not connected to Monad testnet")
            await update.message.reply_text("Blockchain connection failed. Try again later or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
            logger.info(f"/balance failed due to Web3 connection, took {time.time() - start_time:.2f} seconds")
            return

        # Ensure checksum address
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
        except Exception as e:
            logger.error(f"Error converting wallet address to checksum: {str(e)}")
            await update.message.reply_text(f"Invalid wallet address format: {str(e)}. Try /connectwallet again. 😅")
            logger.info(f"/balance failed due to checksum error, took {time.time() - start_time:.2f} seconds")
            return

        # Check $MON balance
        try:
            mon_balance = w3.eth.get_balance(checksum_address)
        except Exception as e:
            logger.error(f"Error checking $MON balance: {str(e)}")
            mon_balance = 0

        # Check $TOURS balance
        try:
            tours_balance = tours_contract.functions.balanceOf(checksum_address).call({'gas': 500000})
        except Exception as e:
            logger.error(f"Error checking $TOURS balance: {str(e)}")
            tours_balance = 0

        # Check profile existence
        profile_exists = False
        try:
            profile = contract.functions.profiles(checksum_address).call({'gas': 500000})
            profile_exists = profile[0]
        except Exception as e:
            logger.error(f"Error checking profile existence: {str(e)}")

        response = f"Wallet [{checksum_address[:6]}\\.\\.\\.]({EXPLORER_URL}/address/{checksum_address})\n$MON: {mon_balance / 10**18}\n$TOURS: {tours_balance / 10**18}\nProfile: {'Exists' if profile_exists else 'Not Created \\(Use /createprofile\\)'}\n"
        await update.message.reply_text(response, parse_mode="MarkdownV2")
        logger.info(f"Sent /balance response to user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /balance: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")

async def apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /apply command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    try:
        if await is_approved(user_id):
            await update.message.reply_text("You are already approved! Try /balance or /createprofile. 😊")
            logger.info(f"/apply already approved for user {user_id}, took {time.time() - start_time:.2f} seconds")
            return ConversationHandler.END
        context.user_data['apply_step'] = 0
        context.user_data['application'] = {}
        await update.message.reply_text("Let's start your application. What's your full name?")
        logger.info(f"/apply started for user {user_id}, took {time.time() - start_time:.2f} seconds")
        return 'NAME'
    except Exception as e:
        logger.error(f"Error in /apply: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply name from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        context.user_data['application']['name'] = update.message.text
        await update.message.reply_text("What's your email?")
        logger.info(f"Apply name received for user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
        return 'EMAIL'
    except Exception as e:
        logger.error(f"Error in apply_name: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply email from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        context.user_data['application']['email'] = update.message.text
        await update.message.reply_text("What's your climbing experience?")
        logger.info(f"Apply email received for user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
        return 'CLIMB_EXP'
    except Exception as e:
        logger.error(f"Error in apply_email: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_climb_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply climb_exp from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        context.user_data['application']['climb_exp'] = update.message.text
        await update.message.reply_text("What's your interest in Web3?")
        logger.info(f"Apply climb_exp received for user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
        return 'WEB3_INTEREST'
    except Exception as e:
        logger.error(f"Error in apply_climb_exp:{str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_web3_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply web3_interest from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        context.user_data['application']['web3_interest'] = update.message.text
        await update.message.reply_text("Why do you want to join EmpowerTours?")
        logger.info(f"Apply web3_interest received for user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
        return 'WHY_JOIN'
    except Exception as e:
        logger.error(f"Error in apply_web3_interest: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_why_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply why_join from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        context.user_data['application']['why_join'] = update.message.text
        await update.message.reply_text("What's your date of birth (YYYY-MM-DD)?")
        logger.info(f"Apply why_join received for user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
        return 'DOB'
    except Exception as e:
        logger.error(f"Error in apply_why_join: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply dob from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        context.user_data['application']['dob'] = update.message.text
        await update.message.reply_text("What's your address?")
        logger.info(f"Apply dob received for user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
        return 'ADDRESS'
    except Exception as e:
        logger.error(f"Error in apply_dob: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply address from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        context.user_data['application']['address'] = update.message.text
        await update.message.reply_text("What's your education?")
        logger.info(f"Apply address received for user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
        return 'EDUCATION'
    except Exception as e:
        logger.error(f"Error in apply_address: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply education from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        context.user_data['application']['education'] = update.message.text
        await update.message.reply_text("Please send your headshot photo.")
        logger.info(f"Apply education received for user {update.effective_user.id}, took {time.time() - start_time:.2f} seconds")
        return 'HEADSHOT'
    except Exception as e:
        logger.error(f"Error in apply_education: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def apply_headshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received apply headshot from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)  # Add this line
    try:
        photo = update.message.photo[-1]
        context.user_data['application']['headshot'] = photo.file_id
        application = context.user_data['application']
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO applications (user_id, name, email, climb_exp, web3_interest, why_join, dob, address, education, headshot) 
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (user_id) DO UPDATE SET 
                    name = EXCLUDED.name,
                    email = EXCLUDED.email,
                    climb_exp = EXCLUDED.climb_exp,
                    web3_interest = EXCLUDED.web3_interest,
                    why_join = EXCLUDED.why_join,
                    dob = EXCLUDED.dob,
                    address = EXCLUDED.address,
                    education = EXCLUDED.education,
                    headshot = EXCLUDED.headshot,
                    status = 'pending'
            ''', user_id, application['name'], application['email'], application['climb_exp'], application['web3_interest'], application['why_join'], application['dob'], application['address'], application['education'], application['headshot'])
        await update.message.reply_text("Application submitted! Waiting for approval. Check status with /balance. 😊")
        logger.info(f"Application submitted for user {user_id}, took {time.time() - start_time:.2f} seconds")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in apply_headshot: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")
        return ConversationHandler.END

async def listpending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /listpending command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if user_id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("Only the owner can list pending applications. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
        logger.info(f"/listpending failed: unauthorized user {user_id}, took {time.time() - start_time:.2f} seconds")
        return
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id, name FROM applications WHERE status = 'pending'")
        if not rows:
            await update.message.reply_text("No pending applications.")
            logger.info(f"/listpending no pending, took {time.time() - start_time:.2f} seconds")
            return
        response = "Pending Applications:\n"
        for row in rows:
            response += f"User ID: {row['user_id']}, Name: {row['name']}\n"
        await update.message.reply_text(response)
        logger.info(f"Sent /listpending response to user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /listpending: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /approve command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if user_id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("Only the owner can approve applications. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
        logger.info(f"/approve failed: unauthorized user {user_id}, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 1:
            await update.message.reply_text("Use: /approve [user_id]")
            logger.info(f"/approve failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        approve_user_id = args[0]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE applications SET status = 'approved' WHERE user_id = $1 AND status = 'pending'", approve_user_id)
        await update.message.reply_text(f"User {approve_user_id} approved.")
        await application.bot.send_message(approve_user_id, "Your application has been approved! Try /connectwallet and /createprofile. 😊")
        logger.info(f"User {approve_user_id} approved by {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /approve: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /reject command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    user_id = str(update.effective_user.id)
    if user_id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("Only the owner can reject applications. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="MarkdownV2")
        logger.info(f"/reject failed: unauthorized user {user_id}, took {time.time() - start_time:.2f} seconds")
        return
    try:
        args = context.args or []
        if len(args) < 1:
            await update.message.reply_text("Use: /reject [user_id]")
            logger.info(f"/reject failed due to insufficient args, took {time.time() - start_time:.2f} seconds")
            return
        reject_user_id = args[0]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE applications SET status = 'rejected' WHERE user_id = $1 AND status = 'pending'", reject_user_id)
        await update.message.reply_text(f"User {reject_user_id} rejected.")
        await application.bot.send_message(reject_user_id, "Your application has been rejected. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat) for more information. 😔", parse_mode="MarkdownV2")
        logger.info(f"User {reject_user_id} rejected by {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /reject: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

command_handlers = {
    'start': start,
    'tutorial': tutorial,
    'connectwallet': connect_wallet,
    'help': help,
    'ping': ping,
    'clearcache': clearcache,
    'forcewebhook': forcewebhook,
    'debug': debug,
    'buyTours': buy_tours,
    'sendTours': send_tours,
    'journal': journal,
    'comment': comment,
    'buildaclimb': buildaclimb_start,
    'purchaseclimb': purchaseclimb,
    'findaclimb': findaclimb,
    'createtournament': createtournament,
    'jointournament': jointournament,
    'endtournament': endtournament,
    'balance': balance,
    'apply': apply,
    'listpending': listpending,
    'approve': approve,
    'reject': reject,
}

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.message.web_app_data.data
    logger.info(f"Received web_app_data from mini app: {data}")
    if data.startswith('/'):
        parts = data.lstrip('/').split()
        command = parts[0]
        args = parts[1:]
        if command in command_handlers:
            original_args = context.args
            context.args = args
            try:
                await command_handlers[command](update, context)
            finally:
                context.args = original_args
        else:
            await update.message.reply_text(f"Unknown command {data}. Try /help.")
    else:
        await update.message.reply_text(f"Invalid data {data}.")
    
async def handle_tx_hash(user_id, tx_hex, application):
    start_time = time.time()
    logger.info(f"Handling tx for user {user_id} with tx_hex {tx_hex}")
    if user_id not in pending_wallets or not pending_wallets[user_id].get("awaiting_tx"):
        logger.warning(f"No pending transaction for user {user_id}")
        logger.info(f"handle_tx_hash no pending tx, took {time.time() - start_time:.2f} seconds")
        return
    try:
        tx_hash_bytes = w3.eth.send_raw_transaction(tx_hex)
        tx_hash = tx_hash_bytes.hex()
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status == 1:
            msg = "Transaction confirmed! 🎉"
            if "next_tx" in pending_wallets[user_id]:
                next_tx_data = pending_wallets[user_id]["next_tx"]
                if next_tx_data["type"] == "join_tournament":
                    nonce = w3.eth.get_transaction_count(pending_wallets[user_id]["wallet_address"])
                    tx = contract.functions.joinTournament(next_tx_data["tournament_id"]).build_transaction({
                        'chainId': 10143,
                        'from': pending_wallets[user_id]["wallet_address"],
                        'nonce': nonce,
                        'gas': 200000,
                        'gasPrice': w3.eth.gas_price
                    })
                    pending_wallets[user_id] = {
                        "awaiting_tx": True,
                        "tx_data": tx,
                        "wallet_address": pending_wallets[user_id]["wallet_address"],
                        "timestamp": time.time()
                    }
                    try:
                        with open("pending_wallets.json", "w") as f:
                            json.dump(pending_wallets, f, default=str)
                        logger.info(f"Saved pending_wallets for user {user_id} with next_tx")
                    except Exception as e:
                        logger.error(f"Error saving pending_wallets: {str(e)}")
                    await application.bot.send_message(
                        user_id,
                        f"Approval confirmed! Now open {base_url}/public/connect.html?userId={user_id} to sign the transaction for joining tournament #{next_tx_data['tournament_id']}."
                    )
                    logger.info(f"handle_tx_hash processed approval, next transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
                    return
                # Add similar logic for other next_tx types if needed (e.g., journal, buildaclimb, purchaseclimb)

            if "purchaseClimbingLocation" in pending_wallets[user_id]["tx_data"]["data"]:
                input_data = pending_wallets[user_id]["tx_data"]["data"]
                location_id = int.from_bytes(bytes.fromhex(input_data[10:]), 'big')
                location = contract.functions.getClimbingLocation(location_id).call()
                lat = location[3] / 10**6
                lon = location[4] / 10**6
                directions_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
                msg += f" Climb purchased. Directions: [Google Maps]({directions_url}) 🗺️"
            await application.bot.send_message(user_id, msg, parse_mode="MarkdownV2")
            del pending_wallets[user_id]
            try:
                with open("pending_wallets.json", "w") as f:
                    json.dump(pending_wallets, f, default=str)
                logger.info(f"Saved pending_wallets after clearing for user {user_id}")
            except Exception as e:
                logger.error(f"Error saving pending_wallets: {str(e)}")
            logger.info(f"handle_tx_hash success for user {user_id}, took {time.time() - start_time:.2f} seconds")
        else:
            await application.bot.send_message(user_id, "Transaction failed. Check parameters or contact support at https://t.me/empowertourschat. 😅")
            logger.info(f"handle_tx_hash failed transaction for user {user_id}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in handle_tx_hash: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await application.bot.send_message(user_id, f"Error: {str(e)}. Try again! 😅")

async def submit_tx(request: Request):
    start_time = time.time()
    data = await request.json()
    user_id = data.get("userId")
    tx_hex = data.get("txHex")
    if not user_id or not tx_hex:
        logger.error("Missing userId or txHex in /submit_tx")
        raise HTTPException(status_code=400, detail="Missing userId or txHex")
    logger.info(f"Received /submit_tx for user {user_id} with tx_hex {tx_hex}")
    await handle_tx_hash(user_id, tx_hex, application)
    logger.info(f"Processed /submit_tx for user {user_id}, took {time.time() - start_time:.2f} seconds")
    return {"status": "ok"}

@app.get("/get_transaction")
async def get_transaction(userId: str):
    start_time = time.time()
    logger.info(f"Received /get_transaction request for user {userId}")
    if userId in pending_wallets and pending_wallets[userId].get("awaiting_tx"):
        tx_data = pending_wallets[userId]["tx_data"]
        logger.info(f"Transaction served for user {userId}: {tx_data}, took {time.time() - start_time:.2f} seconds")
        return {"tx": tx_data}
    else:
        logger.info(f"No pending transaction for user {userId}, ignoring poll, took {time.time() - start_time:.2f} seconds")
        return {"tx": None}

@app.post("/submit_wallet")
async def submit_wallet(request: Request):
    start_time = time.time()
    data = await request.json()
    user_id = data.get("userId")
    wallet_address = data.get("walletAddress")
    if not user_id or not wallet_address:
        logger.error("Missing userId or walletAddress in /submit_wallet")
        raise HTTPException(status_code=400, detail="Missing userId or walletAddress")
    logger.info(f"Received /submit_wallet for user {user_id} with wallet {wallet_address}")
    await handle_wallet_address(user_id, wallet_address, application)
    logger.info(f"Processed /submit_wallet for user {user_id}, took {time.time() - start_time:.2f} seconds")
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    start_time = time.time()
    try:
        update_json = await request.json()
        update = Update.de_json(update_json, application.bot)
        await application.process_update(update)
        logger.info(f"Processed webhook update, took {time.time() - start_time:.2f} seconds")
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}, took {time.time() - start_time:.2f} seconds")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    start_time = time.time()
    logger.info("Starting up...")
    await init_db()
    initialize_web3()
    global application
    persistence = PicklePersistence(filepath="persistence")
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("apply", apply)],
        states={
            'NAME': [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_name)],
            'EMAIL': [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_email)],
            'CLIMB_EXP': [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_climb_exp)],
            'WEB3_INTEREST': [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_web3_interest)],
            'WHY_JOIN': [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_why_join)],
            'DOB': [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_dob)],
            'ADDRESS': [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_address)],
            'EDUCATION': [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_education)],
            'HEADSHOT': [MessageHandler(filters.PHOTO, apply_headshot)],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("clearcache", clearcache))
    application.add_handler(CommandHandler("forcewebhook", forcewebhook))
    application.add_handler(CommandHandler("debug", debug))
    application.add_handler(CommandHandler("tutorial", tutorial))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("connectwallet", connect_wallet))
    application.add_handler(CommandHandler("buyTours", buy_tours))
    application.add_handler(CommandHandler("sendTours", send_tours))
    application.add_handler(CommandHandler("journal", journal))
    application.add_handler(CommandHandler("comment", comment))
    application.add_handler(CommandHandler("purchaseclimb", purchaseclimb))
    application.add_handler(CommandHandler("findaclimb", findaclimb))
    application.add_handler(CommandHandler("createtournament", createtournament))
    application.add_handler(CommandHandler("jointournament", jointournament))
    application.add_handler(CommandHandler("endtournament", endtournament))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("listpending", listpending))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("reject", reject))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug_command))

    build_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("buildaclimb", buildaclimb_start)],
        states={
            BUILD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, buildaclimb_name)],
            BUILD_DIFFICULTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, buildaclimb_difficulty)],
            BUILD_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, buildaclimb_photo)],
            BUILD_LOCATION: [MessageHandler(filters.LOCATION | filters.TEXT & ~filters.COMMAND, buildaclimb_location)],
        },
        fallbacks=[],
    )
    application.add_handler(build_conv_handler)
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # Add this line to initialize the application
    await application.initialize()
    
    webhook_success = await reset_webhook()
    if not webhook_success:
        logger.warning("Webhook failed, falling back to polling")
        asyncio.create_task(application.run_polling(allowed_updates=Update.ALL_TYPES))
    logger.info(f"Startup complete, took {time.time() - start_time:.2f} seconds")

@app.on_event("shutdown")
async def shutdown_event():
    start_time = time.time()
    logger.info("Shutting down...")
    try:
        await application.stop()
    except RuntimeError as e:
        if "not running" in str(e).lower():
            logger.info("Application was not running, skipping stop")
        else:
            raise
    await pool.close()
    logger.info(f"Shutdown complete, took {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
