import logging
import os
import signal
import asyncio
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import aiohttp
from web3 import Web3
from dotenv import load_dotenv
import html
import uvicorn
import socket
import json
import subprocess
from datetime import datetime
import asyncpg  # Added for Postgres

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/public", StaticFiles(directory="public", html=True), name="public")

# Global variables
application = None
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
YOUR_TELEGRAM_ID = os.getenv("YOUR_TELEGRAM_ID")  # Add this to .env for owner notifications
DATABASE_URL = os.getenv("DATABASE_URL")  # Added for Postgres

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
logger.info(f"YOUR_TELEGRAM_ID: {'Set' if YOUR_TELEGRAM_ID else 'Missing'}")  # Log owner ID
logger.info(f"DATABASE_URL: {'Set' if DATABASE_URL else 'Missing'}")  # Log DATABASE_URL
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
if not YOUR_TELEGRAM_ID: missing_vars.append("YOUR_TELEGRAM_ID")  # Check owner ID
if not DATABASE_URL: missing_vars.append("DATABASE_URL")  # Check DATABASE_URL
if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    logger.warning("Proceeding with limited functionality")
else:
    logger.info("All required environment variables are set")

# Contract ABIs (unchanged)
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

# Global Postgres pool
db_pool = None

# States for conversation
NAME, EMAIL, CLIMB_EXP, WEB3_INTEREST, WHY_JOIN = range(5)

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
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT status FROM applications WHERE user_id = $1", user_id)
    return row and row['status'] == 'approved'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /start command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        welcome_message = (
            f"Welcome to EmpowerTours! 🧗\n"
            f"Join our community at [EmpowerTours Chat](https://t.me/empowertourschat) to connect with climbers and explore Web3-powered adventures.\n"
            f"Use /connectwallet to link your wallet, then /createprofile to get started.\n"
            f"Run /tutorial for a full guide or /help for all commands."
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
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

async def testlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /testlink command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        message = "Testing link: [EmpowerTours Chat](https://t.me/empowertourschat)"
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Sent /testlink response to user {update.effective_user.id}: {message}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /testlink: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def testplain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /testplain command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        message = "Testing plain link: https://t.me/empowertourschat"
        await update.message.reply_text(message)
        logger.info(f"Sent /testplain response to user {update.effective_user.id}: {message}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /testplain: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def testmarkdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /testmarkdown command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        message = "Testing Markdown link: [EmpowerTours Chat](https://t.me/empowertourschat)"
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"Sent /testmarkdown response to user {update.effective_user.id}: {message}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /testmarkdown: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def testentity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /testentity command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        message = "Testing entity link: EmpowerTours Chat"
        await update.message.reply_text(
            message,
            entities=[MessageEntity(type="text_link", offset=21, length=17, url="https://t.me/empowertourschat")]
        )
        logger.info(f"Sent /testentity response to user {update.effective_user.id}: {message}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /testentity: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def testshort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    logger.info(f"Received /testshort command from user {update.effective_user.id} in chat {update.effective_chat.id}")
    try:
        message = "Testing short link: t.me/empowertourschat"
        await update.message.reply_text(message)
        logger.info(f"Sent /testshort response to user {update.effective_user.id}: {message}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in /testshort: {str(e)}, took {time.time() - start_time:.2f} seconds")
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
        await update.message.reply_text("Cache cleared. Try /start, /testlink, /testplain, /testmarkdown, /testentity, or /testshort again.")
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
            "Tutorial\n"
            "1. Wallet:\n"
            "- Get MetaMask, Phantom, or Gnosis Safe.\n"
            f"- Add Monad testnet (RPC: https://testnet-rpc.monad.xyz, ID: 10143).\n"
            "- If you see a chain ID mismatch (e.g., 10159), go to MetaMask Settings > Networks, remove all Monad Testnet entries, and reconnect.\n"
            "- Get $MON: https://testnet.monad.xyz/faucet\n"
            "2. Connect:\n"
            "- Use /connectwallet to connect via MetaMask or WalletConnect\n"
            "3. Profile:\n"
            "- /createprofile (1 $MON, receive 1 $TOURS)\n"
            "4. Manage Tokens:\n"
            "- /buyTours [amount] - Buy $TOURS tokens with $MON (e.g., /buyTours 10 to buy 10 $TOURS)\n"
            "- /sendTours [recipient] [amount] - Send $TOURS to another wallet (e.g., /sendTours 0x123...456 10 to send 10 $TOURS)\n"
            "5. Explore:\n"
            "- /journal [your journal entry] - Log a climb (5 $TOURS)\n"
            "- /comment [id] [your comment] - Comment on a journal (0.1 $MON)\n"
            "- /buildaclimb [name]...(truncated 87161 characters)...rieve balance: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="Markdown")
            logger.info(f"/balance failed due to balance error, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Unexpected error in /balance for user {user_id}: {str(e)}")
        await update.message.reply_text(f"Unexpected error: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅", parse_mode="Markdown")
        logger.info(f"/balance failed due to unexpected error, took {time.time() - start_time:.2f} seconds")

async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM applications WHERE user_id = $1", user_id)
    if row:
        await update.message.reply_text("You've already applied! We'll review soon. 😊")
        return ConversationHandler.END
    await update.message.reply_text("Let's start your application! What's your full name?")
    return NAME

async def apply_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Great! What's your email?")
    return EMAIL

async def apply_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['email'] = update.message.text
    await update.message.reply_text("Tell me about your climbing experience (e.g., beginner, years climbing).")
    return CLIMB_EXP

async def apply_climb_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['climb_exp'] = update.message.text
    await update.message.reply_text("What's your interest in Web3/English learning (e.g., building dApps, improving tech English)?")
    return WEB3_INTEREST

async def apply_web3_interest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['web3_interest'] = update.message.text
    await update.message.reply_text("Why do you want to join EmpowerTours (be detailed – this helps us select!)?")
    return WHY_JOIN

async def apply_why_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['why_join'] = update.message.text
    user_id = str(update.effective_user.id)
    async with db_pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO applications (user_id, name, email, climb_exp, web3_interest, why_join, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        ''', user_id, context.user_data['name'], context.user_data['email'], context.user_data['climb_exp'], context.user_data['web3_interest'], context.user_data['why_join'], 'pending')
    await update.message.reply_text("Application submitted! We'll review and notify you soon. Thanks! 🎉")
    # Notify owner (replace with your Telegram ID)
    await context.bot.send_message(YOUR_TELEGRAM_ID, f"New application from @{update.effective_user.username}: \nName: {context.user_data['name']}\nEmail: {context.user_data['email']}\nClimbing Exp: {context.user_data['climb_exp']}\nWeb3 Interest: {context.user_data['web3_interest']}\nWhy Join: {context.user_data['why_join']}")
    return ConversationHandler.END

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    user_id = str(update.effective_user.id)
    if user_id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("Only the owner can approve applications! 😅")
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Use: /approve [user_id]")
        return
    applicant_id = args[0]
    async with db_pool.acquire() as conn:
        result = await conn.execute("UPDATE applications SET status = $1 WHERE user_id = $2", 'approved', applicant_id)
    if int(result.split()[-1]) > 0:
        await context.bot.send_message(applicant_id, "Congrats! Your application is approved. Now connect your wallet with /connectwallet and create a profile with /createprofile. Welcome aboard! 🧗")
        await update.message.reply_text(f"Approved user {applicant_id}.")
    else:
        await update.message.reply_text(f"No application found for user {applicant_id}.")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    user_id = str(update.effective_user.id)
    if user_id != YOUR_TELEGRAM_ID:
        await update.message.reply_text("Only the owner can reject applications! 😅")
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Use: /reject [user_id]")
        return
    applicant_id = args[0]
    async with db_pool.acquire() as conn:
        result = await conn.execute("UPDATE applications SET status = $1 WHERE user_id = $2", 'rejected', applicant_id)
    if int(result.split()[-1]) > 0:
        await context.bot.send_message(applicant_id, "Thanks for applying! Unfortunately, we can't approve at this time. Feel free to reapply or contact support.")
        await update.message.reply_text(f"Rejected user {applicant_id}.")
    else:
        await update.message.reply_text(f"No application found for user {applicant_id}.")

# Add to your application handlers list
apply_handler = ConversationHandler(
    entry_points=[CommandHandler('apply', apply_start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_name)],
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_email)],
        CLIMB_EXP: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_climb_exp)],
        WEB3_INTEREST: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_web3_interest)],
        WHY_JOIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_why_join)],
    },
    fallbacks=[]
)

async def handle_tx_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    user_id = str(update.effective_user.id)
    logger.info(f"Received transaction hash from user {user_id}: {update.message.text} in chat {update.effective_chat.id}")
    if user_id not in pending_wallets or not pending_wallets[user_id].get("awaiting_tx"):
        logger.warning(f"No pending transaction for user {user_id}")
        await update.message.reply_text("No pending transaction found. Use /createprofile, /buyTours, or another command again! 😅")
        logger.info(f"/handle_tx_hash no pending transaction, took {time.time() - start_time:.2f} seconds")
        return
    if not w3:
        logger.error("Web3 not initialized, transaction handling disabled")
        await update.message.reply_text("Transaction handling unavailable due to blockchain issues. Try again later! 😅")
        logger.info(f"/handle_tx_hash failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    tx_hash = update.message.text.strip()
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        await update.message.reply_text("Invalid transaction hash. Send a valid hash (e.g., 0x123...).")
        logger.info(f"/handle_tx_hash failed due to invalid hash, took {time.time() - start_time:.2f} seconds")
        return
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt and receipt.status:
            action = "Action completed"
            if "createProfile" in pending_wallets[user_id]["tx_data"]["data"]:
                action = "Profile created with 1 $TOURS funded to your wallet"
            elif "buyTours" in pending_wallets[user_id]["tx_data"]["data"]:
                amount = int.from_bytes(bytes.fromhex(pending_wallets[user_id]["tx_data"]["data"][10:]), byteorder='big') / 10**18
                action = f"Successfully purchased {amount} $TOURS"
            elif "transfer" in pending_wallets[user_id]["tx_data"]["data"]:
                action = "Successfully sent $TOURS to the recipient"
            elif "createClimbingLocation" in pending_wallets[user_id]["tx_data"]["data"]:
                action = f"Climb '{pending_wallets[user_id].get('name', 'Unknown')}' ({pending_wallets[user_id].get('difficulty', 'Unknown')}) created"
            await update.message.reply_text(f"Transaction confirmed! [Tx: {tx_hash}]({EXPLORER_URL}/tx/{tx_hash}) 🪙 {action}.", parse_mode="Markdown")
            if CHAT_HANDLE and TELEGRAM_TOKEN:
                message = f"New activity by {escape_html(update.effective_user.username or update.effective_user.first_name)} on EmpowerTours! 🧗 <a href=\"{EXPLORER_URL}/tx/{tx_hash}\">Tx: {escape_html(tx_hash)}</a>"
                await send_notification(CHAT_HANDLE, message)
            if user_id in pending_wallets and pending_wallets[user_id].get("next_tx"):
                next_tx_data = pending_wallets[user_id]["next_tx"]
                if next_tx_data["type"] == "create_climbing_location":
                    nonce = w3.eth.get_transaction_count(pending_wallets[user_id]["wallet_address"])
                    tx = contract.functions.createClimbingLocation(
                        next_tx_data["name"],
                        next_tx_data["difficulty"],
                        next_tx_data["latitude"],
                        next_tx_data["longitude"],
                        next_tx_data["photo_hash"]
                    ).build_transaction({
                        'chainId': 10143,
                        'from': pending_wallets[user_id]["wallet_address"],
                        'nonce': nonce,
                        'gas': 300000,
                        'gasPrice': w3.eth.gas_price
                    })
                    pending_wallets[user_id] = {
                        "awaiting_tx": True,
                        "tx_data": tx,
                        "wallet_address": pending_wallets[user_id]["wallet_address"],
                        "timestamp": time.time(),
                        "name": next_tx_data["name"],
                        "difficulty": next_tx_data["difficulty"],
                        "latitude": next_tx_data["latitude"],
                        "longitude": next_tx_data["longitude"],
                        "photo_hash": next_tx_data["photo_hash"]
                    }
                    try:
                        with open("pending_wallets.json", "w") as f:
                            json.dump(pending_wallets, f, default=str)
                        logger.info(f"Saved pending_wallets for user {user_id} with next_tx")
                    except Exception as e:
                        logger.error(f"Error saving pending_wallets: {str(e)}")
                    await update.message.reply_text(
                        f"Approval confirmed! Now open https://version1-production.up.railway.app/public/connect.html?userId={user_id} to sign the transaction for climb '{next_tx_data['name']}' ({next_tx_data['difficulty']}) using 10 $TOURS."
                    )
                    logger.info(f"/handle_tx_hash processed approval, next transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
                    return
            del pending_wallets[user_id]
            try:
                with open("pending_wallets.json", "w") as f:
                    json.dump(pending_wallets, f, default=str)
                logger.info(f"Saved pending_wallets after clearing for user {user_id}")
            except Exception as e:
                logger.error(f"Error saving pending_wallets: {str(e)}")
            logger.info(f"/handle_tx_hash confirmed for user {user_id}, took {time.time() - start_time:.2f} seconds")
        else:
            await update.message.reply_text("Transaction failed or pending. Check and try again! 😅")
            logger.info(f"/handle_tx_hash failed or pending, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in handle_tx_hash: {str(e)}, took {time.time() - start_time:.2f} seconds")
        await update.message.reply_text(f"Error: {str(e)}. Try again! 😅")

async def monitor_events(context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    global last_processed_block
    if not w3 or not contract:
        logger.error("Web3 or contract not initialized, cannot monitor events")
        logger.info(f"/monitor_events failed due to Web3 issues, took {time.time() - start_time:.2f} seconds")
        return
    try:
        latest_block = w3.eth.get_block_number()
        if last_processed_block == 0:
            last_processed_block = max(0, latest_block - 100)
        end_block = min(last_processed_block + 10, latest_block + 1)
        for block_number in range(last_processed_block + 1, end_block):
            logger.info(f"Processing block {block_number}")
            block = w3.eth.get_block(block_number, full_transactions=True)
            for tx in block.transactions:
                receipt = w3.eth.get_transaction_receipt(tx.hash.hex())
                if receipt and receipt.status:
                    for log in receipt.logs:
                        if log.address.lower() == Web3.to_checksum_address(CONTRACT_ADDRESS).lower():
                            try:
                                event_map = {
                                    w3.keccak(text="ProfileCreated(address,uint256)").hex(): (
                                        contract.events.ProfileCreated,
                                        lambda e: f"New climber joined EmpowerTours! 🧗 Address: <a href=\"{EXPLORER_URL}/address/{e.args.user}\">{e.args.user[:6]}...</a>"
                                    ),
                                    w3.keccak(text="ProfileCreatedEnhanced(address,uint256,string,uint256)").hex(): (
                                        contract.events.ProfileCreatedEnhanced,
                                        lambda e: f"New climber with Farcaster profile joined EmpowerTours! 🧗 Address: <a href=\"{EXPLORER_URL}/address/{e.args.user}\">{e.args.user[:6]}...</a>"
                                    ),
                                    w3.keccak(text="JournalEntryAdded(uint256,address,string,uint256)").hex(): (
                                        contract.events.JournalEntryAdded,
                                        lambda e: f"New journal entry #{e.args.entryId} by <a href=\"{EXPLORER_URL}/address/{e.args.author}\">{e.args.author[:6]}...</a> on EmpowerTours! 📝"
                                    ),
                                    w3.keccak(text="JournalEntryAddedEnhanced(uint256,address,uint256,string,string,string,bool,uint256)").hex(): (
                                        contract.events.JournalEntryAddedEnhanced,
                                        lambda e: f"New enhanced journal entry #{e.args.entryId} by <a href=\"{EXPLORER_URL}/address/{e.args.author}\">{e.args.author[:6]}...</a> on EmpowerTours! 📝"
                                    ),
                                    w3.keccak(text="CommentAdded(uint256,address,string,uint256)").hex(): (
                                        contract.events.CommentAdded,
                                        lambda e: f"New comment on journal #{e.args.entryId} by <a href=\"{EXPLORER_URL}/address/{e.args.commenter}\">{e.args.commenter[:6]}...</a> on EmpowerTours! 🗣️"
                                    ),
                                    w3.keccak(text="CommentAddedEnhanced(uint256,address,uint256,string,string,uint256)").hex(): (
                                        contract.events.CommentAddedEnhanced,
                                        lambda e: f"New enhanced comment on journal #{e.args.entryId} by <a href=\"{EXPLORER_URL}/address/{e.args.commenter}\">{e.args.commenter[:6]}...</a> on EmpowerTours! 🗣️"
                                    ),
                                    w3.keccak(text="ClimbingLocationCreated(uint256,address,string,uint256)").hex(): (
                                        contract.events.ClimbingLocationCreated,
                                        lambda e: f"New climb '{e.args.name}' created by <a href=\"{EXPLORER_URL}/address/{e.args.creator}\">{e.args.creator[:6]}...</a> on EmpowerTours! 🪨"
                                    ),
                                    w3.keccak(text="ClimbingLocationCreatedEnhanced(uint256,address,uint256,string,string,int256,int256,bool,uint256)").hex(): (
                                        contract.events.ClimbingLocationCreatedEnhanced,
                                        lambda e: f"New enhanced climb '{e.args.name}' created by <a href=\"{EXPLORER_URL}/address/{e.args.creator}\">{e.args.creator[:6]}...</a> on EmpowerTours! 🪨"
                                    ),
                                    w3.keccak(text="LocationPurchased(uint256,address,uint256)").hex(): (
                                        contract.events.LocationPurchased,
                                        lambda e: f"Climb #{e.args.locationId} purchased by <a href=\"{EXPLORER_URL}/address/{e.args.buyer}\">{e.args.buyer[:6]}...</a> on EmpowerTours! 🪙"
                                    ),
                                    w3.keccak(text="LocationPurchasedEnhanced(uint256,address,uint256,uint256)").hex(): (
                                        contract.events.LocationPurchasedEnhanced,
                                        lambda e: f"Enhanced climb #{e.args.locationId} purchased by <a href=\"{EXPLORER_URL}/address/{e.args.buyer}\">{e.args.buyer[:6]}...</a> on EmpowerTours! 🪙"
                                    ),
                                    w3.keccak(text="TournamentCreated(uint256,uint256,uint256)").hex(): (
                                        contract.events.TournamentCreated,
                                        lambda e: f"New tournament #{e.args.tournamentId} created on EmpowerTours! 🏆"
                                    ),
                                    w3.keccak(text="TournamentCreatedEmbedded(uint256,address,uint256,string,uint256,uint256)").hex(): (
                                        contract.events.TournamentCreatedEmbedded,
                                        lambda e: f"New enhanced tournament #{e.args.tournamentId} created by <a href=\"{EXPLORER_URL}/address/{e.args.creator}\">{e.args.creator[:6]}...</a> on EmpowerTours! 🏆"
                                    ),
                                    w3.keccak(text="TournamentJoined(uint256,address)").hex(): (
                                        contract.events.TournamentJoined,
                                        lambda e: f"Climber <a href=\"{EXPLORER_URL}/address/{e.args.participant}\">{e.args.participant[:6]}...</a> joined tournament #{e.args.tournamentId} on EmpowerTours! 🏆"
                                    ),
                                    w3.keccak(text="TournamentJoinedEnhanced(uint256,address,uint256)").hex(): (
                                        contract.events.TournamentJoinedEnhanced,
                                        lambda e: f"Climber <a href=\"{EXPLORER_URL}/address/{e.args.participant}\">{e.args.participant[:6]}...</a> joined enhanced tournament #{e.args.tournamentId} on EmpowerTours! 🏆"
                                    ),
                                    w3.keccak(text="TournamentEnded(uint256,address,uint256)").hex(): (
                                        contract.events.TournamentEnded,
                                        lambda e: f"Tournament #{e.args.tournamentId} ended! Winner: <a href=\"{EXPLORER_URL}/address/{e.args.winner}\">{e.args.winner[:6]}...</a> Prize: {e.args.pot / 10**18} $TOURS 🏆"
                                    ),
                                    w3.keccak(text="TournamentEndedEnhanced(uint256,address,uint256,uint256)").hex(): (
                                        contract.events.TournamentEndedEnhanced,
                                        lambda e: f"Enhanced tournament #{e.args.tournamentId} ended! Winner: <a href=\"{EXPLORER_URL}/address/{e.args.winner}\">{e.args.winner[:6]}...</a> Prize: {e.args.pot / 10**18} $TOURS 🏆"
                                    ),
                                    w3.keccak(text="FarcasterCastShared(address,uint256,string,string,uint256,uint256)").hex(): (
                                        contract.events.FarcasterCastShared,
                                        lambda e: f"New Farcaster cast shared by <a href=\"{EXPLORER_URL}/address/{e.args.user}\">{e.args.user[:6]}...</a> for {e.args.contentType} #{e.args.contentId} on EmpowerTours! 📢"
                                    ),
                                    w3.keccak(text="FarcasterProfileUpdated(address,uint256,string,string,uint256)").hex(): (
                                        contract.events.FarcasterProfileUpdated,
                                        lambda e: f"Farcaster profile updated by <a href=\"{EXPLORER_URL}/address/{e.args.user}\">{e.args.user[:6]}...</a> on EmpowerTours! 📢"
                                    ),
                                    w3.keccak(text="TokensPurchased(address,uint256,uint256)").hex(): (contract.events.TokensPurchased,
                                        lambda e: f"User <a href=\"{EXPLORER_URL}/address/{e.args.buyer}\">{e.args.buyer[:6]}...</a> bought {e.args.amount / 10**18} $TOURS on EmpowerTours! 🪙"
                                    ),
                                }
                                if log.topics[0].hex() in event_map:
                                    event_class, message_fn = event_map[log.topics[0].hex()]
                                    event = event_class().process_log(log)
                                    message = message_fn(event)
                                    # Auto-announce to group
                                    await send_notification(CHAT_HANDLE, message)
                                    # New: PM user if wallet matches an event arg
                                    user_address = event.args.get('user') or event.args.get('creator') or event.args.get('author') or event.args.get('buyer') or event.args.get('commenter') or event.args.get('participant') or event.args.get('winner')
                                    if user_address:
                                        checksum_user_address = Web3.to_checksum_address(user_address)
                                        if checksum_user_address in reverse_sessions:
                                            user_id = reverse_sessions[checksum_user_address]
                                            user_message = f"Your action succeeded! {message.replace('<a href=', '[Tx: ').replace('</a>', ']')} 🪙 Check details on {EXPLORER_URL}/tx/{receipt.transactionHash.hex()}"
                                            await application.bot.send_message(user_id, user_message, parse_mode="Markdown")
                            except Exception as e:
                                logger.error(f"Error processing event in block {block_number}: {str(e)}")
        last_processed_block = end_block - 1
        logger.info(f"Processed events up to block {last_processed_block}, took {time.time() - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in monitor_events: {str(e)}, took {time.time() - start_time:.2f} seconds")

async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    device_info = (
        f"via_bot={update.message.via_bot.id if update.message.via_bot else 'none'}, "
        f"chat_type={update.message.chat.type}, "
        f"platform={getattr(update.message.via_bot, 'platform', 'unknown')}"
    )
    logger.info(f"Received text message from user {update.effective_user.id} in chat {update.effective_chat.id}: {update.message.text}, {device_info}")
    await update.message.reply_text(
        f"Received message: '{update.message.text}'. Use a valid command like /start or /tutorial. 😅\nDebug: {device_info}"
    )
    logger.info(f"Processed non-command text message, took {time.time() - start_time:.2f} seconds")

@app.on_event("startup")
async def startup_event():
    start_time = time.time()
    global application, webhook_failed, pending_wallets, db_pool
    try:
        # Load pending_wallets
        if os.path.exists("pending_wallets.json"):
            try:
                with open("pending_wallets.json", "r") as f:
                    loaded_wallets = json.load(f)
                    current_time = time.time()
                    pending_wallets.update({
                        k: v for k, v in loaded_wallets.items()
                        if 'timestamp' in v and current_time - v['timestamp'] < 3600
                    })
                logger.info(f"Loaded pending_wallets: {len(pending_wallets)} entries")
            except Exception as e:
                logger.error(f"Error loading pending_wallets: {str(e)}")

        # Check and free port
        port = int(os.getenv("PORT", 8080))
        ports = [port, 8081]
        selected_port = None
        for p in ports:
            logger.info(f"Checking for port {p} availability")
            for attempt in range(1, 4):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('0.0.0.0', p))
                    sock.close()
                    logger.info(f"Port {p} is available")
                    selected_port = p
                    break
                except socket.error as e:
                    logger.error(f"Port {p} in use on attempt {attempt}/3: {str(e)}. Attempting to free port...")
                    try:
                        result = subprocess.run(
                            f"lsof -i :{p} | grep LISTEN | awk '{{print $2}}' | xargs kill -9",
                            shell=True, capture_output=True, text=True
                        )
                        logger.info(f"Port {p} cleanup result: {result.stdout}, {result.stderr}")
                    except subprocess.SubprocessError as se:
                        logger.error(f"Failed to run cleanup command for port {p}: {str(se)}")
                    time.sleep(2)
                    if attempt == 3:
                        logger.error(f"Failed to free port {p} after 3 attempts.")
                        if p == ports[-1]:
                            logger.error("No available ports. Falling back to polling.")
                            webhook_failed = True
                else:
                    break
            if selected_port:
                break

        if not selected_port:
            logger.error("No ports available, proceeding with polling")
            webhook_failed = True

        logger.info("Starting bot initialization")
        initialize_web3()

        # Initialize Postgres pool
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        async with db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    climb_exp TEXT,
                    web3_interest TEXT,
                    why_join TEXT,
                    status TEXT DEFAULT 'pending'
                )
            ''')

        # Initialize Telegram Application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        logger.info("Application initialized")

        # Register command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help))
        application.add_handler(CommandHandler("debug", debug))
        application.add_handler(CommandHandler("connectwallet", connect_wallet))
        application.add_handler(CommandHandler("createprofile", create_profile))
        application.add_handler(CommandHandler("tutorial", tutorial))
        application.add_handler(CommandHandler("journal", journal_entry))
        application.add_handler(CommandHandler("testlink", testlink))
        application.add_handler(CommandHandler("testplain", testplain))
        application.add_handler(CommandHandler("testmarkdown", testmarkdown))
        application.add_handler(CommandHandler("testentity", testentity))
        application.add_handler(CommandHandler("testshort", testshort))
        application.add_handler(CommandHandler("clearcache", clearcache))
        application.add_handler(CommandHandler("forcewebhook", forcewebhook))
        application.add_handler(CommandHandler("comment", add_comment))
        application.add_handler(CommandHandler("buildaclimb", buildaclimb))
        application.add_handler(CommandHandler("purchaseclimb", purchase_climb))
        application.add_handler(CommandHandler("findaclimb", findaclimb))
        application.add_handler(CommandHandler("createtournament", create_tournament))
        application.add_handler(CommandHandler("jointournament", join_tournament))
        application.add_handler(CommandHandler("endtournament", end_tournament))
        application.add_handler(CommandHandler("balance", balance))
        application.add_handler(CommandHandler("buyTours", buy_tours))
        application.add_handler(CommandHandler("sendTours", send_tours))
        application.add_handler(CommandHandler("ping", ping))
        application.add_handler(CommandHandler("approve", approve))
        application.add_handler(CommandHandler("reject", reject))
        application.add_handler(apply_handler)
        application.add_handler(MessageHandler(filters.Regex(r'^0x[a-fA-F0-9]{64}$'), handle_tx_hash))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.LOCATION, handle_location))
        application.add_handler(MessageHandler(filters.COMMAND, debug_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_message))
        logger.info("Command handlers registered successfully")

        # Schedule monitor_events with 60-second interval
        if application.job_queue:
            logger.info("JobQueue available, scheduling monitor_events")
            application.job_queue.run_repeating(monitor_events, interval=60, first=10)
        else:
            logger.warning("JobQueue not available, monitor_events not scheduled")

        # Initialize and start application
        await application.initialize()
        logger.info("Application initialized via initialize()")

        # Set webhook with increased max_connections
        logger.info("Forcing webhook reset on startup")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            webhook_success = False
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
                                webhook_success = True
                                break
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
            if not webhook_success:
                logger.error("All webhook reset attempts failed. Forcing polling mode.")
                webhook_failed = True

        if not webhook_success or webhook_failed:
            logger.info("Webhook failed or not set, starting polling")
            await application.start()
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        else:
            logger.info("Webhook set successfully, starting application")
            await application.start()
        webhook_info = await check_webhook()
        logger.info(f"Webhook verification: {webhook_info}")
        logger.info(f"Bot startup complete, took {time.time() - start_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Error in startup_event: {str(e)}, took {time.time() - start_time:.2f} seconds")
        webhook_failed = True
        raise

@app.on_event("shutdown")
async def shutdown_event():
    start_time = time.time()
    global application, db_pool
    logger.info("Received shutdown signal")
    if application:
        try:
            await application.stop()
            await application.updater.stop()
            logger.info(f"Application shutdown complete, took {time.time() - start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}, took {time.time() - start_time:.2f} seconds")
    if db_pool:
        await db_pool.close()
        logger.info("Postgres pool closed")

@app.get("/public/{path:path}")
async def log_static_access(path: str, request: Request):
    start_time = time.time()
    logger.info(f"Access attempt to static file: /public/{path}, url={request.url}")
    file_path = os.path.join("public", path)
    if not os.path.exists(file_path):
        for fname in os.listdir("public"):
            if fname.lower() == path.lower():
                file_path = os.path.join("public", fname)
                logger.info(f"Found case-insensitive match for {path}: {file_path}")
                break
        else:
            logger.error(f"Static file not found: {file_path}")
            raise HTTPException(status_code=404, detail=f"File {path} not found in public directory")
    response = FileResponse(file_path)
    response.headers["Cache-Control"] = "public, max-age=86400"
    response.headers["ETag"] = f"{os.path.getmtime(file_path)}"
    logger.info(f"/public/{path} served, took {time.time() - start_time:.2f} seconds")
    return response

@app.get("/get_transaction")
async def get_transaction(userId: str):
    start_time = time.time()
    logger.info(f"Received /get_transaction request for user {userId}")
    try:
        if userId in pending_wallets and pending_wallets[userId].get("awaiting_tx"):
            if pending_wallets[userId].get("tx_served", False):
                # Already served once—prevent repeat
                logger.info(f"Transaction already served for user {userId}, ignoring repeat poll")
                return {"transaction": None}
            pending_wallets[userId]["tx_served"] = True  # Mark as served
            try:
                with open("pending_wallets.json", "w") as f:
                    json.dump(pending_wallets, f, default=str)
            except Exception as e:
                logger.error(f"Error saving pending_wallets: {str(e)}")
            logger.info(f"Transaction served (once) for user {userId}: {pending_wallets[userId]['tx_data']}, took {time.time() - start_time:.2f} seconds")
            return {"transaction": pending_wallets[userId]["tx_data"]}
        logger.info(f"No transaction found for user {userId}, took {time.time() - start_time:.2f} seconds")
        return {"transaction": None}
    except Exception as e:
        logger.error(f"Error in /get_transaction for user {userId}: {str(e)}, took {time.time() - start_time:.2f} seconds")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit_wallet")
async def submit_wallet(request: Request):
    start_time = time.time()
    try:
        data = await request.json()
        user_id = data.get("userId")
        wallet_address = data.get("walletAddress")
        if not user_id or not wallet_address:
            logger.error(f"Missing userId or walletAddress in /submit_wallet:{data}")
            raise HTTPException(status_code=400, detail="Missing userId or walletAddress")
        logger.info(f"Received wallet submission for user {user_id}: {wallet_address}")
        
        # Validate wallet address
        if not w3 or not w3.is_address(wallet_address):
            logger.error(f"Invalid wallet address or Web3 not initialized: {wallet_address}")
            await application.bot.send_message(user_id, "Invalid wallet address or blockchain unavailable. Try /connectwallet again. 😅")
            logger.info(f"/submit_wallet failed due to invalid address or Web3, took {time.time() - start_time:.2f} seconds")
            return {"status": "error"}
        
        # Process wallet even if not in pending_wallets to handle edge cases
        if user_id not in pending_wallets or not pending_wallets[user_id].get("awaiting_wallet"):
            logger.warning(f"No pending wallet connection for user {user_id}, proceeding anyway")
        
        try:
            checksum_address = w3.to_checksum_address(wallet_address)
            sessions[user_id] = {"wallet_address": checksum_address}
            reverse_sessions[checksum_address] = user_id  # Add reverse map for event monitoring
            await application.bot.send_message(
                user_id,
                f"Wallet [{checksum_address[:6]}...]({EXPLORER_URL}/address/{checksum_address}) connected! Use /createprofile to create your profile or /balance to check your status. 🪙",
                parse_mode="Markdown"
            )
            if user_id in pending_wallets:
                del pending_wallets[user_id]
                try:
                    with open("pending_wallets.json", "w") as f:
                        json.dump(pending_wallets, f, default=str)
                    logger.info(f"Saved pending_wallets after clearing for user {user_id}")
                except Exception as e:
                    logger.error(f"Error saving pending_wallets: {str(e)}")
            logger.info(f"/submit_wallet processed for user {user_id}, wallet {checksum_address}, took {time.time() - start_time:.2f} seconds")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error processing wallet address for user {user_id}: {str(e)}")
            await application.bot.send_message(user_id, f"Error connecting wallet: {str(e)}. Try /connectwallet again. 😅")
            return {"status": "error"}
    except Exception as e:
        logger.error(f"Error in /submit_wallet: {str(e)}, took {time.time() - start_time:.2f} seconds")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit_tx")
async def submit_tx(request: Request):
    start_time = time.time()
    try:
        data = await request.json()
        user_id = data.get("userId")
        tx_hash = data.get("txHash")
        if isinstance(tx_hash, dict):
            tx_hash = tx_hash.get("transactionHash") or tx_hash.get("txHash")
            logger.info(f"Extracted txHash from object: {tx_hash}")
        if not user_id or not tx_hash:
            logger.error(f"Missing userId or txHash in /submit_tx: {data}")
            raise HTTPException(status_code=400, detail="Missing userId or txHash")
        if not isinstance(tx_hash, str) or not tx_hash.startswith("0x") or len(tx_hash) != 66:
            logger.error(f"Invalid txHash format: {tx_hash}")
            raise HTTPException(status_code=400, detail="Invalid txHash format")
        logger.info(f"Received transaction hash for user {user_id}: {tx_hash}")
        if not w3:
            logger.error("Web3 not initialized, transaction handling disabled")
            raise HTTPException(status_code=500, detail="Blockchain unavailable")
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt and receipt.status:
                if user_id in pending_wallets:
                    tx_data = pending_wallets[user_id]
                    input_data = tx_data.get("tx_data", {}).get("data", "")
                    success_message = f"Transaction confirmed! [Tx: {tx_hash}]({EXPLORER_URL}/tx/{tx_hash}) 🪙 Action completed successfully."
                    if input_data.startswith('0x00547664'):  # createProfile
                        success_message = f"Transaction confirmed! [Tx: {tx_hash}]({EXPLORER_URL}/tx/{tx_hash}) 🪙 Profile created with 1 $TOURS funded to your wallet."
                    elif input_data.startswith('0x9954e40d'):  # buyTours
                        amount = int.from_bytes(bytes.fromhex(input_data[10:]), byteorder='big') / 10**18
                        success_message = f"Transaction confirmed! [Tx: {tx_hash}]({EXPLORER_URL}/tx/{tx_hash}) 🪙 Successfully purchased {amount} $TOURS."
                    elif input_data.startswith('0xa9059cbb'):  # transfer (sendTours)
                        success_message = f"Transaction confirmed! [Tx: {tx_hash}]({EXPLORER_URL}/tx/{tx_hash}) 🪙 Successfully sent $TOURS to the recipient."
                    elif input_data.startswith('0xfe985ae0'):  # createClimbingLocation
                        success_message = f"Transaction confirmed! [Tx: {tx_hash}]({EXPLORER_URL}/tx/{tx_hash}) 🪙 Climb '{tx_data.get('name', 'Unknown')}' ({tx_data.get('difficulty', 'Unknown')}) created!"
                    if CHAT_HANDLE and TELEGRAM_TOKEN:
                        message = f"New activity by user {user_id} on EmpowerTours! 🧗 <a href=\"{EXPLORER_URL}/tx/{tx_hash}\">Tx: {escape_html(tx_hash)}</a>"
                        await send_notification(CHAT_HANDLE, message)
                    await application.bot.send_message(user_id, success_message, parse_mode="Markdown")
                    if user_id in pending_wallets and pending_wallets[user_id].get("next_tx"):
                        next_tx_data = pending_wallets[user_id]["next_tx"]
                        if next_tx_data["type"] == "create_climbing_location":
                            nonce = w3.eth.get_transaction_count(pending_wallets[user_id]["wallet_address"])
                            tx = contract.functions.createClimbingLocation(
                                next_tx_data["name"],
                                next_tx_data["difficulty"],
                                next_tx_data["latitude"],
                                next_tx_data["longitude"],
                                next_tx_data["photo_hash"]
                            ).build_transaction({
                                'chainId': 10143,
                                'from': pending_wallets[user_id]["wallet_address"],
                                'nonce': nonce,
                                'gas': 300000,
                                'gasPrice': w3.eth.gas_price
                            })
                            pending_wallets[user_id] = {
                                "awaiting_tx": True,
                                "tx_data": tx,
                                "wallet_address": pending_wallets[user_id]["wallet_address"],
                                "timestamp": time.time(),
                                "name": next_tx_data["name"],
                                "difficulty": next_tx_data["difficulty"],
                                "latitude": next_tx_data["latitude"],
                                "longitude": next_tx_data["longitude"],
                                "photo_hash": next_tx_data["photo_hash"]
                            }
                            try:
                                with open("pending_wallets.json", "w") as f:
                                    json.dump(pending_wallets, f, default=str)
                                logger.info(f"Saved pending_wallets for user {user_id} with next_tx")
                            except Exception as e:
                                logger.error(f"Error saving pending_wallets: {str(e)}")
                            await application.bot.send_message(
                                user_id,
                                f"Approval confirmed! Now open https://version1-production.up.railway.app/public/connect.html?userId={user_id} to sign the transaction for climb '{next_tx_data['name']}' ({next_tx_data['difficulty']}) using 10 $TOURS."
                            )
                            logger.info(f"/submit_tx processed approval, next transaction built for user {user_id}, took {time.time() - start_time:.2f} seconds")
                            return {"status": "success"}
                    del pending_wallets[user_id]
                    try:
                        with open("pending_wallets.json", "w") as f:
                            json.dump(pending_wallets, f, default=str)
                        logger.info(f"Saved pending_wallets after clearing for user {user_id}")
                    except Exception as e:
                        logger.error(f"Error saving pending_wallets: {str(e)}")
                logger.info(f"/submit_tx confirmed for user {user_id}, took {time.time() - start_time:.2f} seconds")
                return {"status": "success"}
            else:
                # Check for specific revert reasons
                try:
                    tx = w3.eth.get_transaction(tx_hash)
                    input_data = tx['input']
                    if input_data.startswith('0x00547664'):  # createProfile
                        contract.functions.createProfile().call({
                            'from': tx['from'],
                            'value': tx['value'],
                            'gas': tx['gas']
                        })
                    elif input_data.startswith('0x9954e40d'):  # buyTours
                        amount = int.from_bytes(input_data[4:], byteorder='big')
                        contract.functions.buyTours(amount).call({
                            'from': tx['from'],
                            'value': tx['value'],
                            'gas': tx['gas']
                        })
                    elif input_data.startswith('0xa9059cbb'):  # transfer (sendTours)
                        recipient = '0x' + input_data[34:74]
                        amount = int.from_bytes(input_data[74:], byteorder='big') / 10**18
                        tours_contract.functions.transfer(recipient, amount * 10**18).call({
                            'from': tx['from'],
                            'gas': tx['gas']
                        })
                    elif input_data.startswith('0xfe985ae0'):  # createClimbingLocation
                        name = w3.to_text(bytes.fromhex(input_data[74:138])).rstrip('\x00')
                        difficulty = w3.to_text(bytes.fromhex(input_data[202:234])).rstrip('\x00')
                        latitude = int.from_bytes(bytes.fromhex(input_data[138:170]), byteorder='big', signed=True)
                        longitude = int.from_bytes(bytes.fromhex(input_data[170:202]), byteorder='big', signed=True)
                        photo_hash = w3.to_text(bytes.fromhex(input_data[266:])).rstrip('\x00')
                        contract.functions.createClimbingLocation(name, difficulty, latitude, longitude, photo_hash).call({
                            'from': tx['from'],
                            'gas': tx['gas']
                        })
                    else:
                        raise Exception("Unknown function call")
                except Exception as e:
                    revert_reason = str(e)
                    logger.error(f"Transaction {tx_hash} reverted: {revert_reason}")
                    if "ProfileExists" in revert_reason:
                        await application.bot.send_message(
                            user_id,
                            f"Transaction failed: Profile already exists for wallet [{tx['from'][:6]}...]({EXPLORER_URL}/address/{tx['from']})! Use /balance to check your status or try commands like /journal or /buildaclimb. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅",
                            parse_mode="Markdown"
                        )
                    elif "ProfileRequired" in revert_reason:
                        await application.bot.send_message(
                            user_id,
                            f"Transaction failed: Aprofile is required. Use /createprofile first, then try again. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅",
                            parse_mode="Markdown"
                        )
                    elif "InsufficientMonSent" in revert_reason:
                        await application.bot.send_message(
                            user_id,
                            f"Transaction failed: Insufficient $MON sent. Top up at https://testnet.monad.xyz/faucet and try again. 😅"
                        )
                    elif "InsufficientTokenBalance" in revert_reason:
                        await application.bot.send_message(
                            user_id,
                            f"Transaction failed: Insufficient $TOURS. Use /buyTours to get more $TOURS. Contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅",
                            parse_mode="Markdown"
                        )
                    elif "InvalidLocationId" in revert_reason or "InvalidEntryId" in revert_reason:
                        await application.bot.send_message(
                            user_id,
                            f"Transaction failed: Invalid climb or entry ID. Check with /findaclimb or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅",
                            parse_mode="Markdown"
                        )
                    else:
                        await application.bot.send_message(
                            user_id,
                            f"Transaction failed: {revert_reason}. Check parameters or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅",
                            parse_mode="Markdown"
                        )
                logger.info(f"/submit_tx failed or pending for user {user_id}, took {time.time() - start_time:.2f} seconds")
                raise HTTPException(status_code=400, detail="Transaction failed or pending")
        except Exception as e:
            logger.error(f"Error verifying transaction for user {user_id}: {str(e)}, took {time.time() - start_time:.2f} seconds")
            await application.bot.send_message(
                user_id,
                f"Error verifying transaction: {str(e)}. Try again or contact support at [EmpowerTours Chat](https://t.me/empowertourschat). 😅",
                parse_mode="Markdown"
            )
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error in /submit_tx: {str(e)}, took {time.time() - start_time:.2f} seconds")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def webhook(request: Request):
    start_time = time.time()
    try:
        update = await request.json()
        logger.info(f"Received webhook update: update_id={update.get('update_id')}, message_id={update.get('message', {}).get('message_id')}")
        if not application:
            logger.error("Application not initialized, cannot process webhook update")
            raise HTTPException(status_code=500, detail="Application not initialized")
        async with asyncio.timeout(5):
            await application.process_update(Update.de_json(update, application.bot))
        logger.info(f"Processed webhook update, took {time.time() - start_time:.2f} seconds")
        return {"status": "success"}
    except asyncio.TimeoutError:
        logger.error(f"Webhook processing timed out, took {time.time() - start_time:.2f} seconds")
        return {"status": "timeout"}
    except Exception as e:
        logger.error(f"Error in /webhook: {str(e)}, took {time.time() - start_time:.2f} seconds")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
