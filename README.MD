# bAIbysitter - Intelligent Transaction Guardian

bAIbysitter is a decentralized transaction monitoring system that uses AI to protect agents and humans from potentially harmful transactions or money losses. The system comprises three key components working in harmony to ensure transaction safety.

## Key Components

Architecture

<img width="856" alt="Image" src="https://github.com/user-attachments/assets/63f3a763-4ca2-44ae-8029-2d481119fb76" />

### 1. bAIby Agent (AI Decision Maker)

- Powered by GPT-4 for intelligent transaction analysis
- Processes warnings from monitoring bots
- Makes final approval/rejection decisions
- Stores transaction history in Supabase
- Provides detailed reasoning for each decision

### 2. Monitoring Bots

Currently focused on SONIC blockchain monitoring:

- **Balance Monitor:** Detects potential wallet draining attempts
  - Tracks transactions using >90% of wallet balance
  - Real-time balance checking
  - Immediate warning generation for suspicious patterns

### 3. Main Application

Orchestrates the entire transaction flow:

- Receives incoming transactions
- Manages WebSocket connections with monitoring bots
- Coordinates communication between components
- Handles timeouts and retries
- Returns final decisions to users

## Transaction Flow

1. **Initial Reception:**

   - Transaction received from SONIC wallet
   - Unique hash generated for tracking
   - Transaction details broadcast to monitoring bots

2. **Bot Analysis:**

   - Balance bot checks for draining attempts
   - Warnings collected via WebSocket
   - 5-second timeout for bot responses

3. **AI Processing:**

   - bAIby Agent receives transaction data and warnings
   - GPT-4 analyzes transaction context and risks
   - Decision made based on comprehensive analysis

4. **Response Handling:**

   - Approval/rejection decision returned
   - Transaction proceeds if approved
   - Detailed explanation provided for rejections

## Setup Instructions

### Environment Configuration

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key
WS_BOT_URL=ws://localhost:8000/ws/bot
TX_AGENT_URL=http://localhost:8001/tx_agent
```

### Installation

```
pip install -r requirements.txt
```

### Running the System

```
# Start main application
uvicorn app.main:app --reload

# Launch bAIby agent
uvicorn baiby_agent.txagent:app --port 8001

# Start Zerepy AGENT
```

## Technical Details

### Stack

- Backend: FastAPI
- AI: OpenAI GPT-4
- Database: Supabase
- Blockchain: SONIC
- Real-time: WebSockets
- HTTP Client: HTTPX

### Security Features

- Real-time transaction monitoring
- AI-powered risk assessment
- Comprehensive error logging
- Transaction audit trail
- Multiple retry mechanisms
- Timeout handling

## Future Development

- Additional monitoring bots
- Enhanced AI capabilities
- Multi-chain support
- Advanced risk scoring
- User preferences


