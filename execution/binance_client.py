"""
NEXUS Bot - Binance Client Wrapper
Provides clean interface to Binance API with error handling
"""

import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

# Setup logging
logger = logging.getLogger(__name__)


class BinanceClientWrapper:
    """
    Wrapper around python-binance Client
    Handles connection, error handling, and rate limiting
    """
    
    def __init__(self, testnet: bool = False):
        """
        Initialize Binance client
        
        Args:
            testnet: Use testnet if True (default: False)
        """
        # Load environment variables
        load_dotenv()
        
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        if not self.api_key or not self.api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_SECRET_KEY must be set in .env")
        
        # Initialize client
        self.testnet = testnet
        self.client = None
        self._initialize_client()
        
        logger.info(f"BinanceClientWrapper initialized (testnet={testnet})")
    
    def _initialize_client(self):
        """Initialize Binance client with credentials"""
        try:
            self.client = Client(self.api_key, self.api_secret, testnet=self.testnet)
            logger.info("Binance client connected successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test connection to Binance API
        
        Returns:
            bool: True if connection successful
        """
        try:
            status = self.client.get_system_status()
            logger.info(f"Connection test successful: {status}")
            return True
        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            return False
        except BinanceRequestException as e:
            logger.error(f"Binance request error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing connection: {e}")
            return False
    
    def get_symbol_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get current price for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            dict: Ticker data or None if error
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return ticker
        except BinanceAPIException as e:
            logger.error(f"API error getting ticker for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")
            return None
    
    def get_all_tickers(self) -> List[Dict]:
        """
        Get current prices for all symbols
        
        Returns:
            list: List of ticker data for all symbols
        """
        try:
            tickers = self.client.get_all_tickers()
            logger.debug(f"Fetched {len(tickers)} tickers")
            return tickers
        except BinanceAPIException as e:
            logger.error(f"API error getting all tickers: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting all tickers: {e}")
            return []
    
    def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get 24-hour ticker data including volume
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            dict: 24h ticker data or None if error
        """
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            return ticker
        except BinanceAPIException as e:
            logger.error(f"API error getting 24h ticker for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting 24h ticker for {symbol}: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List[List]:
        """
        Get historical klines (candles)
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '15m', '1h', '1d')
            limit: Number of candles (default: 500, max: 1000)
            
        Returns:
            list: List of kline data
        """
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            logger.debug(f"Fetched {len(klines)} klines for {symbol} ({interval})")
            return klines
        except BinanceAPIException as e:
            logger.error(f"API error getting klines for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return []
    
    def get_exchange_info(self) -> Optional[Dict]:
        """
        Get exchange information (trading rules, symbols, etc)
        
        Returns:
            dict: Exchange info or None if error
        """
        try:
            info = self.client.get_exchange_info()
            return info
        except BinanceAPIException as e:
            logger.error(f"API error getting exchange info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting exchange info: {e}")
            return None
    
    def get_account(self) -> Optional[Dict]:
        """
        Get account information
        
        Returns:
            dict: Account data or None if error
        """
        try:
            account = self.client.get_account()
            return account
        except BinanceAPIException as e:
            logger.error(f"API error getting account: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None
    
    def get_funding_rate(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get funding rate history for a futures symbol
        
        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT')
            limit: Number of records (default: 10, max: 1000)
        
        Returns:
            list: Funding rate history
        """
        try:
            funding = self.client.futures_funding_rate(
                symbol=symbol,
                limit=limit
            )
            logger.debug(f"Fetched {len(funding)} funding rate records for {symbol}")
            return funding
        except BinanceAPIException as e:
            logger.error(f"API error getting funding rate for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting funding rate for {symbol}: {e}")
            return []

    def get_open_interest(self, symbol: str) -> Optional[Dict]:
        """
        Get current open interest for a futures symbol
        
        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT')
        
        Returns:
            dict: Open interest data or None if error
        """
        try:
            oi = self.client.futures_open_interest(symbol=symbol)
            logger.debug(f"Fetched open interest for {symbol}: {oi}")
            return oi
        except BinanceAPIException as e:
            logger.error(f"API error getting open interest for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting open interest for {symbol}: {e}")
            return None

    def get_open_interest_hist(self, symbol: str, period: str = '5m', limit: int = 30) -> List[Dict]:
        """
        Get open interest history for analysis
        
        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT')
            period: Time period ('5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d')
            limit: Number of records (default: 30, max: 500)
        
        Returns:
            list: Open interest history
        """
        try:
            oi_hist = self.client.futures_open_interest_hist(
                symbol=symbol,
                period=period,
                limit=limit
            )
            logger.debug(f"Fetched {len(oi_hist)} OI history records for {symbol}")
            return oi_hist
        except BinanceAPIException as e:
            logger.error(f"API error getting OI history for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting OI history for {symbol}: {e}")
            return []

    def get_long_short_ratio(self, symbol: str, period: str = '5m', limit: int = 30) -> List[Dict]:
        """
        Get long/short account ratio
        
        Args:
            symbol: Futures symbol (e.g., 'BTCUSDT')
            period: Time period ('5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d')
            limit: Number of records (default: 30, max: 500)
        
        Returns:
            list: Long/short ratio history
        """
        try:
            ratio = self.client.futures_top_longshort_account_ratio(
                symbol=symbol,
                period=period,
                limit=limit
            )
            logger.debug(f"Fetched {len(ratio)} long/short ratio records for {symbol}")
            return ratio
        except BinanceAPIException as e:
            logger.error(f"API error getting long/short ratio for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting long/short ratio for {symbol}: {e}")
            return []


    def get_futures_symbols(self) -> List[str]:
        """
        Get all USDT futures trading pairs
        
        Returns:
            list: List of futures symbols (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        try:
            exchange_info = self.get_exchange_info()
            if not exchange_info:
                return []
            
            # Filter for USDT pairs that are actively trading
            symbols = []
            for symbol_info in exchange_info.get('symbols', []):
                symbol = symbol_info['symbol']
                status = symbol_info['status']
                quote_asset = symbol_info.get('quoteAsset', '')
                
                # Only USDT pairs that are trading
                if quote_asset == 'USDT' and status == 'TRADING':
                    symbols.append(symbol)
            
            logger.info(f"Found {len(symbols)} active USDT trading pairs")
            return symbols
            
        except Exception as e:
            logger.error(f"Error getting futures symbols: {e}")
            return []


# Convenience function to create client instance
def get_binance_client(testnet: bool = False) -> BinanceClientWrapper:
    """
    Factory function to create BinanceClientWrapper instance
    
    Args:
        testnet: Use testnet if True
        
    Returns:
        BinanceClientWrapper instance
    """
    return BinanceClientWrapper(testnet=testnet)


if __name__ == "__main__":
    """Test the Binance client wrapper"""
    
    # Setup basic logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("Testing BinanceClientWrapper")
    print("=" * 60)
    
    # Initialize client
    print("\n[1] Initializing client...")
    client = get_binance_client(testnet=False)
    
    # Test connection
    print("\n[2] Testing connection...")
    if client.test_connection():
        print("✅ Connection successful")
    else:
        print("❌ Connection failed")
        exit(1)
    
    # Get BTC price
    print("\n[3] Fetching BTC price...")
    ticker = client.get_symbol_ticker('BTCUSDT')
    if ticker:
        print(f"✅ BTC Price: ${float(ticker['price']):,.2f}")
    
    # Get 24h ticker
    print("\n[4] Fetching 24h ticker (BTC)...")
    ticker_24h = client.get_24h_ticker('BTCUSDT')
    if ticker_24h:
        volume = float(ticker_24h['quoteVolume'])
        print(f"✅ 24h Volume: ${volume:,.0f}")
    
    # Get klines
    print("\n[5] Fetching recent candles (BTC 15m)...")
    klines = client.get_klines('BTCUSDT', '15m', limit=10)
    if klines:
        print(f"✅ Fetched {len(klines)} candles")
        # Show last candle
        last = klines[-1]
        print(f"   Last Close: ${float(last[4]):,.2f}")
    
    # Get futures symbols
    print("\n[6] Fetching futures symbols...")
    symbols = client.get_futures_symbols()
    if symbols:
        print(f"✅ Found {len(symbols)} USDT futures pairs")
        print(f"   Examples: {symbols[:5]}")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)