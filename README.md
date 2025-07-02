<<<<<<< HEAD
# 🚀 JumpTrader - AI-Powered Trading Dashboard

A comprehensive, modular trading dashboard for monitoring Binance perpetual futures with real-time AI-powered signal detection.

## 🎯 Features

### Data Ingestion
- **Real-time Binance Data**: Stream all ~500 perpetual contracts
- **Multi-timeframe Candles**: 1m (24h), 1h (7 days), 4h, 1d data
- **WebSocket Streams**: Real-time ticker and kline updates
- **Orion Integration**: Full-market snapshots every 15 seconds (future)
- **Rate Limiting**: Intelligent API rate management

### Signal Processing
- **Volume Analysis**: Spike detection with configurable thresholds
- **Price Momentum**: Stair-step patterns and acceleration detection
- **Range Analysis**: Breakout and consolidation identification
- **Multi-timeframe Signals**: 1h and 24h change analysis
- **Custom Thresholds**: Configurable signal sensitivity

### Web UI
- **Interactive Dashboard**: Real-time data table with sorting/filtering
- **Signal Summary**: Visual breakdown of signal types
- **Performance Metrics**: Market overview and statistics
- **Auto-refresh**: Configurable update intervals
- **Responsive Design**: Works on desktop and mobile

### Architecture
- **Modular Design**: Separate packages for data, signals, UI, clients
- **Extensible**: Easy to add new data sources and signal types
- **Configuration**: Centralized settings management
- **Logging**: Comprehensive error tracking and monitoring

## 🛠️ Installation & Setup

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd JumpTrader
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# Binance API Credentials
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=false

# Orion Protocol (Optional)
ORION_API_KEY=your_orion_key_here

# Feature Flags
ENABLE_WEBSOCKET=true
ENABLE_ORION_INTEGRATION=true
ENABLE_GPT_ANALYSIS=false
ENABLE_TELEGRAM_BOT=false
ENABLE_ALERTS=false

# Logging
LOG_LEVEL=INFO
```

**Important:** 
- Get Binance API keys from: https://www.binance.com/en/my/settings/api-management
- Enable futures trading permissions for full functionality
- Use testnet for development/testing

### 3. Test API Connection

```bash
python credentials.py
```

This will verify your API setup and show your futures account balance.

### 4. Run the Dashboard

```bash
streamlit run main_dashboard.py
```

The dashboard will be available at `http://localhost:8501`

## 📁 Project Structure

```
JumpTrader/
├── config/
│   ├── __init__.py
│   └── settings.py              # Centralized configuration
├── clients/
│   ├── __init__.py
│   ├── binance_client.py        # Binance REST + WebSocket client
│   └── orion_client.py          # Orion Protocol client
├── data/
│   ├── __init__.py
│   └── market_data_manager.py   # Data collection orchestration
├── signals/
│   ├── __init__.py
│   └── signal_processor.py      # AI signal detection logic
├── ui/
│   ├── __init__.py
│   └── dashboard_components.py  # Streamlit UI components
├── utils/
│   ├── __init__.py
│   └── helpers.py               # Utility functions
├── main_dashboard.py            # Main Streamlit application
├── credentials.py               # API connection utilities
├── dashboard_v1.py              # Legacy dashboard (for reference)
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🎮 Usage

### Dashboard Controls

**Sidebar Options:**
- **Symbol Limit**: Control how many symbols to display (10-500)
- **Auto-refresh**: Enable/disable automatic updates
- **Refresh Interval**: Set update frequency (30-300 seconds)
- **Signal Filters**: Toggle different signal types
- **Sort Options**: Sort by price change, volume, signals, etc.

**Main Features:**
- **Real-time Data**: Live market data with WebSocket updates
- **Signal Detection**: Automatic detection of trading opportunities
- **Search/Filter**: Find specific symbols quickly
- **Performance Metrics**: Market overview and statistics

### Signal Types

- 🔥 **Volume Spikes**: Unusual trading volume activity
- 📈📉 **Price Movements**: Significant 1h and 24h changes
- 🟢🔴 **Momentum Patterns**: Stair-step price movements
- 🚀💥 **Range Breaks**: Breakout from consolidation
- 📊⚡ **Acceleration**: Increasing volume or momentum
- 📐📏 **Consolidation**: Tight trading ranges

## 🔧 Configuration

### Signal Thresholds

Edit `config/settings.py` to customize signal sensitivity:

```python
# Volume spike detection
VOLUME_SPIKE_THRESHOLD = 2.0  # 2x average volume

# Price change thresholds
PRICE_CHANGE_THRESHOLDS = {
    '1h': {'high': 5.0, 'medium': 2.0, 'low': 1.0},
    '24h': {'high': 15.0, 'medium': 8.0, 'low': 3.0}
}

# Momentum detection
MOMENTUM_LOOKBACK_PERIODS = 4  # hours
RANGE_BREAK_THRESHOLD = 0.02   # 2% break
```

### Data Collection Settings

```python
# Polling intervals
MARKET_DATA_REFRESH_INTERVAL = 60  # seconds
ORION_POLL_INTERVAL = 15          # seconds

# Candle data limits
CANDLE_INTERVALS = {
    '1m': {'limit': 1440, 'description': '1 minute candles for 24h'},
    '1h': {'limit': 168, 'description': '1 hour candles for 7 days'},
    # ... more intervals
}
```

## 🚀 Development Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Binance REST API integration
- [x] WebSocket real-time data
- [x] Basic signal detection
- [x] Streamlit dashboard

### Phase 2: Enhanced Signals 🔄
- [ ] Advanced pattern recognition
- [ ] Machine learning models
- [ ] Custom signal algorithms
- [ ] Backtesting framework

### Phase 3: Additional Sources 📊
- [ ] Orion Protocol integration
- [ ] CoinMarketCap data
- [ ] Velo Protocol data
- [ ] Cross-exchange arbitrage

### Phase 4: Advanced Features 🤖
- [ ] GPT analysis integration
- [ ] Telegram bot alerts
- [ ] Email notifications
- [ ] Trading automation

### Phase 5: Production Ready 🏭
- [ ] Docker deployment
- [ ] Cloud hosting
- [ ] Database integration
- [ ] User authentication

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk of loss. Always do your own research and never invest more than you can afford to lose.

## 🔗 Links

- **Binance API Documentation**: https://binance-docs.github.io/apidocs/futures/en/
- **Streamlit Documentation**: https://docs.streamlit.io/
- **Orion Protocol**: https://orionprotocol.io/

## 📞 Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check the documentation
- Review the configuration options 
=======
# jumptrader
AI trading ZC tool
>>>>>>> 1eb42c02959704f7186df161323a5a2d6333c80f
